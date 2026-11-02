from abc import ABC, abstractmethod
import os
import json
from typing import Any


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
        if not os.path.isdir(path):
            os.makedirs(path)

        self.full_path = f'{path}/{filename}{self.extension}'

        if not os.path.exists(self.full_path):
            touch(self.full_path)

        self.file = open(self.full_path, mode=access_mode)

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
        self.file.close()

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
            raise ValueError("Data must be a dictionary or a list of dictionaries.")
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
            raise ValueError("Data must be of type dictionary.")
        serialized_data = json.dumps(data, indent=4)
        self.file.seek(0)
        self.file.truncate()
        self.file.write(serialized_data)
        self.file.flush()
