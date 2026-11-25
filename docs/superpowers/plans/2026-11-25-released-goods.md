# Released goods report
User-approved scope: in income reports, list goods released by active original invoices issued in the selected inclusive period. Partial receipts include only their source allocations; totals count unique tallies and insurance once per tally. Columns include invoice/tally identity, HS, original description, owner, warehouse/location, kg, pallets, issue date, proportional customs value and insurance. Include CSV and print.

- Add pure released-goods projection tests before implementing.
- Read active original invoices by issue date; reuse source_rows/preview_sources for read-only allocation and original metadata; exclude remaining invoices and cancelled invoices.
- Customs value follows existing invoice weight/pallet/quantity allocation rules. Exact receipt pallets take precedence; flag estimates and unknown insurance. Surface unresolvable legacy receipts explicitly rather than silently losing them.
- Add reports.income endpoint, date/owner-aware UI section with unique-tally cards and links, CSV and print route.
- Verify pure allocation tests, Oracle read queries, TypeScript/build and existing report tests. No automatic deployment.

## Completed verification
- 104 related backend tests pass, including date boundaries, cancellation/remaining-invoice exclusion, partial allocations, zero-weight row pallet/quantity shares, duplicate insurance, unknown owner and invoice-buyer fallback.
- Oracle read-only endpoint verified on local HR: 77 goods rows, 27 unique tallies, 27 invoices, no unresolved allocations in the broad test period.
- TypeScript and production frontend build pass. Independent review findings on zero-weight customs allocation and owner filtering were corrected.
- Ruling: for zero-weight goods, prefer the exact original-row pallet share or source quantity share, not the whole tally pallet ratio. A whole-tally fallback remains only when neither row basis exists, consistent with old invoice behavior; estimated pallets are flagged.
- No migration, production deployment or database mutation was performed. Printed browser layout not visually exercised.
