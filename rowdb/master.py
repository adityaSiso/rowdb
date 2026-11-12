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
            "partitions": {
                "part-": {
                    "partitions": [
                        {"start_row_id": 0, "end_row_id": None, "name": "part-1"},
                        ...
                    ]
                    "active_partition": "part-x",
                    "next_row_id": xyz,
                },
                "custom-partition-name": {
                    "partitions": [
                        {"start_row_id": 0, "end_row_id": None, "name": "custom-partition-name"},
                        ...
                    ]
                    "active_partition": "custom-partition-name",
                    "next_row_id": xyz,
                }
                ...
            },
        }
    """
    master_collection_name = "master"
    partition_size_limit = 1024 * 1024 * 4  # Default partition size limit (MB)

    def __init__(self, rowdb):
        """
        Initialize the Master instance.
        """
        self.rowdb = rowdb
        self.storage = JsonStorage(
            path=rowdb.db,
            filename=self.master_collection_name, 
        )
        self.set_defaults()
        self._next_row_id = self.sub_partition_metadata.get("next_row_id")

    @property
    def row_id(self):
        return self._next_row_id

    @row_id.setter
    def row_id(self, value):
        
        if not isinstance(value, int):
            raise TypeError("row_id must be an integer.")

        if value < 0:
            raise ValueError("row_id must be a non-negative integer.")

        if self.row_id - value > 1:
            raise ValueError("row_id can only be incremented by 1.")

        partition_limit_reached = self.is_partition_size_limit_reached()
        self._next_row_id = value
        self.sub_partition_metadata["next_row_id"] = value
        if partition_limit_reached:
            self.update_partition_search_key()
            self.add_partition()
        self.storage.write(self.master_data)

    def advance_row_id(self, count: int):
        if not isinstance(count, int) or count < 0:
            raise ValueError("count must be a non-negative integer.")
        if count == 0:
            return

        self._next_row_id += count
        self.sub_partition_metadata["next_row_id"] = self._next_row_id
        if self.is_partition_size_limit_reached():
            self.update_partition_search_key()
            self.add_partition()
        else:
            self.storage.write(self.master_data)

    def set_defaults(self):
        """
        Set default values for the master collection if it doesn't exist.
        """
        master_data = self.storage.read()

        if master_data is None:
            master_data = {}

            master_data["partitions"] = {
                self.rowdb.partition_prefix: {
                    "partitions": [
                        {
                            "start_row_id": 0, 
                            "end_row_id": None, 
                            "name": f"{self.rowdb.partition_prefix}1"
                        },
                    ],
                    "active_partition": f"{self.rowdb.partition_prefix}1",
                    "next_row_id": 0,
                }
            }
            self.storage.write(master_data)
            self.sub_partition_metadata = master_data["partitions"][self.rowdb.partition_prefix]
        else:
            partitions = master_data.get("partitions")
            sub_parition = partitions.get(self.rowdb.partition_prefix)

            if sub_parition is None:
                sub_parition = {
                    "partitions": [
                        {
                            "start_row_id": 0, 
                            "end_row_id": None, 
                            "name": f"{self.rowdb.partition_prefix}1"
                        },
                    ],
                    "active_partition": f"{self.rowdb.partition_prefix}1",
                    
                }
                self.sub_partition_metadata = sub_parition
                partitions[self.rowdb.partition_prefix] = self.sub_partition_metadata
                master_data["partitions"] = partitions
                self.storage.write(master_data)
            else:
                self.sub_partition_metadata = sub_parition
        self.master_data = master_data

    def get_active_partition(self):
        """
        Retrieve the active partition from the master collection.

        :return: The active partition, or None if not found.
        """
        current_partition = self.sub_partition_metadata.get("active_partition")
        if current_partition is None:
            return
        return current_partition

    def get_total_partitions(self):
        """
        Retrieve the total number of partitions from the master collection.

        :return: The total number of partitions, or 0 if not found.
        """
        partitions = self.sub_partition_metadata.get("partitions")
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
        self.sub_partition_metadata["partitions"].append({
            "start_row_id": self._next_row_id,
            "end_row_id": None,
            "name": new_partition_name,
        })
        self.sub_partition_metadata["active_partition"] = new_partition_name
        self.master_data["partitions"][self.rowdb.partition_prefix] = self.sub_partition_metadata
        self.storage.write(self.master_data)
        self.rowdb.update_storage(new_partition_name)

    def get_partition_by_row_id(self, row_id: int):
        """
        Search for a partition based on the provided row ID.

        :param row_id: The row ID to search for.
        :return: The partition name if found, else None.
        """
        partitions = self.sub_partition_metadata.get("partitions")
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

        partitions = self.sub_partition_metadata.get("partitions")
        if partitions is None:
            raise MasterDataNotFoundException("Master data is not initialized.")

        for partition in partitions:
            if partition["name"] == active_partition:
                partition["end_row_id"] = self._next_row_id
                break
        else:
            raise ActivePartitionNotFoundException("Active partition not found in master data.")

        self.storage.write(self.master_data)

    def is_partition_size_limit_reached(self):
        """
        Check if the size of a given partition has reached the specified limit.

        :param partition: The name of the partition to check.
        :return: True if the partition size has reached or exceeded the limit, False otherwise.
        """
        master_data = self.storage.read()
        if master_data is None:
            raise MasterDataNotFoundException("Master data is not initialized.")
        partition_size = self.rowdb._storage.get_size()
        return partition_size >= self.partition_size_limit


def load_master(rowdb):
    return Master(rowdb)