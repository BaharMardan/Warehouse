# Receipt final checklist and invoices

The receipt detail page has a keeper checklist and a red invoice button.
New receipts appear automatically in the keeper queue. The first keeper review
on a tally remains available before initial receipt creation; receipts then
reopen service editing for the final checklist.

A general receipt is actionable only while there are no live detailed receipts.
When detailed receipts exist, the general receipt is a summary.

## Use

1. Complete service inputs on the linked tally, including carrier transportation answers.
2. For a detailed receipt, select the original tally rows and allocated quantities/weights in its checklist and save them. For a general receipt, all nonempty original rows are linked automatically.
3. For volumetric detailed receipts, enter the receipt's pallet quantity in the completion fields.
4. The keeper final-registers the receipt. The red invoice button then becomes available to users with `invoice.issue`.
5. Issuing an invoice saves it once; retries return the existing invoice.

The pallet field is retained. It is locked after final registration.

## Allocation and integrity

- Goods, groups, descriptions and storage prices are read from original tally rows through `FA_GHABZ_TALLY_SOURCE`. Receipt HS-grouped rows are used only to validate source ownership when preparing the checklist.
- Weight and container cargo use the original linked declared weight / total original tally declared weight.
- Volumetric cargo uses receipt pallets / total keeper-recorded tally pallets.
- A sole general receipt receives 100%.
- The first final checklist freezes shared service inputs and saves a tariff snapshot in `FA_RECEIPT_SERVICE_POOL`. Remaining receipts receive proportional shares of this same pool, even if tariff catalogs later change.
- Source allocations cannot overlap beyond original quantities/weights. Finalized ratios cannot exceed 100% in total.
- Service allocation uses cumulative rounding to whole rials; the rounding remainder is reconciled as invoices are issued.
- All mutations lock the same tally row. Invoice header, detail rows and status commit together.
- Tally goods/header edits are blocked once receipts exist. Keeper service edits stop after the first related receipt is finalized. Later detailed receipts can still be allocated from remaining original quantities.
- A finalized general receipt cannot later be converted into a summary by adding detailed receipts.
- Legacy invoices without allocation history are retained; further allocation on those tallies is blocked pending financial review.

## Deployment

Run `python migrate_receipt_checklist.py` from `backend` before using the updated API. The migration is rerunnable and includes the pallet-column prerequisite. Oracle DDL commits immediately.

Grant `invoice.issue` to billing roles. Final checklist and original-row selection use `tally.services`, which implies receipt viewing. Existing receipt editing permissions still control pallet entry.

## Verification

`python -B -m pytest -q -p no:cacheprovider tests/test_receipt_checklist.py tests/test_receipt_sources.py tests/test_ghabz_pallet_quantity.py tests/test_permissions.py tests/test_route_guards.py`

`python -B verify_receipt_checklist.py` performs four Oracle smoke scenarios in one rollback-only transaction: sole general, weighted detailed, volumetric detailed and container detailed. It checks automatic keeper availability, summary exclusion, service/pallet locks, 30/70 allocations, stable service costs after a tariff change, and idempotent invoice retries. Temporary business records are rolled back.
