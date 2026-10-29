![RowDB logo](images/logo.svg)

<h1>RowDB</h1>

RowDB is an experimental, file-backed database library for Python. It stores collection data in newline-delimited JSON (NDJSON) files and is intended to provide a lightweight document-store interface without a separate database server.

<h2>Current status</h2>

The API is under development. The current implementation provides a `RowDB` class and an `NDJsonStorage` backend, but some operations are placeholders and the read/write behavior is not yet a complete key-value database. In particular, `insert_many` and `delete` are not implemented. Treat this version as a work in progress rather than production-ready storage.

<h2>Storage layout</h2>

Create a `RowDB` instance with a database directory and a collection filename. The storage backend creates the directory and file when needed. Collection filenames must end in `.ndjson`.

```text
my_database/
	users.ndjson
```

Each collection is intended to contain one JSON record per line.
