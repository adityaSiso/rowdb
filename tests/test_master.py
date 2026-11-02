import json

import pytest

from rowdb import RowDB
from rowdb.exceptions import (
    ActivePartitionNotFoundException,
    MasterDataNotFoundException,
    PartitionNotFoundException,
)


@pytest.fixture
def db(tmp_path):
    database = RowDB(tmp_path / "database")
    yield database
    database.close()


def test_master_initializes_metadata_and_first_partition(db):
    assert db.master.master_data == {
        "active_partition": "part-1",
        "partitions": [
            {"start_row_id": 0, "end_row_id": None, "name": "part-1"}
        ],
        "next_row_id": 0,
    }
    assert db.master.row_id == 0
    assert db.master.get_total_partitions() == 1


def test_master_migrates_legacy_partition_dictionary(tmp_path):
    database_path = tmp_path / "database"
    db = RowDB(database_path)
    db.close()
    (database_path / "master.json").write_text(json.dumps({
        "active_partition": "part-7",
        "partitions": {},
        "next_row_id": 12,
    }))

    migrated = RowDB(database_path)
    assert migrated.master.master_data["partitions"] == [
        {"start_row_id": 0, "end_row_id": None, "name": "part-7"}
    ]
    assert migrated.master.row_id == 12
    migrated.close()


@pytest.mark.parametrize(
    ("value", "error_type", "message"),
    [("1", TypeError, "integer"), (-1, ValueError, "non-negative")],
)
def test_row_id_setter_rejects_invalid_values(db, value, error_type, message):
    with pytest.raises(error_type, match=message):
        db.master.row_id = value


def test_row_id_setter_rejects_decreasing_by_more_than_one(db):
    db.master.advance_row_id(3)

    with pytest.raises(ValueError, match="incremented by 1"):
        db.master.row_id = 1


@pytest.mark.parametrize("count", ["1", -1])
def test_advance_row_id_rejects_invalid_counts(db, count):
    with pytest.raises(ValueError, match="count"):
        db.master.advance_row_id(count)


def test_advance_row_id_zero_is_a_no_op(db):
    db.master.advance_row_id(0)
    assert db.master.row_id == 0


def test_advance_row_id_rotates_full_partition(db):
    db.master.partition_size_limit = 0

    db.master.advance_row_id(2)

    assert db.master.row_id == 2
    assert db.master.master_data["partitions"] == [
        {"start_row_id": 0, "end_row_id": 2, "name": "part-1"},
        {"start_row_id": 2, "end_row_id": None, "name": "part-2"},
    ]
    assert db.master.get_active_partition() == "part-2"


def test_get_active_partition_returns_none_when_unset(db):
    db.master.master_data["active_partition"] = None
    db.master.storage.write(db.master.master_data)

    assert db.master.get_active_partition() is None


def test_partition_lookups_handle_ranges_and_missing_metadata(db):
    assert db.master.get_partition_by_row_id(0) == "part-1"
    assert db.master.get_partition_by_row_id(10) == "part-1"
    assert db.master.get_partition_by_row_id(-1) is None

    db.master.master_data["partitions"] = None
    with pytest.raises(MasterDataNotFoundException):
        db.master.get_partition_by_row_id(0)
    with pytest.raises(PartitionNotFoundException):
        db.master.get_total_partitions()


def test_update_partition_search_key_closes_active_range(db):
    db.master.advance_row_id(3)

    db.master.update_partition_search_key()

    assert db.master.master_data["partitions"][0]["end_row_id"] == 3


def test_update_partition_search_key_rejects_missing_active_partition(db):
    db.master.master_data["active_partition"] = None
    db.master.storage.write(db.master.master_data)

    with pytest.raises(ActivePartitionNotFoundException, match="not set"):
        db.master.update_partition_search_key()


def test_update_partition_search_key_rejects_missing_partition_metadata(db):
    db.master.master_data["partitions"] = None
    db.master.storage.write(db.master.master_data)

    with pytest.raises(MasterDataNotFoundException):
        db.master.update_partition_search_key()


def test_update_partition_search_key_rejects_unknown_active_partition(db):
    db.master.master_data["partitions"] = []
    db.master.storage.write(db.master.master_data)

    with pytest.raises(ActivePartitionNotFoundException, match="not found"):
        db.master.update_partition_search_key()


def test_partition_size_limit_check(db):
    assert db.master.is_partition_size_limit_reached() is False

    db.master.partition_size_limit = 0
    assert db.master.is_partition_size_limit_reached() is True


def test_partition_size_check_rejects_missing_master_data(db, monkeypatch):
    monkeypatch.setattr(db.master.storage, "read", lambda key=None: None)

    with pytest.raises(MasterDataNotFoundException):
        db.master.is_partition_size_limit_reached()