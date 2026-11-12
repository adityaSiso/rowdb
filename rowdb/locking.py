"""Cross-process exclusive locking for a RowDB directory."""

import os

from .exceptions import DatabaseLockedException


class DatabaseLock:
    """Hold an OS-level exclusive lock for the lifetime of a RowDB handle."""

    def __init__(self, database_path):
        self.database_path = os.path.realpath(
            os.path.abspath(os.fspath(database_path))
        )
        os.makedirs(self.database_path, exist_ok=True)
        lock_path = os.path.join(self.database_path, ".rowdb.lock")
        self.file = open(lock_path, "a+b")  # noqa: SIM115
        self.locked = False

        try:
            # msvcrt locks a byte range, so ensure byte zero exists first.
            self.file.seek(0, os.SEEK_END)
            if self.file.tell() == 0:
                self.file.write(b"\0")
                self.file.flush()
            self.file.seek(0)

            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(
                    self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                )
            self.locked = True
        except OSError as error:
            self.file.close()
            self.file = None
            raise DatabaseLockedException(
                f"Database is already open: {self.database_path}"
            ) from error

    def close(self):
        """Release the lock and close its file handle. Safe to call twice."""
        if self.file is None:
            return

        try:
            if self.locked:
                self.file.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
        finally:
            self.file.close()
            self.file = None
            self.locked = False
