"""Utility functions for cricket scoring."""

from typing import Iterator, List, TypeVar


__all__ = ["chunked"]


T = TypeVar("T")


def chunked(items: List[T], chunk_size: int) -> Iterator[List[T]]:
    """Split a list into chunks of specified size.

    Example utility function to demonstrate package structure.

    Args:
        items: List to split into chunks
        chunk_size: Size of each chunk

    Yields:
        Lists containing up to chunk_size items

    Example:
        >>> list(chunked([1, 2, 3, 4, 5], 2))
        [[1, 2], [3, 4], [5]]
    """
    for i in range(0, len(items), chunk_size):
        yield items[i : i + chunk_size]
