#!/usr/bin/env python3
"""Validate the published static snapshot and evidence packet."""
import csv
import json
import pathlib
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA = DOCS / "data"
SENSITIVE_KEYS = {"address", "address1", "address2", "street", "phone", "zipcode", "zip"}
MAX_BYTES = 8 * 1024 * 1024


def load_candidate(candidate_id):
    path = DATA / f"{candidate_id}.json"
    assert path.exists(), f"missing candidate file: {path.name}"
    payload = json.loads(path.read_text())
    if payload.get("parts"):
        fragments = []
        for part in payload["parts"]:
            part_path = DATA / part
            assert part_path.exists(), f"missing candidate part: {part}"
            assert part_path.stat().st_size < MAX_BYTES, f"candidate part exceeds 8 MiB: {part}"
            fragments.extend(json.loads(part_path.read_text()))
        donors = {}
        for donor in fragments:
            if donor["id"] not in donors:
                donors[donor["id"]] = {**donor, "transactions": []}
            donors[donor["id"]]["transactions"].extend(donor["transactions"])
        payload["donors"] = list(donors.values())
    return payload


def scan_keys(value, path="root"):
    if isinstance(value, dict):
        for key, child in value.items():
            assert key.lower() not in SENSITIVE_KEYS, f"sensitive published key {key!r} at {path}"
            scan_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_keys(child, f"{path}[{index}]")


def main():
    meta = json.loads((DATA / "index.json").read_text())
    office_summary = json.loads((DATA / "office-summary.json").read_text())
    summary_candidates = {candidate["id"]: candidate for candidate in office_summary["candidates"]}
    assert len(meta["candidates"]) == meta["unique_candidates"] == 230
    assert len(summary_candidates) == 230
    assert len({c["id"] for c in meta["candidates"]}) == 230
    entity_ids = {entity["id"] for entity in meta["entities"]}
    assert len(entity_ids) == len(meta["entities"]) == 44
    total_transactions = 0
    federal_transactions = 0
    documented_associations = 0
    donor_groups = 0
    for candidate in meta["candidates"]:
        payload = load_candidate(candidate["id"])
        assert payload["candidate"]["id"] == candidate["id"]
        assert payload["candidate"]["transaction_count"] == sum(
            len(donor["transactions"]) for donor in payload["donors"]
        )
        assert payload["candidate"]["donor_count"] == len(payload["donors"])
        assert sum(bucket["count"] for bucket in summary_candidates[candidate["id"]]["buckets"]) == payload["candidate"]["transaction_count"]
        report_ids = {str(report["CampaignfinanceID"]) for report in payload["reports"]}
        for donor in payload["donors"]:
            for transaction in donor["transactions"]:
                assert isinstance(transaction["cents"], int)
                assert transaction["cents"] != 0
                if transaction.get("source") == "FEC":
                    assert transaction["section"] in {"FEC-11AI", "FEC-11B", "FEC-11C", "FEC-11D"}
                    assert transaction["filing_url"].startswith("https://")
                    federal_transactions += 1
                else:
                    assert str(transaction["report"]) in report_ids
                for association in transaction["connections"]:
                    assert association["entity"] in entity_ids
                    documented_associations += 1
        total_transactions += payload["candidate"]["transaction_count"]
        donor_groups += len(payload["donors"])
        scan_keys(payload)

    assert total_transactions == meta["total_transactions"]
    assert federal_transactions == meta["federal_transactions"]
    federal_candidates = [candidate for candidate in meta["candidates"] if candidate["office_code"] == "USC"]
    assert len(federal_candidates) == 17
    assert all(candidate.get("fec_candidate_id") and not candidate["federal_gap"] for candidate in federal_candidates)
    assert all(any(filer.get("type") == "FEC" for filer in candidate["filers"]) for candidate in federal_candidates)

    with (ROOT / "research/all_donors.csv").open(newline="") as handle:
        all_donor_rows = sum(1 for _ in csv.DictReader(handle))
    with (ROOT / "research/documented_connections.csv").open(newline="") as handle:
        connection_rows = sum(1 for _ in csv.DictReader(handle))
    assert all_donor_rows == donor_groups
    assert connection_rows == documented_associations

    packet = DOCS / "evidence/source-packet.zip"
    assert packet.exists()
    with zipfile.ZipFile(packet) as archive:
        members = set(archive.namelist())
        required = {"source-register.pdf", "source-register.csv", "README.txt", "original-pdf-checksums.json"}
        assert required.issubset(members), f"evidence packet missing {required - members}"
        for original in ("ppl.pdf", "babst.pdf", "project-washington-original.pdf"):
            assert original in members

    pdf_path = DOCS / "evidence/source-register.pdf"
    assert pdf_path.exists() and pdf_path.stat().st_size > 10_000
    for path in DATA.glob("*.json"):
        assert path.stat().st_size < MAX_BYTES, f"published JSON exceeds 8 MiB: {path.name}"

    print(json.dumps({
        "status": "pass",
        "candidates": len(meta["candidates"]),
        "transactions": total_transactions,
        "federal_transactions": federal_transactions,
        "donor_groups": donor_groups,
        "documented_associations": documented_associations,
        "entities": len(entity_ids),
        "coverage_gaps": len(meta["coverage_gaps"]),
        "superseded_reports": meta["superseded_report_count"],
    }, indent=2))


if __name__ == "__main__":
    main()
