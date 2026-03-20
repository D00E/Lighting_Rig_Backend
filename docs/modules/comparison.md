# Comparison Module

The `modules.comparison` module provides utilities for comparing two text files
character by character. It is used in the test suite to verify that processed
packet output matches expected reference files exactly.

## Overview

The comparison pipeline works in three stages:

1. **Read** – both files are loaded as UTF-8 strings via `read_text`.
2. **Locate** – `find_first_mismatch` scans character by character for the
   first divergence.
3. **Report** – `compare_files` and `compare_text_content` return the mismatch
   index, file lengths, and the differing characters for easy diagnosis.

## API Reference

::: modules.comparison
