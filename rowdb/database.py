import json
import shutil
from typing import Any

from .exceptions import CorruptedPartitionDataException, RowNotFoundException
from .locking import DatabaseLock
from .master import load_master
from .storage import NDJsonStorage, validate_filename_component


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
        validate_filename_component(self.partition_prefix)

        # The initial implementation supports one open writer per database.
        # Holding this OS lock prevents stale instances from allocating an ID.
        self._lock = DatabaseLock(self.db)
        try:
            self.master = load_master(self)

            active_partition = self.master.get_active_partition()
            if active_partition is None:
                self.master.add_partition()
            else:
                self.update_storage(active_partition)
        except BaseException:
            self.close()
            raise

    def update_storage(self, partition_name: str):
        """
        Update the storage to point to a new partition.

        :param partition_name: The name of the new partition.
        """
        current_storage = getattr(self, "_storage", None)
        if current_storage is not None:
            current_storage.close()
        self._storage = RowDB.default_storage_class(
            self.db, partition_name,
        )

    def close(self):
        """Close the active partition and master storage files."""
        current_storage = getattr(self, "_storage", None)
        master = getattr(self, "master", None)
        try:
            if current_storage is not None:
                current_storage.close()
        finally:
            try:
                if master is not None:
                    master.storage.close()
            finally:
                lock = getattr(self, "_lock", None)
                if lock is not None:
                    lock.close()

    def insert(self, data: dict) -> int:
        """
        Insert a new record into the RowDB.

        :param data: A dictionary representing the record to be inserted.
        :return: The row ID of the inserted record.
        """
        if not isinstance(data, dict):
            raise TypeError("Data must be of type dictionary.")
        row_id = self.master.advance_row_id(1)[0]
        data['row_id'] = row_id
        self._storage.write(data)
        self.master.rotate_if_full()

        return row_id

    def insert_many(self, data: list[dict]) -> list:
        """
        Insert multiple records into the RowDB.
        """
        if not isinstance(data, list):
            raise TypeError("Data must be a list of dictionaries.")

        if not all(isinstance(record, dict) for record in data):
            raise TypeError("Data must be a list of dictionaries.")

        if data:
            row_ids = self.master.advance_row_id(len(data))
            records = [dict(record) for record in data]
            for record, row_id in zip(records, row_ids):
                record['row_id'] = row_id
            self._storage.write(records)
            self.master.rotate_if_full()
        else:
            row_ids = []

        return row_ids

    def retrieve(self, row_id: Any) -> dict:
        """
        Retrieve a record from the JStore based on the provided row ID.

        :param row_id: The row ID of the record to be retrieved.
        :return: The record associated with the provided row ID, or None if not found.
        """
        partition_name = self.master.get_partition_by_row_id(row_id)

        if partition_name is None:
            raise RowNotFoundException(f"No data found for row_id: {row_id}")

        with RowDB.default_storage_class(self.db, partition_name) as storage:
            records = storage.read()

        record_map = {}
        if records is not None:
            for record in records:
                record = json.loads(record)
                row_id_in_file = record['row_id']
                if row_id_in_file in record_map:
                    raise CorruptedPartitionDataException(
                        f"Duplicate row_id in partition {partition_name}: "
                        f"{row_id_in_file}"
                    )
                record_map[row_id_in_file] = record
        try:
            return record_map[row_id]
        except KeyError:
            raise RowNotFoundException(f"No data found for row_id: {row_id}")

    def retrieve_all(self) -> list[dict]:
        """
        Retrieve all records from the JStore.

        :return: A list of dictionaries containing all records in the JStore.
        """
        partitions = self.master.master_data.get("partitions", [])
        all_records = []
        seen_row_ids = set()
        for partition in partitions:
            partition_name = partition.get("name")
            if (partition_name is None or 
                not partition_name.startswith(self.partition_prefix)):
                continue
            with RowDB.default_storage_class(self.db, partition_name) as storage:
                records = storage.read()
            if records is not None:
                data = [json.loads(record) for record in records]
                for record in data:
                    row_id = record['row_id']
                    if row_id in seen_row_ids:
                        raise CorruptedPartitionDataException(
                            f"Duplicate row_id in database: {row_id}"
                        )
                    seen_row_ids.add(row_id)
                all_records.extend(data)

        return all_records

    def dropPartitions(self, partition_prefix: str):
        """
        Drop the specified partition (NDJSON file) from the database.

        :param partition_prefix: The prefix of the partition to be dropped.
        """

    def dropDatabase(self):
        """
        Drop the entire database (directory) and all its collections."""
        self.close()
        shutil.rmtree(self.db)
