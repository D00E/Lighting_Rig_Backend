from pathlib import Path

import pytest

from modules.comparison import compare_files, compare_text_content


REPO_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_SAMPLES_DIR = REPO_ROOT / "tests" / "payload_samples"
CASE_DIRS = sorted(
    [path for path in PAYLOAD_SAMPLES_DIR.iterdir() if path.is_dir() and path.name.startswith("case_")]
)


def test_payload_samples_cases_exist():
    assert CASE_DIRS, f"No payload case directories found in {PAYLOAD_SAMPLES_DIR}"


def test_identical_text_content():
    result = compare_text_content("abc", "abc")
    assert result == (None, 3, 3)


def test_detects_first_mismatch():
    result = compare_text_content("abc", "axc")
    assert result == (1, 3, 3)


def test_detects_length_mismatch():
    result = compare_text_content("abc", "abcd")
    assert result == (3, 3, 4)


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=[path.name for path in CASE_DIRS])
def test_payload_comparison_case(case_dir: Path):
    actual = case_dir / "actual_payload.txt"
    expected = case_dir / "expected_payload.txt"

    assert actual.exists(), f"Missing actual payload file: {actual}"
    assert expected.exists(), f"Missing expected payload file: {expected}"

    mismatch_index, len1, len2, char1, char2 = compare_files(actual, expected)

    assert mismatch_index is None, (
        f"Payload mismatch at index {mismatch_index}: "
        f"actual={repr(char1)}, expected={repr(char2)}, "
        f"actual_length={len1}, expected_length={len2}"
    )