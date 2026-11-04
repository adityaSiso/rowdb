<p align="center">
	<img src="images/logo.svg" alt="RowDB logo" width="420">
</p>

# RowDB

RowDB is a lightweight file-based document database built using pure Python. It stores records as newline-delimited JSON (NDJSON) objects and organizes them into partitions, it is intended for small applications that need simple, local document storage without the overhead of running a database server.

RowDB is:

- **Document-oriented:** Store records as Python dictionaries, each assigned a unique, sequential `row_id`.
- **Append-focused:** Inserts append records to NDJSON files, making RowDB suitable for workloads with frequent inserts.
- **Partitioned:** The default partition-rotation threshold is 4 Megabytes. Row ID ranges in the metadata select the partition for a lookup, which then scans that partition's records.

## Supported Python Versions

RowDB requires Python `>=3.10,<3.14`.

## Project Status

RowDB is under active development. Its core create and read operations, including single and batch inserts, retrieval by `row_id`, and retrieving all records, are stable and covered by tests. Update and delete operations are not yet available.

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
├── part-1.ndjson		# ~4MB
├── part-2.ndjson		# ~4MB
└── ...
```

`master.json` tracks the next row ID, the active partition, and the row ID range for each partition. Each line in a partition file is a JSON record with its assigned `row_id`. `insert()` and `insert_many()` append records; `retrieve(row_id)` uses the master metadata to find the partition, while `retrieve_all()` reads records from all registered partitions.

## Feedback and Contributions

RowDB is under active development. Bug reports, questions, ideas, and contributions are welcome. Please open an issue or pull request in this repository.
