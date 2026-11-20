# Receipt row layout implementation plan

Goal: Persist a per-tally opt-out of HS grouping and display allocated original rows in receipt details and print, including existing receipts.
Architecture: Keep stored receipt groups and financial allocation unchanged. A dedicated layout preference table and permission-checked endpoints control a read-only source-row projection. Reuse receipt workflow preview allocation for legacy child receipts.
Tech stack: FastAPI, Oracle, React, Mantine, pytest, TypeScript.
Spec: User-approved design in this conversation (checkbox, persisted per tally, default grouped, existing receipts, allocated child quantities, unchanged totals).

## Constraints and review focus
- Never duplicate financial receipt records or weaken the HS uniqueness index.
- Projection must preserve quantity/document weight/weighbridge totals.
- Master receipts include all original rows; children include only allocated rows.
- Legacy children use the existing read-only preview allocation; standalone receipts remain grouped.
- Projected rows must not expose a delete action targeting the entire stored HS group.

## Tasks
- [x] Add failing projection tests for duplicate HS descriptions, partial and master allocations, empty selection, mismatched totals and immutability.
- [x] Add versioned migration 0006 for FA_TALLY_RECEIPT_LAYOUT, default off, foreign key and constrained yes/no value; add read/write layout endpoints with tally.view/tally.edit permissions and audited write serialized on tally header.
- [x] Implement receipt_layout.separate_lines and connect receipt details to existing preview_sources/source_rows with original metadata; verify totals before returning projected lines.
- [x] Add a small checkbox beside the goods heading, server-backed state and error handling, invalidate receipt detail/print/context queries after save.
- [x] Make projected row keys unique and hide grouped delete actions for projected rows.
- [x] Run targeted backend tests, TypeScript checking and diff review. No deployment or database migration execution.

## Validation and deployment
- Projection/persistence endpoint tests and TypeScript checks pass.
- Full Windows suite excludes test_backup_warehouse.py (requires Linux fcntl); other suite has 13 pre-existing failures, reproduced after loading HEAD versions of both changed router modules in memory. No source checkout or schema changes were needed for baseline verification.
- Apply migration 0006_receipt_row_layout.py through the existing versioned migration runner with a verified backup before starting the new backend. It creates only a layout preference table; existing tallies default to grouping until explicitly enabled.
- No database migration or production deployment was executed by this task. Browser print rendering still needs a live UI check after rollout.
