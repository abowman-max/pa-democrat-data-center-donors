# Pennsylvania Democratic candidate donor explorer

## Open the explorer

**[Launch the live donor explorer](https://abowman-max.github.io/pa-democrat-data-center-donors/)**

In the explorer:

1. Choose an **office** and **All candidates** to compare the full 2026 roster for that office by contribution count and amount.
2. Choose **All donors** or **Data-center connections** to change the comparison totals, then optionally narrow by year, contribution type, or connection basis.
3. Sort either table by amount, contribution count, or name; then select **View donors** beside a candidate to drill into that candidate's donor records and source links.
4. Use **Export table** or **Export contributions** to download the current filtered report.

The website files are in `docs/`. A root `index.html` also redirects to that folder for hosts that publish the repository root.

This repository is a portable, static research tool for reviewing itemized Pennsylvania campaign-finance contributions associated with the 2026 Democratic candidate roster supplied for this project. It lets a reader choose an office, district, and candidate; switch between all itemized donors, documented data-center associations, and unverified research leads; inspect each source transaction; and export the current view.

Open the published site through GitHub Pages or serve the `docs/` folder locally. The browser cannot reliably load the data files when `index.html` is opened directly from disk.

## Publish on GitHub Pages

1. Create a new GitHub repository and upload this folder.
2. In the repository, open **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Select the main branch and the `/docs` folder, then save.

The site has no server, database, tracking code, or build step. All published records are under `docs/`.

## What is included

- 230 unique candidate, office, and district records from the supplied 2026 workbook.
- 601,558 itemized contribution entries: 390,126 from the supplied Pennsylvania archives and 211,432 official FEC Schedule A contribution records.
- 44 reviewed organizations with documented data-center connections, plus the House and Senate HB 952 Yea-voter registries.
- 8,652 contribution-to-connection associations identified by an exact reviewed name or reported-employer alias. This includes 2,702 contribution entries from clearly identified lawmakers and campaign committees that voted for HB 952.
- Direct links from each contribution to its campaign-finance source and to the evidence supporting each documented connection.
- A downloadable evidence packet in `docs/evidence/source-packet.zip`.

Money is stored as integer cents in the website data. Pennsylvania cash includes DOS sections IA, IB, IC, and ID; in-kind contributions include sections IIF and IIG. Federal records include processed FEC Schedule A contribution lines 11AI, 11B, 11C, and 11D. Memoed subtotals are excluded to avoid counting conduit totals on top of the underlying contributions.

## Important limits

This is a research index, not a finding that every matched donor personally supports a data-center project. An association can arise because the contribution name is a reviewed organization or PAC, because an individual reported a reviewed organization as an employer, or because the donor is a clearly identified lawmaker or campaign committee whose legislator voted Yea on HB 952. The evidence establishes the cited connection; it does not establish why a contribution was made, the recipient candidate's position, or wrongdoing. Contributions can predate the cited evidence.

The 17 U.S. House candidates are linked to 18 authorized committees through official FEC candidate-committee linkage files. Their processed Schedule A records cover January 1, 2016 through September 15, 2026. Unitemized federal receipts, transfers, loans, other receipts, refunds, debts, and spending are outside this donor report. Some state candidates lack a confidently matched campaign committee. The interface shows coverage warnings rather than treating missing records as zero activity. Unitemized contributions and records with blank employer fields cannot be connected to a donor through this method.

Names are matched only against reviewed aliases. The tool does not use fuzzy matching. Donor rollups use normalized contributor name plus reported city and state; similar spellings stay separate, while different people with the same reported fields can be grouped. Amounts sum signed itemized entries, so negative adjustments reduce displayed totals. Transfers among matched filers can still appear more than once.

See [METHODOLOGY.md](METHODOLOGY.md) for the selection rules, evidence standard, and reproducibility notes.

## Repository layout

- `docs/` — GitHub Pages website and compact candidate-level data files.
- `docs/evidence/` — evidence register, available original PDFs, checksums, and source packet.
- `research/entities.json` — reviewed entity aliases, connection claims, evidence dates, and URLs.
- `research/hb952_rollcall_aliases.json` — full roll-call names, reviewed lawmaker aliases, matched donor names, and exclusions for the HB 952 vote connection.
- `research/all_donors.csv` — candidate-level donor rollups for audit and analysis.
- `research/documented_connections.csv` — every published contribution-to-entity association.
- `research/candidate_mappings.json` — candidate-to-filer mapping decisions and coverage status.
- `research/fec_candidate_mappings.json` — reviewed FEC candidate IDs and official authorized-committee linkages.
- `research/coverage_gaps.json` — candidates whose coverage is known to be incomplete.
- `research/superseded_reports.json` — excluded older versions of reports.
- `scripts/` — repeatable import, build, split, and validation utilities.

## Refresh from DOS archives

The data refresh uses Python 3. Rebuilding the HB 952 roll-call audit also requires Poppler's `pdftotext` utility; rebuilding the authored PDF source register requires the PDF dependencies described in the project workflow.

```bash
python3 scripts/import_dos.py "/path/to/Raw Data (DOS)" work
python3 scripts/add_hb952_connections.py
python3 scripts/build_data.py work
python3 scripts/import_fec.py
python3 scripts/split_large_data.py
python3 scripts/build_office_summary.py
python3 scripts/validate.py
```

The reviewed filer mappings and entity aliases remain explicit files under `research/`; refreshes do not silently invent new candidate or data-center matches. Review them when the candidate roster or source evidence changes.

## License

Code and original documentation in this repository are released under the MIT License. Source campaign-finance records and third-party evidence retain their original terms and attribution.
