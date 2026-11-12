from .exceptions import (
    ActivePartitionNotFoundException,
    MasterDataNotFoundException,
    PartitionNotFoundException,
)
from .storage import JsonStorage


class Master:
    """
    A class to manage the master collection in RowDB.

    master data format: 
        {
            "active_partition": "<partX>.ndjson",
            "partitions": [
                {"start_row_id": 0, "end_row_id": None, "name": "part-1"},
                ...
            ],
            "next_row_id": xyz, 
        }
    """
    master_collection_name = "master"
    partition_size_limit = 1024 * 1024 * 4  # Default partition size limit (MB)

    def __init__(self, rowdb):
        """
        Initialize the Master instance.
        """
        self.storage = JsonStorage(
            path=rowdb.db,
            filename=self.master_collection_name, 
        )
        try:
            self.set_defaults()
        except BaseException:
            self.storage.close()
            raise
        self.rowdb = rowdb
        self._next_row_id = self.master_data.get("next_row_id")

    @property
    def row_id(self):
        return self._next_row_id

    @row_id.setter
    def row_id(self, value):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError("row_id must be an integer.")

        if value < 0:
            raise ValueError("row_id must be a non-negative integer.")

        if value < self.row_id:
            raise ValueError("row_id cannot be decreased.")

        self.advance_row_id(value - self.row_id)

    def advance_row_id(self, count: int):
        """Reserve a consecutive range of IDs in the master file first.

        Reserving before appending ensures a failed metadata write cannot leave
        an already-written record whose ID will be reused after reopening.
        Failed appends may leave gaps, but allocated IDs are never reused.
        """
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("count must be a non-negative integer.")
        if count == 0:
            return []

        # A previous append may have filled the active partition immediately
        # before a rotation metadata write failed. Rotate before reserving more.
        self.rotate_if_full()

        first_row_id = self._next_row_id
        next_row_id = first_row_id + count
        new_master_data = self._copy_master_data()
        new_master_data["next_row_id"] = next_row_id
        self.storage.write(new_master_data)
        self.master_data = new_master_data
        self._next_row_id = next_row_id
        return list(range(first_row_id, next_row_id))

    def rotate_if_full(self):
        """Rotate the active partition if its current file reached the limit."""
        if not self.is_partition_size_limit_reached():
            return False
        self.update_partition_search_key()
        self.add_partition()
        return True

    def _copy_master_data(self):
        partitions = self.master_data.get("partitions")
        if not isinstance(partitions, list):
            raise MasterDataNotFoundException("Master data is not initialized.")
        new_master_data = dict(self.master_data)
        new_master_data["partitions"] = [
            dict(partition) for partition in partitions
        ]
        return new_master_data

    def set_defaults(self):
        """
        Set default values for the master collection if it doesn't exist.
        """
        master_data = self.storage.read()

        if master_data is None:
            master_data = {
                "active_partition": None,
                "partitions": [],
                "next_row_id": 0,
            }
            self.storage.write(master_data)
        elif isinstance(master_data.get("partitions"), dict):
            active_partition = master_data.get("active_partition")
            migrated_master_data = dict(master_data)
            migrated_master_data["partitions"] = (
                [{"start_row_id": 0, "end_row_id": None, "name": active_partition}]
                if active_partition else []
            )
            self.storage.write(migrated_master_data)
            master_data = migrated_master_data
        self.master_data = master_data

    def get_active_partition(self):
        """
        Retrieve the active partition from the master collection.

        :return: The active partition, or None if not found.
        """
        return self.master_data.get("active_partition")

    def get_total_partitions(self):
        """
        Retrieve the total number of partitions from the master collection.

        :return: The total number of partitions, or 0 if not found.
        """
        partitions = self.master_data.get("partitions")
        if partitions is None:
            raise PartitionNotFoundException("Master data is not initialized.")
        return len(partitions)

    def add_partition(self):
        """
        Add a new partition to the master data based on the provided RowDB instance.

        :param row_db: An instance of RowDB containing the database and collection information.
        """
        new_partition_name = \
            f"{self.rowdb.partition_prefix}{self.get_total_partitions() + 1}"
        new_master_data = self._copy_master_data()
        new_master_data["partitions"].append({
            "start_row_id": self._next_row_id,
            "end_row_id": None,
            "name": new_partition_name,
        })
        new_master_data["active_partition"] = new_partition_name
        self.storage.write(new_master_data)
        self.master_data = new_master_data
        self.rowdb.update_storage(new_partition_name)

    def get_partition_by_row_id(self, row_id: int):
        """
        Search for a partition based on the provided row ID.

        :param row_id: The row ID to search for.
        :return: The partition name if found, else None.
        """
        partitions = self.master_data.get("partitions")
        if partitions is None:
            raise MasterDataNotFoundException("Master data is not initialized.")

        for partition in partitions:
            start_row_id = partition["start_row_id"]
            end_row_id = partition["end_row_id"]
            if start_row_id <= row_id and (end_row_id is None or row_id < end_row_id):
                return partition["name"]
        return None

    def update_partition_search_key(self):
        """
        Update the search key for the active partition in the master data.
        """
        active_partition = self.get_active_partition()
        if active_partition is None:
            raise ActivePartitionNotFoundException("Active partition is not set.")

        partitions = self.master_data.get("partitions")
        if partitions is None:
            raise MasterDataNotFoundException("Master data is not initialized.")

        new_master_data = self._copy_master_data()
        partitions = new_master_data["partitions"]

        for partition in partitions:
            if partition["name"] == active_partition:
                partition["end_row_id"] = self._next_row_id
                break
        else:
            raise ActivePartitionNotFoundException("Active partition not found in master data.")

        self.storage.write(new_master_data)
        self.master_data = new_master_data

    def is_partition_size_limit_reached(self):
        """
        Check if the size of a given partition has reached the specified limit.

        :param partition: The name of the partition to check.
        :return: True if the partition size has reached or exceeded the limit, False otherwise.
        """
        if self.master_data is None:
            raise MasterDataNotFoundException("Master data is not initialized.")
        partition_size = self.rowdb._storage.get_size()
        return partition_size >= self.partition_size_limit


def load_master(rowdb):
    return Master(rowdb)
