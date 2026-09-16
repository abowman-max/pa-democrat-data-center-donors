#!/usr/bin/env python3
"""Add reviewed HB 952 yea-voter donor aliases to the connection registry.

The roll calls use surnames and initials.  This script limits matching to full
personal names and clearly identified campaign-committee names.  Generic
surnames and ambiguous committee names are intentionally excluded.
"""
import csv
import json
import pathlib
import re
import subprocess
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence"
REGISTRY = ROOT / "research" / "entities.json"
AUDIT = ROOT / "research" / "hb952_rollcall_aliases.json"


HOUSE_GROUPS = {
    "FRANKEL": ("Dan Frankel", ["DAN FRANKEL 23 DISTRICT COMMITTEE", "DAN FRANKEL FOR 23RD DISTRICT COMMITTEE", "DAN FRANKEL FOR THE 23RD DISTRICT COMMITTEE", "DAN FRANKEL 23RD DISTRICT COMMITTEE", "DAN FRANKEL FOR 23 DISTRICT COMMITTEE", "DAN FRANKEL FOR THE 23RD DIST COMMITTEE", "FRIENDS OF DAN FRANKEL-23RD DIST COMM"]),
    "FREEMAN": ("Robert Freeman", ["COMMITTEE TO ELECT ROBERT FREEMAN"]),
    "LONGIETTI": ("Mark Longietti", ["FRIENDS OF LONGIETTI"]),
    "BIZZARRO": ("Ryan Bizzarro", ["COMMITTEE TO ELECT RYAN BIZZARRO"]),
    "GALLOWAY": ("John Galloway", ["GALLOWAY JOHN FOR STATE REP", "JOHN GALLOWAY FOR STATE REP", "JOHN GALLOWAY FOR STATE REPRESENTATIVE"]),
    "MADDEN": ("Maureen Madden", ["FRIENDS OF MAUREEN MADDEN", "MAUREEN FRIENDS OF MADDEN"]),
    "ROZZI": ("Mark Rozzi", ["FRIENDS OF MARK ROZZI", "ROZZI MARK FRIENDS OF"]),
    "MALAGARI": ("Steve Malagari", ["FRIENDS OF STEVE MALAGARI", "MALAGARI FRIENDS OF", "STEVE MALAGARI FRIENDS OF"]),
    "SAMUELSON": ("Steve Samuelson", ["FRIENDS OF STEVE SAMUELSON"]),
    "BRADFORD": ("Matt Bradford", ["BRADFORD MATT FRIENDS OF", "FRIENDS OF MATT BRADFORD"]),
    "MARKOSEK": ("Joseph Markosek", ["MARKOSEK FOR STATE LEGISLATIVE", "MARKOSEK FOR STATE LEGISLATOR", "MARKOSEK FOR STATE LEGISLATURE", "MARKOSEK FOR STATE LEGISLATURE COMMITTEE", "MARKOSEK JOSEPH FOR STATE LEG COM"]),
    "SANCHEZ": ("Ben Sanchez", ["FRIENDS OF BEN SANCHEZ", "SANCHEZ BEN FRIENDS OF"]),
    "BRIGGS": ("Tim Briggs", ["FRIENDS OF TIM BRIGGS", "TIM BRIGGS FOR STATE REP", "TIM BRIGGS FOR STATE REPRESENTATIVE", "TIM BRIGGS FOR STATE REPRESENTITIVE"]),
    "MARSHALL": ("Jim Marshall", ["FRIENDS OF JIM MARSHALL"]),
    "SAPPEY": ("Christina Sappey", ["FRIENDS OF CHRISTINA SAPPEY"]),
    "BROWN, A.": ("Amen Brown", ["CITIZENS FOR AMEN BROWN"]),
    "MATZIE": ("Robert Matzie", ["MATZIE ROBERT PEOPLE FOR", "PEOPLE FOR MATZIE"]),
    "GUZMAN": ("Manny Guzman", ["FRIENDS OF MANNY GUZMAN"]),
    "MCCLINTON": ("Joanna McClinton", ["FRIENDS OF JOANA MCCLINTON", "FRIENDS OF JOANNA MCCLINTON", "FRIENDS OF JOHANNA MCCLINTON", "FRIENDS OF JOANNA MCCLINTON PAC", "MCCLINTON JOANNA FRIENDS OF"]),
    "BULLOCK": ("Donna Bullock", ["BULLOCK DONNA FRIENDS OF", "FRIENDS OF DONNA BULLOCK", "FRIENDS OF DONNA BULLOCK AND OTIS BULLOCK", "FRIENDS OF DONNA BULLOCK AMBRIA B JOHNSON"]),
    "MCNEILL": ("Jeanne McNeill", ["MCNEILL FOR PA"]),
    "SCHLOSSBERG": ("Mike Schlossberg", ["FRIENDS OF MICHAEL SCHLOSSBERG", "FRIENDS OF MIKE SCHLOSSBERG", "SCHLOSSBERG MIKE FRIENDS OF"]),
    "BURGOS": ("Danilo Burgos", ["FRIENDS OF DANILO BURGOS"]),
    "HARKINS": ("Pat Harkins", ["FRIENDS OF PAT HARKINS"]),
    "CARROLL": ("Mike Carroll", ["CARROLL MIKE FRIENDS OF FOR ST REP", "FRIENDS OF MICHAEL CARROLL", "FRIENDS OF MIKE CARROLL", "FRIENDS OF MIKE CARROLL FOR STATE REPRESENTATIVE"]),
    "HARRIS": ("Jordan Harris", ["CITIZENS FOR JORDAN HARRIS", "HARRIS JORDAN CITIZENS FOR", "JORDAN HARRIS CITIZENS FOR"]),
    "SCHWEYER": ("Peter Schweyer", ["FRIENDS OF PETER SCHWEYER", "SCHWEYER PETER FRIENDS OF"]),
    "MERSKI": ("Bob Merski", ["FRIENDS OF BOB MERSKI"]),
    "SHUSTERMAN": ("Melissa Shusterman", ["FRIENDS OF MELISSA SHUSTERMAN"]),
    "CEPHAS": ("Morgan Cephas", ["CEPHAS MORGAN FRIENDS FOR", "FRIENDS FOR MORGAN CEPHAS", "FRIENDS OF MORGAN CEPHAS"]),
    "CIRESI": ("Joe Ciresi", ["FRIENDS OF JOE CIRESI"]),
    "CONKLIN": ("Scott Conklin", ["FRIENDS OF SCOTT CONKLIN"]),
    "HERRIN": ("Dianne Herrin", ["FRIENDS OF DIANNE HERRIN"]),
    "SNYDER": ("Pam Snyder", ["COMMITTE TO ELECT PAM SNYDER", "COMMITTEE TO ELECT PAM SNYDER"]),
    "MILLER, D.": ("Dan Miller", ["FRIENDS OF DAN MILLER", "MILLER DAN FRIENDS OF"]),
    "HOHENSTEIN": ("Joe Hohenstein", ["ELECT JOE HOHENSTEIN", "FRIENDS OF JOE HOHENSTEIN", "HOHENSTEIN JOE ELECT"]),
    "MULLERY": ("Gerald Mullery", ["CITIZENS FOR MULLERY", "CITIZENS FOR GERALD MULLERY"]),
    "DAVIDSON": ("Margo Davidson", ["DAVIDSON MARGO FRIENDS OF", "FRIENDS OF MARGO DAVIDSON"]),
    "MULLINS": ("Kyle Mullins", ["FRIENDS OF KYLE MULLINS", "MULLINS KYLE FRIENDS OF"]),
    "DAVIS, A.": ("Austin Davis", ["DAVIS AUSTIN FRIENDS OF", "FRIENDS OF AUSTIN DAVIS"]),
    "STURLA": ("Mike Sturla", ["STURLA MIKE FOR STATE REP", "STURLA FOR STATE REPRESENTATIVE"]),
    "DAVIS, T.": ("Tina Davis", ["DAVIS TINA FRIENDS OF", "FRIENDS OF TINA DAVIS", "FRIENDS OF TINA DAVIS DAVIS"]),
    "DAWKINS": ("Jason Dawkins", ["FRIENDS OF JASON DAWKINS"]),
    "NELSON, N.": ("Napoleon Nelson", ["FRIENDS OF NAPOLEON NELSON"]),
    "PASHINSKI": ("Eddie Day Pashinski", ["COMMITTEE TO ELECT EDDIE DAY PASHINKSI", "COMMITTEE TO ELECT EDDIE DAY PASHINSKI"]),
    "DEASY": ("Dan Deasy", ["COMMITTEE TO ELECT DAN DEASY", "DEASY DAN COM TO ELECT"]),
    "O'MARA": ("Jennifer O'Mara", ["FRIENDS OF JENN OMARA", "FRIENDS OF JENNFER OMARA", "FRIENDS OF JENNIFER OMARA"]),
    "DELLOSO": ("Dave Delloso", ["FRIENDS OF DAVE DELLOSO", "FRIENDS OF DAVE DELLOSO FRIENDS OF DAVE DELLOSO"]),
    "WARREN": ("Perry Warren", ["PERRY WARREN FOR STATE REPRESENTATIVE", "PERRY WARREN FOR STATE REP", "WARREN PERRY FOR STATE REPRESENTATIVE"]),
    "DELUCA": ("Tony DeLuca", ["DELUCA LEGISLATOR COMMITTEE"]),
    "KIM": ("Patty Kim", ["FRIENDS OF PATTY KIM", "KIM PATTY FRIENDS OF"]),
    "WEBSTER": ("Joe Webster", ["FRIENDS OF JOE WEBSTER"]),
    "KINSEY": ("Stephen Kinsey", ["FRIENDS OF STEPHEN KINSEY", "FRIENDS OF STEVEN KINSEY"]),
    "WHEATLEY": ("Jake Wheatley", ["CITIZENS FOR JAKE WHEATLEY", "WHEATLEY CITIZENS FOR JAKE"]),
    "DRISCOLL": ("Mike Driscoll", ["FRIENDS OF MIKE DRISCOLL"]),
    "WILLIAMS, D.": ("Dan Williams", ["CITIZENS FOR DAN WILLIAMS"]),
    "KOSIEROWSKI": ("Bridget Kosierowski", ["FRIENDS OF BRIDGET KOSIEROWSKI", "FRIENDS OF BRIDGET MALLAY KOSIEROWSKI", "FRIENDS OF BRIDGET MALLOY KOSIEROWSKI", "FRIENDS OF BRIDGET MOLLAY KOSIEROWSKI", "FRIENDS OF BRIDGET MOLLOY KOSIEROWSKI", "FRIENDS OF BRIDGEY MALLOY KOSIEROWSKI", "FRIENDS OF BRIDGEY MALLOY-KOSIEROWSKI", "KOSIEROWSKI BRIDGET FRIENDS OF"]),
    "YOUNG": ("Regina Young", ["FRIENDS OF REGINA YOUNG", "FRIENDS OF REGINA YOUNG 185"]),
    "KRUEGER": ("Leanne Krueger", ["COMMITTEE TO ELECT LEANNE KRUEGER-BRANEKY", "COMMITTEE TO ELECT LEANNE KRUEGER BRANEKY", "LEANNE KRUEGER FOR PA"]),
    "ZABEL": ("Mike Zabel", ["FRIENDS OF MIKE ZABEL"]),
    "FEE": ("Mindy Fee", ["FEE MINDY FRIENDS OF"]),
    "KULIK": ("Anita Astorino Kulik", ["FRIENDS OF ANITA ASTORINO KULIK", "FRIENDS OF ANITO ASTORINO KULIK", "FRIENDS OF ANITA KULIK", "KULIK ASTORINO ANITA FRIENDS OF"]),
    "FITZGERALD": ("Isabella Fitzgerald", ["FRIENDS OF ISABELLA FITZGERALD"]),
}


SENATE_GROUPS = {
    "STREET": ("Sharif Street", ["FRIENDS OF SHARIF STREET", "SHARIF STREET FOR PA", "STREET SHARIF FRIENDS OF"]),
    "FLYNN": ("Marty Flynn", ["FRIENDS OF MARTY FLYNN"]),
    "TARTAGLIONE": ("Christine Tartaglione", ["FRIENDS TO ELECT CHRISTINE M TARTAGLIONE", "FRIENDS OF CHRISTINE TARTAGLIONE", "FRIENDS TO ELECT CHRISTINE TARTAGLIONE"]),
    "FONTANA": ("Wayne Fontana", ["COMMITTEE TO ELECT WAYNE FONTANA", "THE COMMITTE TO ELECT WAYNE FONTANA"]),
    "BOSCOLA": ("Lisa Boscola", ["FRIENDS OF LISA BOSCOLA", "FRIENDS OF LIZA BOSCOLA"]),
    "BREWSTER": ("Jim Brewster", ["COMMITTEE ELECT JIM BREWSTER", "COMMITTEE FOR JIM BREWSTER", "COMMITTEE TO ELECT JIM BREWSTER"]),
    "PITTMAN": ("Joe Pittman", ["FRIENDS OF JOE PITTMAN"]),
    "HAYWOOD": ("Art Haywood", ["CAMPAIGN FOR COMPASSION COMMITTEE ART HAYWOOD"]),
    "HUGHES": ("Vincent Hughes", ["CITIZENS FOR HUGHES", "CITIZENS FOR VINCENT HUGHES", "HUGHES VINCENT CITIZENS FOR", "VINCENT HUGHES CITIZENS FOR"]),
    "SABATINA": ("John Sabatina", ["COMMITTEE TO RE-ELECT JOHN SABATINA JR"]),
    "COLLETT": ("Maria Collett", ["MARIA COLLETT FOR PA SENATE"]),
    "KANE": ("John Kane", ["JOHN KANE FOR SENATE", "JOHN KANE FOR STATE SENATE", "KANE FOR SENATE"]),
    "SANTARSIERO": ("Steve Santarsiero", ["SANTARSIERO FOR STATE SENATE", "SANTARSIERO STEVE FOR STATE SENATE", "STEVE SANTARSIERO FOR STATE REP", "SANTARSIERO FOR SENATE"]),
    "COMITTA": ("Carolyn Comitta", ["COMITTA CAROLYN FRIENDS OF", "FRIENDS OF CAROLYN COMITTA"]),
    "KEARNEY": ("Tim Kearney", ["FRIENDS OF TIM KEARNEY", "KEARNEY TIM FRIENDS OF", "TIM KEARNEY FOR PA STATE SENATE"]),
    "YUDICHAK": ("John Yudichak", ["CITIZENS FOR JOHN YUDICHAK"]),
    "COSTA": ("Jay Costa", ["COSTA JAY JR FOR STATE SENATE", "JAY COSTA FOR SENATE", "JAY COSTA FOR STATE SENATE", "JAY COSTA JR FOR STATE SENATE", "JAY COSTA FOR STATE STREET"]),
    "SCHWANK": ("Judy Schwank", ["FRIENDS FOR JUDY SCHWANK", "FRIENDS OF JUDY SCHWANK", "SCHWANK JUDY FRIENDS FOR"]),
}


def normalize(value):
    return re.sub(r"[^A-Z0-9]+", " ", value.upper().replace("’", "'")).strip()


def rollcall_yeas(pdf_path):
    with tempfile.TemporaryDirectory() as directory:
        output = pathlib.Path(directory) / "rollcall.txt"
        subprocess.run(["pdftotext", "-layout", str(pdf_path), str(output)], check=True)
        text = output.read_text(errors="replace")
    names = []
    for line in text.splitlines():
        for match in re.finditer(r"\uf00c\s+([A-Z][A-Z, .'’-]*?)(?=\s{2,}|$)", line):
            name = match.group(1).strip()
            if name and name != "YEA":
                names.append(name)
    return names


def entity(entity_id, chamber, roll_number, vote_count, groups, url):
    aliases = set()
    lawmakers = []
    for roll_label, (person, committee_aliases) in groups.items():
        lawmakers.append({"roll_call_name": roll_label, "full_name": person})
        aliases.update([person, " ".join(reversed(person.split()))])
        aliases.update(committee_aliases)
    return {
        "id": entity_id,
        "name": f"HB 952 {chamber} Yea voters and campaign committees",
        "category": "Lawmaker vote / campaign committee",
        "aliases": sorted(aliases, key=lambda value: normalize(value)),
        "url": url,
        "title": f"{chamber} Roll Call Vote Summary #{roll_number}",
        "claim": f"The official {chamber.lower()} roll call records these lawmakers voting Yea on June 25, 2021 on HB 952 PN 1934. The enacted bill created a sales and use tax exemption for computer data center equipment. Donor matches use reviewed full personal names and campaign-committee aliases.",
        "evidence_date": "2021-06-25",
        "accessed": "2026-09-15",
        "geography": "Pennsylvania",
        "status": "Documented lawmaker vote connection",
        "contributor_only": True,
        "roll_call_vote_count": vote_count,
        "reviewed_lawmakers": lawmakers,
    }


def main():
    house_pdf = EVIDENCE / "house-roll-call-470.pdf"
    senate_pdf = EVIDENCE / "senate-roll-call-260.pdf"
    house_yeas = rollcall_yeas(house_pdf)
    senate_yeas = rollcall_yeas(senate_pdf)
    assert len(house_yeas) == 170, len(house_yeas)
    assert len(senate_yeas) == 46, len(senate_yeas)
    assert set(HOUSE_GROUPS).issubset(house_yeas)
    assert set(SENATE_GROUPS).issubset(senate_yeas)

    entities = json.loads(REGISTRY.read_text())
    entities = [row for row in entities if row["id"] not in {"hb952_house_yes", "hb952_senate_yes"}]
    house = entity("hb952_house_yes", "House", 470, 170, HOUSE_GROUPS, "https://www.palegis.us/house/roll-calls/summary?sessYr=2021&sessInd=0&rcNum=470")
    senate = entity("hb952_senate_yes", "Senate", 260, 46, SENATE_GROUPS, "https://www.palegis.us/senate/roll-calls/summary?sessYr=2021&sessInd=0&rcNum=260")
    entities.extend([house, senate])
    REGISTRY.write_text(json.dumps(entities, indent=2) + "\n")

    donors = set()
    with (ROOT / "research" / "all_donors.csv").open(newline="") as handle:
        donors.update(row["donor"] for row in csv.DictReader(handle))
    matched = {}
    for row in (house, senate):
        normalized = [(alias, normalize(alias)) for alias in row["aliases"]]
        matched[row["id"]] = sorted({donor for donor in donors if any(f" {alias} " in f" {normalize(donor)} " for _, alias in normalized)})
    audit = {
        "bill": "HB 952 PN 1934",
        "vote_date": "2021-06-25",
        "house": {"roll_call": 470, "yeas": house_yeas, "reviewed_alias_groups": HOUSE_GROUPS, "matched_donor_names": matched["hb952_house_yes"]},
        "senate": {"roll_call": 260, "yeas": senate_yeas, "reviewed_alias_groups": SENATE_GROUPS, "matched_donor_names": matched["hb952_senate_yes"]},
        "method_note": "The official PDFs establish the vote. Full personal names and campaign committee names were manually reviewed against the surname/initial roll calls. Generic surnames and ambiguous names were excluded. The classification describes the donor lawmaker or committee; it does not establish why a contribution was made or the recipient candidate's position.",
        "excluded_ambiguous_examples": ["Friends of Parker", "Friends of Webster", "Friends of Longietti is retained because the surname is distinctive; generic Brown, Smith, Williams, Ward, and Miller names are excluded unless a reviewed first name identifies the voter."],
    }
    AUDIT.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps({"house_yeas": len(house_yeas), "senate_yeas": len(senate_yeas), "house_aliases": len(house["aliases"]), "senate_aliases": len(senate["aliases"]), "house_matched_donor_names": len(matched["hb952_house_yes"]), "senate_matched_donor_names": len(matched["hb952_senate_yes"])}, indent=2))


if __name__ == "__main__":
    main()
