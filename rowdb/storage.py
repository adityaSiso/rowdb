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


class NDJsonStorage:

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
        if not filename.endswith('.ndjson'):
            raise ValueError("The filename must end with '.ndjson'")

        if not os.path.isdir(path):
            os.makedirs(path)

        self.full_path = f'{path}/{filename}'

        if not os.path.exists(self.full_path):
            touch(self.full_path)

        self.file = open(self.full_path, mode=access_mode)

    def _is_empty(self):
        """
        Check if the NDJSON file is empty.
        """
        self.file.seek(0, os.SEEK_END)
        size = self.file.tell()
        self.file.seek(0)
        return size == 0

    def read(self, key: Any = None):
        """
        Read data from the NDJSON file. If a key is provided, it 
        will return the value associated with that key else it will 
        return all records.

        :param key: The key of the record to be retrieved (optional).
        """
        if self._is_empty():
            return None

        if key is None:
            ...
            
        return self.file.readlines()

    def write(self, data: dict):
        """
        Write data to the NDJSON file.
        
        :param data: The dictionary to be written as a JSON object.
        """
        json.dump(data, self.file, separators='\n')

    def close(self):
        """
        Close the NDJSON file. It's a good practice to close the 
        file after operations are done to free up system resources.
        """
        self.file.close()
