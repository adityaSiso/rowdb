import json

import pytest

from rowdb import RowDB
from rowdb.exceptions import RowNotFoundException


def test_insert_retrieve_and_reopen_database(tmp_path):
    database_path = tmp_path / "database"
    db = RowDB(database_path)

    row_id = db.insert({"name": "Ada"})

    assert row_id == 0
    assert db.retrieve(row_id) == {"name": "Ada", "row_id": 0}
    assert db.retrieve_all() == [{"name": "Ada", "row_id": 0}]
    db.close()

    reopened = RowDB(database_path)
    assert reopened.retrieve(row_id) == {"name": "Ada", "row_id": 0}
    reopened.close()


def test_insert_many_returns_row_ids_and_handles_empty_batch(tmp_path):
    db = RowDB(tmp_path / "database")

    assert db.insert_many([]) == []
    row_ids = db.insert_many([{"name": "Ada"}, {"name": "Grace"}])

    assert row_ids == [0, 1]
    assert db.retrieve_all() == [
        {"name": "Ada", "row_id": 0},
        {"name": "Grace", "row_id": 1},
    ]
    db.close()


@pytest.mark.parametrize("data", [None, "not a list", [1]])
def test_insert_many_rejects_invalid_data(tmp_path, data):
    db = RowDB(tmp_path / "database")
    with pytest.raises(TypeError):
        db.insert_many(data)
    db.close()


def test_insert_rejects_non_dictionary(tmp_path):
    db = RowDB(tmp_path / "database")
    with pytest.raises(TypeError, match="dictionary"):
        db.insert(["not", "a", "record"])
    db.close()


def test_retrieve_raises_for_missing_row(tmp_path):
    db = RowDB(tmp_path / "database")
    with pytest.raises(RowNotFoundException, match="row_id: 42"):
        db.retrieve(42)
    db.close()


def test_close_is_idempotent_and_closes_storage(tmp_path):
    db = RowDB(tmp_path / "database")
    partition_file = db._storage.file
    master_file = db.master.storage.file

    db.close()
    db.close()

    assert partition_file.closed
    assert master_file.closed


def test_drop_database_closes_handles_and_removes_directory(tmp_path):
    database_path = tmp_path / "database"
    db = RowDB(database_path)
    partition_file = db._storage.file
    master_file = db.master.storage.file

    db.dropDatabase()

    assert not database_path.exists()
    assert partition_file.closed
    assert master_file.closed


def test_master_file_tracks_partition_and_next_row_id(tmp_path):
    database_path = tmp_path / "database"
    db = RowDB(database_path)
    db.insert({"name": "Ada"})
    db.close()

    master_data = json.loads((database_path / "master.json").read_text())
    assert master_data["active_partition"] == "part-1"
    assert master_data["next_row_id"] == 1
    assert master_data["partitions"] == [
        {"start_row_id": 0, "end_row_id": None, "name": "part-1"}
    ]


def test_insert_is_retrievable_when_it_triggers_partition_rotation(tmp_path):
    db = RowDB(tmp_path / "database")
    db.master.partition_size_limit = 1

    row_id = db.insert({"name": "Ada"})

    assert db.retrieve(row_id) == {"name": "Ada", "row_id": row_id}
    assert db.master.get_partition_by_row_id(row_id) == "part-1"
    assert db.master.get_active_partition() == "part-2"
    db.close()