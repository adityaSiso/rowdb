import json
import os
import tempfile
from abc import ABC, abstractmethod
from typing import Any


def validate_filename_component(filename: str) -> str:
    """Reject names that could escape a database directory on either OS."""
    if not isinstance(filename, str) or not filename:
        raise ValueError("Storage filename must be a non-empty string.")
    if (
        filename in {'.', '..'}
        or '\x00' in filename
        or '/' in filename
        or '\\' in filename
        or ':' in filename
    ):
        raise ValueError("Storage filename must be a single path component.")
    return filename


def touch(path: str):
    """
    Create an empty file at the specified path if it doesn't exist.

    :param path: The path where the file should be created.
    """
    with open(path, 'w'):
        pass


class Storage(ABC):
    """
    Base class for storage management in RowDB.
    """
    
    extension = None
    
    def __init__(self, path: str, filename: str, access_mode: str = 'a+', **kwargs):
        """
        Initialize the Storage class.

        :param path: The directory path where the storage file is located.
        :param filename: The name of the storage file.
        :param access_mode: The mode in which the file should be opened. 
                            Default is 'a+' (append and read).
        """
        validate_filename_component(filename)

        path = os.path.abspath(os.fsdecode(os.fspath(path)))
        os.makedirs(path, exist_ok=True)
        self.full_path = os.path.abspath(
            os.path.join(path, f'{filename}{self.extension}')
        )
        try:
            common_path = os.path.commonpath((path, self.full_path))
        except ValueError as error:
            raise ValueError("Storage file must stay inside its database directory.") from error
        if os.path.normcase(common_path) != os.path.normcase(path):
            raise ValueError("Storage file must stay inside its database directory.")

        if not os.path.exists(self.full_path):
            touch(self.full_path)

        self.file = open(self.full_path, mode=access_mode)  # noqa: SIM115

    @abstractmethod
    def read(self, key: Any = None):
        """
        Read data from the storage file. If a key is provided, it 
        will return the value associated with that key else it will 
        return all records.

        :param key: The key of the record to be retrieved (optional).
        """
        raise NotImplementedError("The read method must be implemented by subclasses.")

    @abstractmethod
    def write(self, data: dict):
        """
        Write data to the storage file.
        
        :param data: The dictionary or list of dictionaries to be written as JSON objects.
        """
        raise NotImplementedError("The write method must be implemented by subclasses.")

    def close(self):
        """
        Close the storage file. It's a good practice to close the 
        file after operations are done to free up system resources.
        """
        if not self.file.closed:
            self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def get_size(self):
        """
        Get the size of a file in bytes.
        """
        self.file.seek(0, os.SEEK_END)
        size = self.file.tell()
        self.file.seek(0)
        return size


class NDJsonStorage(Storage):
    
    extension = '.ndjson'
    
    def __init__(
            self, path: str, filename: str, access_mode: str = 'a+',
            **kwargs,
        ):
        """
        Initialize the NDJsonStorage class.

        :param path: The directory path where the NDJSON file is located.
        :param filename: The name of the NDJSON file.
        :param access_mode: The mode in which the file should be opened. 
                            Default is 'a+' (append and read).
        """
        super().__init__(path, filename, access_mode, **kwargs)

    def read(self, key: Any = None):
        """
        Read data from the NDJSON file. If a key is provided, it 
        will return the value associated with that key else it will 
        return all records.

        :param key: The key of the record to be retrieved (optional).
        """
        if self.get_size() == 0:
            return None

        if key is None:
            ...
            
        return self.file.readlines()

    def write(self, data: dict):
        """
        Write data to the NDJSON file.
        
        :param data: The dictionary or list of dictionaries to be written as JSON objects.
        """
        records = data if isinstance(data, list) else [data]
        if not all(isinstance(record, dict) for record in records):
            raise TypeError("Data must be a dictionary or a list of dictionaries.")
        serialized_data = ''.join(
            f'{json.dumps(record)}\n' for record in records
        )
        self.file.write(serialized_data)


class JsonStorage(Storage):
    """
    A class to manage JSON storage in RowDB.
    Inherits from Storage.
    """
    
    extension = '.json'
    
    def __init__(self, path: str, filename: str, access_mode: str = 'r+', **kwargs):
        """
        Initialize the JsonStorage class.

        :param path: The directory path where the JSON file is located.
        :param filename: The name of the JSON file.
        :param access_mode: The mode in which the file should be opened. 
                            Default is 'r+' (read and write).
        """
        super().__init__(path, filename, access_mode, **kwargs)

    def read(self, key: Any = None):
        """
        Read data from the JSON file. If a key is provided, it 
        will return the value associated with that key else it will 
        return all entries.

        :param key: The key of the record to be retrieved (optional).
        """
        if self.get_size() == 0:
            return None

        data = json.loads(self.file.read())
        if key is None:
            return data
            
        return data.get(key)

    def write(self, data: dict):
        """
        Write data to the JSON file.
        
        :param data: The dictionary or list of dictionaries to be 
                     written as JSON objects.
        """
        if not isinstance(data, dict):
            raise TypeError("Data must be of type dictionary.")
        serialized_data = json.dumps(data, indent=4)
        if self.file.closed:
            raise ValueError("I/O operation on closed JSON storage.")

        directory = os.path.dirname(self.full_path)
        fd, temp_path = tempfile.mkstemp(
            prefix=f'.{os.path.basename(self.full_path)}.',
            suffix='.tmp',
            dir=directory,
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as temp_file:
                temp_file.write(serialized_data)
                temp_file.flush()
                os.fsync(temp_file.fileno())

            self.file.close()
            try:
                os.replace(temp_path, self.full_path)
            except Exception:
                self.file = open(  # noqa: SIM115
                    self.full_path, mode='r+', encoding='utf-8'
                )
                raise

            temp_path = None
            self.file = open(  # noqa: SIM115
                self.full_path, mode='r+', encoding='utf-8'
            )
        finally:
            if temp_path is not None and os.path.exists(temp_path):
                os.unlink(temp_path)
