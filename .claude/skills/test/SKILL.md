---
name: test
description: Use this skill to run host-side unit tests. Triggers during TDD red/green cycles, before finishing a development branch, and when verifying logic changes. Tests compile with gcc and mock GBDK headers — no hardware required.
---

Run `make test`.

On success: report "Tests OK — N passed".

On failure: list each failing test with name, file:line, and expected vs
actual values. If compilation fails before tests run, show the gcc error
and identify which mock header or test file needs fixing.

New tests go in `tests/test_*.c` — the Makefile picks them up automatically.
Mock GBDK headers live in `tests/mocks/`.
