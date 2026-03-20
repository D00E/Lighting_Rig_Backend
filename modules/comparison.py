"""Utilities for comparing text file contents character by character.

Used primarily in tests to verify that processed payload output matches
expected reference files.
"""

from pathlib import Path


def read_text(path: Path) -> str:
    """Read a file's contents as a UTF-8 string, replacing undecodable bytes.

    Args:
        path: Absolute or relative path to the file.

    Returns:
        The file contents as a string.
    """
    return path.read_text(encoding="utf-8", errors="replace")


def find_first_mismatch(data1: str, data2: str) -> int | None:
    """Find the index of the first differing character between two strings.

    Args:
        data1: The first string to compare.
        data2: The second string to compare.

    Returns:
        The zero-based index of the first mismatch, or ``None`` if the strings
        are identical.
    """
    min_len = min(len(data1), len(data2))
    for index in range(min_len):
        if data1[index] != data2[index]:
            return index
    if len(data1) != len(data2):
        return min_len
    return None


def compare_text_content(data1: str, data2: str) -> tuple[int | None, int, int]:
    """Compare two strings and return mismatch details.

    Args:
        data1: The first string to compare.
        data2: The second string to compare.

    Returns:
        A three-tuple of ``(mismatch_index, len(data1), len(data2))``.
        ``mismatch_index`` is ``None`` when the strings are identical.
    """
    mismatch_index = find_first_mismatch(data1, data2)
    return mismatch_index, len(data1), len(data2)


def compare_files(path1: str | Path, path2: str | Path) -> tuple[int | None, int, int, str | None, str | None]:
    """Compare two text files and report the first point of divergence.

    Both paths are resolved to absolute paths before reading so that relative
    paths are handled correctly regardless of the working directory.

    Args:
        path1: Path to the first file (actual output).
        path2: Path to the second file (expected reference).

    Returns:
        A five-tuple of
        ``(mismatch_index, len1, len2, char_from_file1, char_from_file2)``.

        ``mismatch_index`` is the zero-based character index of the first
        difference, or ``None`` if the files are identical.
        ``len1`` and ``len2`` are the total character counts of each file.
        ``char_from_file1`` and ``char_from_file2`` are the differing
        characters at ``mismatch_index``, or ``None`` when the mismatch is
        a length difference.
    """
    file1 = Path(path1).resolve()
    file2 = Path(path2).resolve()

    data1 = read_text(file1)
    data2 = read_text(file2)

    mismatch_index, len1, len2 = compare_text_content(data1, data2)

    if mismatch_index is None:
        return None, len1, len2, None, None

    min_len = min(len1, len2)

    if mismatch_index < min_len:
        return (
            mismatch_index,
            len1,
            len2,
            data1[mismatch_index],
            data2[mismatch_index],
        )

    return mismatch_index, len1, len2, None, None