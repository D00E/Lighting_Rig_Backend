# How to Test

## Payload Comparison
1. Create a case folder in `tests/payload_samples` named like `case_001`, `case_002`, etc.
2. Add `actual_payload.txt` to the case folder.
3. Add `expected_payload.txt` to the case folder.
4. Run the tests from the project root: `pytest tests/test_payload_comparison.py`.

## Notes
1. The suite auto-discovers all folders beginning with `case_`.
2. Every discovered case must include both payload files, otherwise the test will fail.
3. Payloads are compared character-by-character, and the first mismatch is reported.