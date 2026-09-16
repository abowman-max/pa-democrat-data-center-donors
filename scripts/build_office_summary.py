#!/usr/bin/env python3
"""Build compact candidate comparison totals for the static website."""
import collections
import json
import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"


def candidate_transactions(candidate_id):
    payload = json.loads((DATA / f"{candidate_id}.json").read_text())
    donors = payload.get("donors", [])
    if payload.get("parts"):
        donors = []
        for part in payload["parts"]:
            donors.extend(json.loads((DATA / part).read_text()))
    for donor in donors:
        yield from donor["transactions"]


def contribution_kind(row):
    if row["section"] in {"IIF", "IIG"}:
        return "inkind"
    if row.get("source") == "FEC" and re.search(
        r"IN[ -]?KIND", f"{row.get('memo_text', '')} {row.get('description', '')}", re.I
    ):
        return "inkind"
    return "cash"


def main():
    meta = json.loads((DATA / "index.json").read_text())
    candidates = []
    for candidate in meta["candidates"]:
        buckets = collections.defaultdict(lambda: [0, 0])
        for row in candidate_transactions(candidate["id"]):
            fields = {connection["field"] for connection in row["connections"]}
            key = (
                row.get("year"),
                contribution_kind(row),
                "contributor" in fields,
                "employer" in fields,
                bool(row.get("lead")),
            )
            buckets[key][0] += 1
            buckets[key][1] += row["cents"]
        candidates.append({
            "id": candidate["id"],
            "name": candidate["name"],
            "office_code": candidate["office_code"],
            "district_number": candidate["district_number"],
            "coverage": candidate["coverage"],
            "report_count": candidate["report_count"],
            "has_committee": candidate["has_committee"],
            "last_submitted": candidate["last_submitted"],
            "buckets": [
                {
                    "year": key[0],
                    "kind": key[1],
                    "dc_contributor": key[2],
                    "dc_employer": key[3],
                    "lead": key[4],
                    "count": totals[0],
                    "cents": totals[1],
                }
                for key, totals in sorted(buckets.items(), key=lambda item: str(item[0]))
            ],
        })
    output = {"as_of": meta["as_of"], "candidates": candidates}
    (DATA / "office-summary.json").write_text(json.dumps(output, separators=(",", ":")))
    print(f"Wrote office-summary.json for {len(candidates)} candidates")


if __name__ == "__main__":
    main()
