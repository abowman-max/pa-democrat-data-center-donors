#!/usr/bin/env python3
"""Import selected Pennsylvania DOS campaign-finance records.

The candidate-to-filer decisions are deliberately read from the reviewed
research/candidate_mappings.json file. This script does not make fuzzy matches.
"""
import argparse
import collections
import csv
import datetime
import decimal
import io
import json
import pathlib
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=pathlib.Path, help="Folder containing 2016.zip through 2026.zip")
    parser.add_argument("work_dir", nargs="?", default="work", type=pathlib.Path)
    return parser.parse_args()


def main():
    args = parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    candidates = json.loads((ROOT / "research/candidate_mappings.json").read_text())
    (args.work_dir / "mapped.json").write_text(json.dumps(candidates, indent=2))

    filer_ids = {m["filer_id"].upper() for c in candidates for m in c["filers"]}
    filer_rows = []
    contribution_members = {}

    for year in range(2016, 2027):
        archive_path = args.input_dir / f"{year}.zip"
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            filer_name = next(n for n in names if "filer_" in n.lower())
            contribution_members[year] = next(n for n in names if "contrib_" in n.lower())
            with archive.open(filer_name) as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding="cp1252", errors="replace"))
                for row in reader:
                    row = {k: (v or "").strip() for k, v in row.items() if k is not None}
                    if row.get("FILERID", "").upper() in filer_ids:
                        filer_rows.append(row)

    groups = collections.defaultdict(list)
    for row in filer_rows:
        groups[(row["FILERID"].upper(), row["EYEAR"], row["CYCLE"])].append(row)

    selected = {}
    superseded = []
    for key, rows in groups.items():
        chosen = max(rows, key=lambda r: (r["SubmittedDate"], int(r["CampaignfinanceID"])))
        selected[chosen["CampaignfinanceID"]] = chosen
        for old in rows:
            if old["CampaignfinanceID"] != chosen["CampaignfinanceID"]:
                superseded.append({
                    "old": old["CampaignfinanceID"],
                    "selected": chosen["CampaignfinanceID"],
                    "filer": key[0],
                    "year": key[1],
                    "cycle": key[2],
                })

    counts = []
    errors = []
    sections = collections.Counter()
    output_path = args.work_dir / "transactions.jsonl"
    with output_path.open("w") as output:
        for year in range(2016, 2027):
            input_rows = selected_rows = transactions = malformed = 0
            archive_path = args.input_dir / f"{year}.zip"
            with zipfile.ZipFile(archive_path) as archive:
                member = contribution_members[year]
                with archive.open(member) as raw:
                    reader = csv.DictReader(io.TextIOWrapper(raw, encoding="cp1252", errors="replace"))
                    for record_number, row in enumerate(reader, 2):
                        input_rows += 1
                        report_id = row.get("CampaignFinanceID")
                        if report_id not in selected:
                            continue
                        if None in row or any(value is None for value in row.values()):
                            errors.append([year, record_number, "malformed"])
                            malformed += 1
                            continue
                        row = {k: v.strip() for k, v in row.items()}
                        if row["FilerID"].upper() != selected[report_id]["FILERID"].upper():
                            errors.append([year, record_number, "filer mismatch"])
                            malformed += 1
                            continue
                        selected_rows += 1
                        for slot in (1, 2, 3):
                            try:
                                cents = int(decimal.Decimal(row[f"CONTAMT{slot}"] or "0") * 100)
                            except decimal.InvalidOperation:
                                errors.append([year, record_number, f"bad amount slot {slot}"])
                                continue
                            if cents == 0:
                                continue
                            source_date = row[f"CONTDATE{slot}"]
                            try:
                                contribution_date = datetime.datetime.strptime(source_date, "%Y%m%d").date().isoformat()
                                date_valid = True
                            except ValueError:
                                contribution_date = source_date
                                date_valid = False
                            item = {
                                "report": report_id,
                                "filer": row["FilerID"].upper(),
                                "year": int(row["EYEAR"]),
                                "submitted": row["SubmittedDate"],
                                "cycle": row["CYCLE"],
                                "section": row["Section"],
                                "donor": row["CONTRIBUTOR"],
                                "city": row["CITY"],
                                "state": row["STATE"],
                                "occupation": row["OCCUPATION"],
                                "employer": row["ENAME"],
                                "date": contribution_date,
                                "date_valid": date_valid,
                                "cents": cents,
                                "description": row["CONTDESC"],
                                "archive": year,
                                "member": member,
                                "record": record_number,
                                "slot": slot,
                            }
                            output.write(json.dumps(item, separators=(",", ":")) + "\n")
                            transactions += 1
                            sections[row["Section"]] += 1
            counts.append({
                "year": year,
                "input_rows": input_rows,
                "selected_rows": selected_rows,
                "transactions": transactions,
                "malformed": malformed,
            })
            print(json.dumps(counts[-1]))

    selected_rows = list(selected.values())
    (args.work_dir / "selected_reports.json").write_text(json.dumps(selected_rows))
    (args.work_dir / "quality.json").write_text(json.dumps({
        "archives": counts,
        "superseded": superseded,
        "sections": dict(sections),
        "errors": errors,
    }, indent=2))
    print(json.dumps({
        "selected_reports": len(selected_rows),
        "superseded_reports": len(superseded),
        "transactions": sum(row["transactions"] for row in counts),
        "errors": len(errors),
    }))


if __name__ == "__main__":
    main()
