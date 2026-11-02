import json
import shutil
from typing import Any

from .storage import NDJsonStorage
from .master import load_master


class RowDB:
    """
    Base class for RowDB, which provides a simple interface for 
    interacting with a database stored in NDJSON format.
    """
    default_database = 'default'
    default_partition_prefix = 'part-'
    default_storage_class = NDJsonStorage
 
    def __init__(self, db: str | None = None, partition_prefix: str | None = None, **kwargs):
        """
        Initialize the RowDB class with the specified database and collection.

        :param db: The name of the database (directory).
        :param partition_prefix: The prefix for the partition files.
        """
        self.db = db if db else RowDB.default_database
        self.partition_prefix = (partition_prefix 
            if partition_prefix else RowDB.default_partition_prefix
        )
        # Initialize the master collection
        self.master = load_master(self)

        # Initialize the storage for the active partition
        if self.master.get_active_partition() is None:
            self.master.add_partition()
        self._storage = RowDB.default_storage_class(
            self.db, self.master.get_active_partition(),
        )

    def update_storage(self, partition_name: str):
        """
        Update the storage to point to a new partition.

        :param partition_name: The name of the new partition.
        """
        self._storage = RowDB.default_storage_class(
            self.db, partition_name,
        )

    def insert(self, data: dict) -> int:
        """
        Insert a new record into the RowDB.

        :param data: A dictionary representing the record to be inserted.
        :return: The row ID of the inserted record.
        """
        if not isinstance(data, dict):
            raise ValueError("Data must be of type dictionary.")
        data['row_id'] = self.master.row_id
        self._storage.write(data)
        self.master.row_id += 1

        return data['row_id']

    def insert_many(self, data: list[dict]) -> list:
        """
        Insert multiple records into the RowDB.
        """
        if not isinstance(data, list):
            raise ValueError("Data must be a list of dictionaries.")

        if not all(isinstance(record, dict) for record in data):
            raise ValueError("Data must be a list of dictionaries.")

        first_row_id = self.master.row_id
        row_ids = list(range(first_row_id, first_row_id + len(data)))
        for record, row_id in zip(data, row_ids):
            record['row_id'] = row_id

        if data:
            self._storage.write(data)
            self.master.advance_row_id(len(data))

        return row_ids

    def retrieve(self, row_id: Any) -> dict:
        """
        Retrieve a record from the JStore based on the provided row ID.

        :param row_id: The row ID of the record to be retrieved.
        :return: The record associated with the provided row ID, or None if not found.
        """
        partition_name = self.master.get_partition_by_row_id(row_id)

        if partition_name is None:
            raise ValueError(f"No data found for row_id: {row_id}")

        storage = RowDB.default_storage_class(
            self.db, partition_name,
        )

        def build_record_map() -> dict[int, dict]:
            """
            Build a mapping of row_id to records for the current partition.
            """
            record_map = {}
            records = storage.read()
            if records is not None:
                for record in records:
                    record = json.loads(record)
                    record_map[record['row_id']] = record
            return record_map

        record_map = build_record_map()
        try:
            return record_map[row_id]
        except KeyError:
            raise ValueError(f"No data found for row_id: {row_id}")

    def retrieve_all(self) -> list[dict]:
        """
        Retrieve all records from the JStore.

        :return: A list of dictionaries containing all records in the JStore.
        """
        partitions = self.master.master_data.get("partitions", [])
        all_records = []
        for partition in partitions:
            partition_name = partition.get("name")
            if (partition_name is None or 
                not partition_name.startswith(self.partition_prefix)):
                continue
            storage = RowDB.default_storage_class(
                self.db, partition_name,
            )
            records = storage.read()
            if records is not None:
                data = [json.loads(record) for record in records]
                all_records.extend(data)

        return all_records

    def dropPartitions(self, partition_prefix: str):
        """
        Drop the specified partition (NDJSON file) from the database.

        :param partition_prefix: The prefix of the partition to be dropped.
        """
        ...

    def dropDatabase(self):
        """
        Drop the entire database (directory) and all its collections."""
        shutil.rmtree(self.db)
