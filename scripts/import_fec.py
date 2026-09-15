#!/usr/bin/env python3
"""Download and merge official FEC Schedule A records for the 2026 U.S. House roster.

This uses the FEC's public candidate-committee linkage files and processed
Schedule A export service. Published JSON excludes street addresses and ZIPs.
"""
import argparse
import collections
import csv
import decimal
import hashlib
import html
import json
import os
import pathlib
import re
import subprocess
import time
import urllib.parse
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/data"
WORK_DEFAULT = ROOT.parent.parent / "work/fec"
FEC_IDS = {
    "c014": "H6PA15181", "c023": "H4PA13199", "c025": "H6PA14200",
    "c029": "H6PA07188", "c043": "H6PA08293", "c054": "H8PA04116",
    "c058": "H2PA17103", "c069": "H4PA13298", "c103": "H6PA01181",
    "c110": "H8PA06087", "c134": "H2PA18200", "c143": "H6PA11099",
    "c179": "H6PA03203", "c192": "H8PA07200", "c207": "H4PA10104",
    "c215": "H6PA16379", "c217": "H6PA09127",
}
CONTRIBUTION_LINES = {"11AI", "11B", "11C", "11D"}


def run_curl(url, output=None, method=None, body=None):
    command = ["curl", "-sS", "--retry", "3", "--retry-delay", "2"]
    if method:
        command += ["-X", method]
    if body is not None:
        command += ["-H", "Content-Type: application/json", "--data", json.dumps(body)]
    command.append(url)
    if output:
        command += ["-o", str(output)]
        subprocess.run(command, check=True)
        return None
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def get_download_key():
    if os.environ.get("FEC_DOWNLOAD_API_KEY"):
        return os.environ["FEC_DOWNLOAD_API_KEY"]
    page = run_curl("https://www.fec.gov/data/receipts/?data_type=processed")
    match = re.search(r"DOWNLOAD_API_KEY\s*=\s*'([^']+)'", page)
    if not match:
        raise RuntimeError("The FEC public download key was not found on the receipts page")
    return match.group(1)


def ensure_linkage_files(work):
    bulk = work / "bulk"
    bulk.mkdir(parents=True, exist_ok=True)
    for cycle in range(2016, 2027, 2):
        short = str(cycle)[-2:]
        path = bulk / f"ccl{short}.zip"
        if not path.exists() or not zipfile.is_zipfile(path):
            run_curl(f"https://www.fec.gov/files/bulk-downloads/{cycle}/ccl{short}.zip", path)
    return bulk


def read_linkages(bulk):
    candidate_by_fec = {value: key for key, value in FEC_IDS.items()}
    committees = collections.defaultdict(dict)
    for path in sorted(bulk.glob("ccl*.zip")):
        with zipfile.ZipFile(path) as archive:
            member = archive.namelist()[0]
            lines = (line.decode("cp1252") for line in archive.open(member))
            for row in csv.reader(lines, delimiter="|"):
                if len(row) < 7 or row[0] not in candidate_by_fec or row[5] not in {"P", "A"}:
                    continue
                candidate_key = candidate_by_fec[row[0]]
                committees[candidate_key][row[3]] = {
                    "committee_id": row[3], "committee_type": row[4],
                    "designation": row[5], "candidate_id": row[0],
                }
    missing = sorted(set(FEC_IDS) - set(committees))
    if missing:
        raise RuntimeError(f"No FEC candidate-committee linkage found for: {missing}")
    return committees


def export_committee(committee_id, work, api_key, max_date):
    raw = work / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    path = raw / f"{committee_id}.csv"
    if path.exists() and path.stat().st_size > 100:
        return path
    params = [
        ("api_key", api_key), ("committee_id", committee_id),
        ("min_date", "01/01/2016"), ("max_date", max_date),
    ]
    endpoint = "https://api.open.fec.gov/v1/download/schedules/schedule_a/?" + urllib.parse.urlencode(params)
    filename = f"{committee_id}-schedule-a.csv"
    response = json.loads(run_curl(endpoint, method="POST", body={"filename": filename}))
    task_id = response.get("task_id")
    for _ in range(360):
        if response.get("status") == "complete":
            break
        if response.get("status") not in {"queued", None} or not task_id:
            raise RuntimeError(f"FEC export failed for {committee_id}: {response}")
        time.sleep(3)
        response = json.loads(run_curl(endpoint, method="POST", body={"filename": filename, "task_id": task_id}))
    else:
        raise RuntimeError(f"FEC export timed out for {committee_id}")
    run_curl(response["url"], path)
    return path


def norm(value):
    value = html.unescape(str(value or "")).upper().replace("'", "").replace("’", "")
    return re.sub(r"[^A-Z0-9]+", " ", value).strip()


def alias_present(text, alias):
    return f" {alias} " in f" {text} "


def load_candidate(candidate_id):
    path = DATA / f"{candidate_id}.json"
    payload = json.loads(path.read_text())
    if payload.get("parts"):
        fragments = [
            donor for part in payload["parts"]
            for donor in json.loads((DATA / part).read_text())
        ]
        merged = {}
        for donor in fragments:
            if donor["id"] not in merged:
                merged[donor["id"]] = {**donor, "transactions": []}
            merged[donor["id"]]["transactions"].extend(donor["transactions"])
        payload["donors"] = list(merged.values())
    return payload


def match_entities(value, entities):
    text = norm(value)
    matches = []
    for entity in entities:
        if entity["id"] == "ibew" and re.search(r"\b(LOCAL|LU|L U)\s*\d", text):
            continue
        if any(alias_present(text, alias) for alias in entity["_aliases"]):
            matches.append(entity["id"])
    return matches


def parse_committee(path, entities):
    rows = []
    committee_name = path.stem
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for source_row, row in enumerate(csv.DictReader(handle), 2):
            committee_name = row.get("committee_name") or committee_name
            line = (row.get("line_number") or "").upper()
            if line not in CONTRIBUTION_LINES:
                continue
            if (row.get("memoed_subtotal") or "").lower() in {"t", "true", "1", "y", "yes"}:
                continue
            try:
                cents = int(decimal.Decimal(row.get("contribution_receipt_amount") or "0") * 100)
            except decimal.InvalidOperation:
                continue
            if cents == 0:
                continue
            raw_date = (row.get("contribution_receipt_date") or "")[:10]
            date_valid = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date))
            year = int(raw_date[:4]) if date_valid else int(row.get("report_year") or 0)
            donor = row.get("contributor_name") or row.get("contributor") or "(blank contributor name)"
            employer = row.get("contributor_employer") or ""
            direct = match_entities(donor, entities)
            employed = match_entities(employer, entities)
            associations = []
            for entity_id in direct:
                organization = bool(re.search(r"\b(PAC|COPE|POLITICAL|GOVT|GOVERNMENT|COMMITTEE)\b", norm(donor)))
                associations.append({
                    "entity": entity_id,
                    "basis": "PAC / organization name" if organization else "Organization name",
                    "field": "contributor", "value": donor,
                })
            for entity_id in employed:
                if entity_id not in direct:
                    associations.append({
                        "entity": entity_id, "basis": "Reported employer",
                        "field": "employer", "value": employer,
                    })
            lead_text = norm(donor + " " + employer)
            lead = not associations and bool(re.search(
                r"\b(DATA CENTER|DATA CENTERS|IBEW|CARPENTERS|STEAMFITTERS|PLUMBERS|OPERATING ENGINEERS|LABORERS|SHEET METAL|BUILDING TRADES|FIRSTENERGY|EXELON|PECO|COREWEAVE|POWERHOUSE|DIGITAL REALTY|MCGUIREWOODS|K L GATES|GREENBERG TRAURIG|EQT)\b",
                lead_text,
            ))
            image = row.get("image_number") or row.get("file_number") or row.get("sub_id")
            filing_url = row.get("pdf_url") or (f"https://docquery.fec.gov/cgi-bin/fecimg/?{image}" if image else "https://www.fec.gov/data/receipts/")
            if filing_url.startswith("http://"):
                filing_url = "https://" + filing_url[7:]
            rows.append({
                "source": "FEC", "report": image, "filer": row.get("committee_id") or path.stem,
                "year": year, "submitted": (row.get("load_date") or "")[:10],
                "cycle": row.get("two_year_transaction_period") or "", "section": f"FEC-{line}",
                "donor": donor, "city": row.get("contributor_city") or "",
                "state": row.get("contributor_state") or "",
                "occupation": row.get("contributor_occupation") or "",
                "employer": employer, "date": raw_date, "date_valid": date_valid,
                "cents": cents, "description": row.get("line_number_label") or row.get("receipt_type_desc") or "FEC Schedule A receipt",
                "archive": "FEC processed Schedule A", "member": row.get("committee_id") or path.stem,
                "record": row.get("sub_id") or source_row, "slot": 1,
                "filing_url": filing_url, "file_number": row.get("file_number") or "",
                "entity_type": row.get("entity_type_desc") or row.get("entity_type") or "",
                "memo_text": row.get("memo_text") or "", "connections": associations, "lead": lead,
            })
    return committee_name, rows


def write_audit_csvs(meta, entities):
    entity_by_id = {entity["id"]: entity for entity in entities}
    donor_rows = []
    connection_rows = []
    for candidate in meta["candidates"]:
        payload = load_candidate(candidate["id"])
        for donor in payload["donors"]:
            sources = sorted({row.get("source", "PA DOS") for row in donor["transactions"]})
            donor_rows.append({
                "candidate_id": candidate["id"], "candidate": candidate["name"],
                "office": candidate["office"], "district": candidate["district_number"],
                "donor": donor["name"], "city": donor["city"], "state": donor["state"],
                "amount": sum(row["cents"] for row in donor["transactions"]) / 100,
                "transactions": len(donor["transactions"]),
                "documented_transactions": sum(bool(row["connections"]) for row in donor["transactions"]),
                "sources": "; ".join(sources),
            })
            for row in donor["transactions"]:
                for association in row["connections"]:
                    entity = entity_by_id[association["entity"]]
                    connection_rows.append({
                        "candidate_id": candidate["id"], "candidate": candidate["name"],
                        "donor": row["donor"], "date": row["date"], "amount": row["cents"] / 100,
                        "entity": entity["name"], "basis": association["basis"],
                        "reported_employer": row["employer"], "connection": entity["claim"],
                        "source_url": entity["url"], "evidence_date": entity["evidence_date"],
                        "finance_source": row.get("source", "PA DOS"),
                        "filing_url": row.get("filing_url", ""),
                        "report_id": row["report"], "source_record": row["record"],
                    })
    for filename, rows in (("all_donors.csv", donor_rows), ("documented_connections.csv", connection_rows)):
        with (ROOT / "research" / filename).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", type=pathlib.Path, default=WORK_DEFAULT)
    parser.add_argument("--max-date", default="09/15/2026")
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    meta = json.loads((DATA / "index.json").read_text())
    entities = json.loads((ROOT / "research/entities.json").read_text())
    for entity in entities:
        entity["_aliases"] = [norm(alias) for alias in entity["aliases"]]

    bulk = ensure_linkage_files(args.work_dir)
    linkages = read_linkages(bulk)
    api_key = get_download_key()
    all_committees = sorted({committee_id for rows in linkages.values() for committee_id in rows})
    for index, committee_id in enumerate(all_committees, 1):
        print(f"FEC export {index}/{len(all_committees)}: {committee_id}", flush=True)
        export_committee(committee_id, args.work_dir, api_key, args.max_date)

    candidate_by_id = {candidate["id"]: candidate for candidate in meta["candidates"]}
    mapping_output = []
    federal_transaction_total = 0
    for candidate_key, fec_candidate_id in FEC_IDS.items():
        candidate = candidate_by_id[candidate_key]
        existing = load_candidate(candidate_key)
        state_transactions = [
            row for donor in existing["donors"] for row in donor["transactions"]
            if row.get("source", "PA DOS") != "FEC"
        ]
        state_filers = [filer for filer in candidate.get("filers", []) if filer.get("type") != "FEC"]
        state_reports = [report for report in existing.get("reports", []) if report.get("source") != "FEC"]
        transactions = list(state_transactions)
        fec_transactions = []
        filers = list(state_filers)
        committee_names = {}
        for committee_id, linkage in sorted(linkages[candidate_key].items()):
            committee_name, rows = parse_committee(args.work_dir / "raw" / f"{committee_id}.csv", entities)
            committee_names[committee_id] = committee_name
            transactions.extend(rows)
            fec_transactions.extend(rows)
            filers.append({
                "filer_id": committee_id, "name": committee_name,
                "basis": f"FEC candidate-committee linkage ({linkage['designation']})",
                "type": "FEC", "report_id": fec_candidate_id,
                "source_url": f"https://www.fec.gov/data/committee/{committee_id}/?cycle=2026",
            })
        groups = {}
        for transaction in transactions:
            key = "|".join(norm(transaction[field]) for field in ("donor", "city", "state"))
            donor_id = hashlib.sha256(key.encode()).hexdigest()[:16]
            if donor_id not in groups:
                groups[donor_id] = {
                    "id": donor_id, "name": html.unescape(transaction["donor"]),
                    "city": transaction["city"], "state": transaction["state"], "transactions": [],
                }
            groups[donor_id]["transactions"].append(transaction)
        report_keys = sorted({(row["filer"], row["year"]) for row in fec_transactions})
        fec_reports = [{
            "CampaignfinanceID": f"FEC-{committee_id}-{year}", "FILERID": committee_id,
            "EYEAR": year, "CYCLE": str(year), "AMMEND": "Processed",
            "SubmittedDate": max((row["submitted"] for row in fec_transactions if row["filer"] == committee_id and row["year"] == year), default=""),
            "FILERNAME": committee_names[committee_id], "MONETARY": "", "INKIND": "", "source": "FEC",
        } for committee_id, year in report_keys]
        reports = state_reports + fec_reports
        fec_report_count = len({row["file_number"] or row["report"] for row in fec_transactions})
        candidate.update({
            "filers": filers, "transaction_count": len(transactions), "donor_count": len(groups),
            "report_count": len(state_reports) + fec_report_count,
            "has_committee": bool(filers), "federal_gap": False,
            "data_source": "PA DOS + FEC" if state_transactions else "FEC",
            "fec_candidate_id": fec_candidate_id,
            "coverage": "Official FEC processed Schedule A contribution records for linked authorized committees" + (" plus matched historical Pennsylvania filings" if state_transactions else ""),
            "last_submitted": max((row["submitted"] for row in transactions), default=None),
            "dc_donor_count": sum(any(row["connections"] for row in group["transactions"]) for group in groups.values()),
        })
        payload = {"candidate": candidate, "donors": sorted(groups.values(), key=lambda group: group["name"].upper()), "reports": reports}
        (DATA / f"{candidate_key}.json").write_text(json.dumps(payload, separators=(",", ":")))
        mapping_output.append({
            "candidate_id": candidate_key, "candidate": candidate["name"], "district": candidate["district_number"],
            "fec_candidate_id": fec_candidate_id, "committees": filers,
            "transactions": len(transactions), "federal_transactions": len(fec_transactions), "donors": len(groups),
        })
        federal_transaction_total += len(fec_transactions)

    for entity in entities:
        entity.pop("_aliases", None)
    meta["candidates"] = [candidate_by_id[candidate["id"]] for candidate in meta["candidates"]]
    meta["total_transactions"] = sum(candidate["transaction_count"] for candidate in meta["candidates"])
    meta["federal_transactions"] = federal_transaction_total
    meta["source"] = "Pennsylvania Department of State archives supplied by the user and official FEC processed Schedule A exports"
    meta["fec_source_url"] = "https://www.fec.gov/data/browse-data/?tab=bulk-data"
    meta["coverage_gaps"] = [
        {key: candidate[key] for key in ("id", "name", "office", "district", "coverage")}
        for candidate in meta["candidates"] if not candidate["has_committee"]
    ]
    meta["quality"]["fec"] = {
        "candidate_count": len(FEC_IDS), "committee_count": len(all_committees),
        "transaction_count": federal_transaction_total,
        "included_lines": sorted(CONTRIBUTION_LINES), "memoed_subtotals_excluded": True,
        "min_date": "2016-01-01", "max_date": args.max_date,
    }
    (DATA / "index.json").write_text(json.dumps(meta, separators=(",", ":")))
    (ROOT / "research/fec_candidate_mappings.json").write_text(json.dumps(mapping_output, indent=2))
    (ROOT / "research/coverage_gaps.json").write_text(json.dumps(meta["coverage_gaps"], indent=2))
    write_audit_csvs(meta, entities)
    print(json.dumps({
        "candidates": len(FEC_IDS), "committees": len(all_committees),
        "federal_transactions": federal_transaction_total,
        "total_transactions": meta["total_transactions"],
    }, indent=2))


if __name__ == "__main__":
    main()
