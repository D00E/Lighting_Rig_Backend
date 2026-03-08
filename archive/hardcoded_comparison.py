#!/usr/bin/env python3

from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def find_first_mismatch(data1: str, data2: str) -> int | None:
    min_len = min(len(data1), len(data2))
    for index in range(min_len):
        if data1[index] != data2[index]:
            return index
    if len(data1) != len(data2):
        return min_len
    return None


def compare_text_content(data1: str, data2: str) -> tuple[int | None, int, int]:
    mismatch_index = find_first_mismatch(data1, data2)
    return mismatch_index, len(data1), len(data2)


def compare_files(path1: str | Path, path2: str | Path) -> None:
    file1 = Path(path1).resolve()
    file2 = Path(path2).resolve()

    data1 = read_text(file1)
    data2 = read_text(file2)

    mismatch_index, len1, len2 = compare_text_content(data1, data2)

    print("Comparing:")
    print(" ", file1)
    print(" ", file2)
    print()

    if mismatch_index is None:
        print("Files are identical (all characters match and lengths are equal).")
        return

    min_len = min(len1, len2)

    if mismatch_index < min_len:
        print(f"Mismatch at index {mismatch_index}:")
        print(f"  {file1.name}[{mismatch_index}] = {repr(data1[mismatch_index])}")
        print(f"  {file2.name}[{mismatch_index}] = {repr(data2[mismatch_index])}")
        return

    print("Files match for the first", min_len, "characters,")
    print("but lengths differ:")
    print(f"  {file1.name} length = {len1}")
    print(f"  {file2.name} length = {len2}")
    print(f"First mismatch is at index {min_len} (one file ends there).")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]

    actual = repo_root / "tests/payload_comparison/case_001/actual_payload.txt"
    expected = repo_root / "tests/payload_comparison/case_001/expected_payload.txt"

    compare_files(actual, expected)