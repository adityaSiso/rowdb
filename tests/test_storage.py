import json

import pytest

from rowdb.storage import JsonStorage, NDJsonStorage


def test_ndjson_storage_appends_records_on_separate_lines(tmp_path):
    with NDJsonStorage(tmp_path, "part-1") as storage:
        storage.write({"value": 1})
        storage.write([{"value": 2}, {"value": 3}])
        records = storage.read()

    assert [json.loads(record) for record in records] == [
        {"value": 1},
        {"value": 2},
        {"value": 3},
    ]


def test_ndjson_storage_returns_none_when_empty(tmp_path):
    with NDJsonStorage(tmp_path, "empty") as storage:
        assert storage.read() is None


def test_ndjson_storage_rejects_non_dictionary_records(tmp_path):
    with NDJsonStorage(tmp_path, "part-1") as storage, pytest.raises(
        TypeError, match="dictionary"
    ):
        storage.write([{"value": 1}, "invalid"])


def test_json_storage_replaces_existing_document(tmp_path):
    with JsonStorage(tmp_path, "master") as storage:
        storage.write({"state": "old", "padding": "long value"})
        storage.write({"state": "new"})
        assert storage.read() == {"state": "new"}
        assert storage.read("state") == "new"

    assert json.loads((tmp_path / "master.json").read_text()) == {"state": "new"}


def test_json_storage_preserves_old_document_if_replace_fails(
    tmp_path, monkeypatch
):
    storage = JsonStorage(tmp_path, "master")
    storage.write({"state": "old"})

    def fail_replace(_source, _destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("rowdb.storage.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        storage.write({"state": "new"})

    assert storage.read() == {"state": "old"}
    assert not storage.file.closed
    storage.close()


def test_json_storage_returns_none_when_empty(tmp_path):
    with JsonStorage(tmp_path, "empty") as storage:
        assert storage.read() is None


def test_json_storage_rejects_non_dictionary_data(tmp_path):
    with JsonStorage(tmp_path, "master") as storage, pytest.raises(
        TypeError, match="dictionary"
    ):
        storage.write([{"value": 1}])
