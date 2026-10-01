"""Save Wikidata country-linked music genre leads for atlas research gaps.

The query uses explicit P31=music genre and P495=country of origin statements.
Wikidata is community edited; these statements are discovery leads, not reviewed
evidence of origin, importance, dates, or precise regions. Nothing is published.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.import_unesco_candidates import COUNTRY_CODES, INVENTORY


ROOT = Path(__file__).resolve().parents[1]
UNESCO = ROOT / "research" / "unesco_candidates.json"
OUTPUT = ROOT / "research" / "wikidata_candidates.json"
ENDPOINT = "https://query.wikidata.org/sparql"
QID = re.compile(r"^https?://www\.wikidata\.org/entity/(Q[1-9][0-9]*)$")


def target_countries(inventory: dict, unesco: dict, all_countries: bool = False) -> dict[str, str]:
    mapped = {row["code"] for row in inventory["countries"]}
    if not all_countries:
        mapped -= {row["country"] for row in unesco["candidates"]}
    iso_by_map = {map_code: iso for iso, map_code in COUNTRY_CODES.items()}
    return {code: iso_by_map[code] for code in sorted(mapped) if code in iso_by_map}


def query_service(iso_codes: list[str]) -> dict:
    if not iso_codes:
        return {"results": {"bindings": []}}
    values = " ".join(f'"{code}"' for code in iso_codes)
    query = (
        "SELECT DISTINCT ?item ?country ?iso2 ?itemLabel ?itemDescription WHERE {\n"
        f"  VALUES ?iso2 {{ {values} }}\n"
        "  ?country wdt:P297 ?iso2.\n"
        "  ?item wdt:P31 wd:Q188451; wdt:P495 ?country.\n"
        "  SERVICE wikibase:label { bd:serviceParam wikibase:language \"en\". }\n"
        "}"
    )
    url = ENDPOINT + "?" + urlencode({"query": query, "format": "json"})
    request = Request(url, headers={"User-Agent": "MusicAtlasResearch/1.0 (public research leads)"})
    with urlopen(request, timeout=90) as response:
        return json.load(response)


def parse_results(data: dict, targets: dict[str, str]) -> list[dict]:
    map_by_iso = {iso: code for code, iso in targets.items()}
    rows = []
    seen = set()
    for binding in data["results"]["bindings"]:
        iso = binding["iso2"]["value"]
        item_url = binding["item"]["value"]
        country_url = binding["country"]["value"]
        item = QID.fullmatch(item_url)
        country = QID.fullmatch(country_url)
        code = map_by_iso.get(iso)
        if not item or not country or not code:
            continue
        key = (code, item.group(1))
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "id": f"wikidata-{item.group(1).lower()}-{code.lower()}",
            "country": code,
            "source_country_code": iso,
            "country_wikidata_id": country.group(1),
            "wikidata_id": item.group(1),
            "title": binding.get("itemLabel", {}).get("value", item.group(1)),
            "description": binding.get("itemDescription", {}).get("value"),
            "source_url": item_url,
            "statement": "P31=music genre (Q188451); P495=country of origin",
            "review_status": "unreviewed",
        })
    return sorted(rows, key=lambda row: (row["country"], row["title"].casefold(), row["id"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Query all mapped ISO-coded countries, not only UNESCO gaps")
    parser.add_argument("--input", type=Path, help="Use a saved WDQS JSON response instead of querying the service")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    inventory = json.loads(INVENTORY.read_text())
    unesco = json.loads(UNESCO.read_text())
    targets = target_countries(inventory, unesco, args.all)
    response = json.loads(args.input.read_text()) if args.input else query_service(list(targets.values()))
    candidates = parse_results(response, targets)
    result = {
        "version": 1,
        "source": "Wikidata Query Service: explicit music genre and country of origin statements",
        "source_url": "https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service",
        "query_mode": "all_mapped_iso_countries" if args.all else "unesco_gap_countries_only",
        "queried_country_codes": sorted(targets),
        "candidate_count": len(candidates),
        "matched_country_count": len({row["country"] for row in candidates}),
        "limitations": (
            "Community-edited P31/P495 statements are discovery leads, not independent evidence "
            "for origin, importance, dates, or precise region. This query omits music traditions "
            "that are not explicitly typed as music genre or lack country-of-origin statements. "
            "No result does not mean a country lacks genres. Verify with local and specialist sources."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidates": candidates,
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"{len(candidates)} leads for {result['matched_country_count']} of {len(targets)} queried countries; no catalogue changes")


if __name__ == "__main__":
    main()
