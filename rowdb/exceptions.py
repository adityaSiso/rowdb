class Exception(Exception):
    """Base class for exceptions in this module."""

class RowDBException(Exception):
    """Exception raised for errors in the RowDB operations."""

class MasterDataNotFoundException(RowDBException):
    """Exception raised when the master data is not found."""

class ActivePartitionNotFoundException(RowDBException):
    """Exception raised when the active partition is not found."""

class CorruptedMasterDataException(RowDBException):
    """Exception raised when the master data is found to be corrupted."""

class PartitionNotFoundException(RowDBException):
    """Exception raised when a specified partition is not found."""

class CorruptedPartitionDataException(RowDBException):
    """Exception raised when a partition's data is found to be corrupted."""

class RowNotFoundException(RowDBException):
    """Exception raised when a specified row is not found in the database."""


class DatabaseLockedException(RowDBException):
    """Exception raised when another RowDB instance owns the database lock."""
