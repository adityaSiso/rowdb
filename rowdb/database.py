import os
import shutil
from typing import Any

from .storage import NDJsonStorage


class RowDB:
    """
    Base class for RowDB, which provides a simple interface for 
    interacting with a database stored in NDJSON format.
    """
    DEFAULT_DATABASE = 'default'
    DEFAULT_COLLECTION = 'items.ndjson'
    DEFAULT_STORAGE_CLASS = NDJsonStorage
 
    def __init__(self, db: str, collection: str, **kwargs):
        """
        Initialize the RowDB class with the specified database and collection.

        :param db: The name of the database (directory).
        :param collection: The name of the collection (NDJSON file).
        """
        self.db = db
        self.collection = collection
        self._storage = RowDB.DEFAULT_STORAGE_CLASS(db, collection)

    def insert(self, data: dict):
        """
        Insert a new record into the RowDB.

        :param data: A dictionary representing the record to be inserted.
        """
        self._storage.write(data)

    def insert_many(self, data: list[dict]):
        ...

    def retrieve(self, key: Any):
        """
        Retrieve a record from the JStore based on the provided key.

        :param key: The key of the record to be retrieved.
        :return: The record associated with the provided key, or None if not found.
        """
        data = self._storage.read()
       
        if data is None:
            raise ValueError("The data file is empty or corrupted.")

        try:
            value = data[key]
        except KeyError:
            raise KeyError(f"Key '{key}' not found in JStore DB.")

        return value

    def retrieve_all(self):
        """
        Retrieve all records from the JStore.

        :return: A dictionary containing all records in the JStore.
        """
        data = self._storage.read()
        return data

    def drop(self):
        """
        Drop the current collection (NDJSON file) from the database.
        """
        os.remove(f"{self.db}/{self.collection}")

    def dropDatabase(self):
        """
        Drop the entire database (directory) and all its collections."""
        shutil.rmtree(self.db)
        
    def delete(self, key: Any):
        """
        Delete a record from the JStore based on the provided key.

        :param key: The key of the record to be deleted.
        """
        ...