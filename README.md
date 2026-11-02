<p align="center">
	<img src="images/logo.svg" alt="RowDB logo" width="420">
</p>

# RowDB

RowDB is an experimental, lightweight, file-based document database for Python. It stores records as newline-delimited JSON (NDJSON) and organizes them into partitions, with no separate database server required.

## Python Versions

RowDB requires Python `>=3.10,<3.14`.

## Usage

From the repository root, install RowDB and its development dependencies with:

```bash
uv sync
```

Run the example or other Python commands in the project environment with `uv run python`.

## Example

```python
from rowdb import RowDB

db = RowDB(db="my_database", partition_prefix="part-")

row_id = db.insert({"first_name": "John", "last_name": "Wick"})
record = db.retrieve(row_id)

row_ids = db.insert_many([
		{"first_name": "Jane", "last_name": "Doe"},
		{"first_name": "Alice", "last_name": "Smith"},
])
records = db.retrieve_all()

print(record)
print(row_ids)
print(records)
```

## Data and Flow

For the example above, RowDB creates a directory containing a master file and one or more partition files:

```text
my_database/
├── master.json
└── part-1.ndjson
```

`master.json` tracks the next row ID, the active partition, and the row ID range for each partition. Each line in a partition file is a JSON record with its assigned `row_id`. `insert()` and `insert_many()` append records; `retrieve(row_id)` uses the master metadata to find the partition, while `retrieve_all()` reads records from all registered partitions.

## Feedback and Contributions

RowDB is under active development. Bug reports, questions, ideas, and contributions are welcome. Please open an issue or pull request in this repository.
