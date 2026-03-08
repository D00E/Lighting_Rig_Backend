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


def compare_files(path1: str | Path, path2: str | Path) -> tuple[int | None, int, int, str | None, str | None]:
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