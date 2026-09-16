# Methodology and evidence standard

## Scope

The candidate population is the supplied `2026 Democrat Candidates.xlsx` workbook. Two duplicate candidate-office-district rows were consolidated, producing 230 unique records. District and office labels describe the 2026 roster even when a matched filer contains activity from an earlier campaign.

The contribution sources are the user-supplied Pennsylvania Department of State annual archives for 2016 through 2026 and official Federal Election Commission records. The supplied DOS readme was treated as the state schema authority. It describes filer records and contribution sections, including up to three date-and-amount slots on one CSV row.

## Report selection

For each matched filer, election year, and reporting cycle, the import selects the filing with the latest `SubmittedDate`; a larger `CampaignfinanceID` breaks a tie. This excludes 44 older versions from the current snapshot. The selection prevents amended and original versions from being added together.

Every nonzero contribution slot in a selected row becomes a separate transaction. The source trail retains the archive year, member filename, CSV record number, amount-slot number, filer ID, and report ID. One malformed 2023 CSV row was excluded. Three entries with blank section codes remain visible as `Unknown` rather than being forced into cash or in-kind.

## Candidate and committee mapping

Candidate names were normalized for punctuation and reviewed against DOS filer names. Candidate filer records and clearly attributable political committees were mapped explicitly in `research/candidate_mappings.json`. Ambiguous committees were not assigned. Coverage notices identify candidates with no matched reports, candidate-only matches, or federal-office gaps.

The 17 U.S. House candidates were matched to current FEC candidate IDs by name, office, state, and district. Official FEC candidate-committee linkage files for the 2016–2026 cycles identify 18 principal or additional authorized committees. The site includes processed Schedule A contribution records for those committees from January 1, 2016 through September 15, 2026. Any separately matched historical Pennsylvania filings for those candidates remain included and are labeled by source.

Federal contribution records are limited to Form 3 Schedule A lines 11AI, 11B, 11C, and 11D: itemized individuals, party committees, other political committees, and candidate contributions. Memoed subtotals are excluded so a conduit total is not added to the underlying donor transactions. Unitemized receipts, transfers, loans, offsets, other receipts, refunds, debts, and spending are outside the donor report. The FEC processed-data service governs amendments and transaction replacements. Street addresses and ZIP codes are removed before publication.

## Donor grouping and amounts

The donor table groups records by normalized contributor name plus reported city and state. This is a display convenience, not an identity-resolution claim. Individual source records remain available in the detail view.

Cash is defined as Pennsylvania sections IA, IB, IC, and ID and federal contribution entries without an in-kind notation. In-kind is defined as Pennsylvania sections IIF and IIG or a federal contribution explicitly described as in-kind. Amounts remain integer cents until display or CSV export. Zero-amount slots are omitted. Signed negative adjustments are retained and reduce displayed sums. Identical-looking entries within a selected filing are retained because the source does not establish that they are duplicates.

## Data-center connection standard

An organization enters the reviewed registry only when a public source documents a material connection to a data center. Qualifying relationships include ownership, operation, development, construction, power supply, legal representation, financing, organized-labor project agreements, or another specific project role. Each registry row records the claim, relationship category, geography, publication title, evidence date, source URL, aliases, and review date.

The registry also includes contributions from Pennsylvania lawmakers and campaign committees tied to lawmakers recorded as voting Yea on HB 952 PN 1934. The June 25, 2021 House concurrence roll call recorded 170 yeas, and the Senate final-passage roll call recorded 46 yeas. HB 952 was enacted as Act 25 of 2021 and created a sales and use tax exemption for computer data center equipment. This category uses the reported contributor field only. It does not match employer fields.

The roll calls identify most members by surname, with initials where needed. A donor is assigned to this category only through a reviewed full personal name or a campaign-committee name that clearly identifies the voter. Generic surnames and ambiguous names are excluded. `research/hb952_rollcall_aliases.json` preserves the complete extracted Yea lists, reviewed aliases, matched donor spellings, and the exclusion rule. A match establishes the donor lawmaker's recorded vote or the identified committee's tie to that lawmaker. It does not establish why the contribution was made or the recipient candidate's position on the bill or tax exemption.

Contribution associations use exact normalized aliases in either:

1. the reported contributor or PAC/organization name; or
2. the reported employer field.

Fuzzy matching is intentionally disabled. A special rule keeps an IBEW local from also matching the national IBEW alias unless the national organization is named separately.

An organization-name match supports an association with that organization. An employer match reports only what the campaign-finance record says about the donor’s employer. Neither establishes that an individual donor worked on a project, endorsed it, owned land, benefited financially, or shared the organization’s position. Dates matter: a contribution can precede the cited connection.

The `Unverified research leads` view uses a limited keyword screen to surface possible follow-up work. Those records are excluded from documented totals and should not be published as established connections without additional evidence and an explicit registry entry.

## Evidence packet

`docs/evidence/source-register.pdf` is an authored index with clickable links and concise claims; it is not an original publication. Where an original public PDF was available, the packet includes it and records its SHA-256 checksum. Link-only entries remain in the register because many authoritative sources are web pages rather than PDFs. The source URL is the controlling reference if an archived copy and the live page differ.

## Reproducibility and review

`scripts/import_dos.py` reads the annual Pennsylvania ZIP archives, applies the fixed filer mappings, selects the current filing version, and writes normalized transaction records. `scripts/add_hb952_connections.py` verifies the supplied roll-call PDFs and updates the reviewed lawmaker aliases and audit file. `scripts/build_data.py` applies the reviewed connection registry and produces the state website snapshot. `scripts/import_fec.py` downloads the official linkage files and processed Schedule A extracts, applies the same reviewed aliases, strips address fields, and merges federal and state records. `scripts/split_large_data.py` keeps large candidate data compatible with GitHub hosting. `scripts/validate.py` checks file coverage, transaction reconciliation, integer amounts, evidence references, federal line types, privacy-sensitive fields, packet contents, and maximum data-file size.

The registry is a documented starting point, not a claim of completeness. Data-center ownership, contractors, utilities, lobbyists, unions, land interests, and corporate names change. New research should be added only with a source and a narrowly reviewed alias.
