"""Discover possible music research leads from UNESCO's public ICH dataset.

This importer never edits the reviewed genre catalogue or the country inventory.
UNESCO inscriptions are neither a complete music inventory nor evidence of a
genre's origin, lifespan, regional footprint, or relative importance.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATASET = "https://data.unesco.org/api/explore/v2.1/catalog/datasets/ich001/records"
OUTPUT = ROOT / "research" / "unesco_candidates.json"
INVENTORY = ROOT / "research" / "country_inventory.json"

# ISO 3166 alpha-2 to the actual Natural Earth map codes. Special map areas
# without a corresponding UNESCO country code are intentionally not guessed.
MAP_CODE_PAIRS = """
AF:AFG AO:AGO AE:ARE AM:ARM AZ:AZE BI:BDI BJ:BEN BF:BFA BD:BGD
BH:BHR BN:BRN BT:BTN BW:BWA CF:CAF CN:CHN CI:CIV CM:CMR
CD:COD CG:COG KM:COM CV:CPV CY:CYP DJ:DJI DZ:DZA EG:EGY
ER:ERI ET:ETH GA:GAB GE:GEO GH:GHA GN:GIN GM:GMB GW:GNB
GQ:GNQ HK:HKG ID:IDN IN:IND IR:IRN IQ:IRQ IL:ISR JO:JOR
JP:JPN KZ:KAZ KE:KEN KG:KGZ KH:KHM KR:KOR KW:KWT LA:LAO
LB:LBN LR:LBR LY:LBY LK:LKA LS:LSO MO:MAC MA:MAR MG:MDG
ML:MLI MM:MMR MN:MNG MZ:MOZ MR:MRT MW:MWI MY:MYS NA:NAM
NE:NER NG:NGA NP:NPL OM:OMN PK:PAK PH:PHL KP:PRK PS:PSX
QA:QAT RW:RWA SA:SAU SD:SDN SS:SDS SN:SEN SG:SGP SL:SLE
SO:SOM ST:STP SZ:SWZ SY:SYR TD:TCD TG:TGO TH:THA TJ:TJK
TM:TKM TL:TLS TN:TUN TR:TUR TW:TWN TZ:TZA UG:UGA UZ:UZB
VN:VNM YE:YEM ZA:ZAF ZM:ZMB ZW:ZWE
"""
COUNTRY_CODES = dict(pair.split(":") for pair in MAP_CODE_PAIRS.split())
MUSIC_CONCEPT = re.compile(
    r"\b(?:music|musical|song|songs|singing|chant|chants|chanting|vocal|"
    r"polyphony|polyphonic|drum|drums|drumming|instrument|instruments|"
    r"instrumental|percussion|opera)\b",
    re.IGNORECASE,
)


def fetch_records() -> tuple[list[dict], int]:
    records: list[dict] = []
    total = None
    while total is None or len(records) < total:
        url = DATASET + "?" + urlencode({"limit": 100, "offset": len(records)})
        request = Request(url, headers={"User-Agent": "MusicAtlasResearch/1.0 (public UNESCO data)"})
        with urlopen(request, timeout=30) as response:
            page = json.load(response)
        total = page["total_count"]
        batch = page["results"]
        if not batch:
            raise RuntimeError(f"UNESCO returned an empty page before {total} records")
        records.extend(batch)
    if len(records) != total:
        raise RuntimeError(f"UNESCO returned {len(records)} records; expected {total}")
    return records, total


def import_candidates(records: list[dict], inventory: dict) -> dict:
    mapped = {row["code"] for row in inventory["countries"]}
    invalid_map_codes = sorted(set(COUNTRY_CODES.values()) - mapped)
    if invalid_map_codes:
        raise ValueError(f"Country code mapping is not in the atlas inventory: {invalid_map_codes}")
    candidates = []
    skipped_country_codes: set[str] = set()
    seen: set[tuple[str, str]] = set()
    for record in records:
        primary = [name for name in (record.get("concepts_primary_names") or []) if MUSIC_CONCEPT.search(name)]
        secondary = [name for name in (record.get("concepts_secondary_names") or []) if MUSIC_CONCEPT.search(name)]
        if not primary and not secondary:
            continue
        source_url = record.get("http_url_en")
        reference = record.get("ich_public_ref")
        if not source_url or not reference or not record.get("title_en"):
            continue
        for source_code in record.get("countries") or []:
            code = COUNTRY_CODES.get(source_code)
            if code not in mapped:
                skipped_country_codes.add(source_code)
                continue
            key = (str(reference), code)
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                "id": f"unesco-{reference}-{code.lower()}",
                "country": code,
                "source_country_code": source_code,
                "title": record["title_en"],
                "source_url": source_url,
                "inscription_year": record.get("inscription_year"),
                "music_match": "primary_concept" if primary else "secondary_concept",
                "matched_concepts": sorted(set(primary + secondary)),
                "review_status": "unreviewed",
            })
    candidates.sort(key=lambda item: (item["country"], item["title"].casefold(), item["id"]))
    return {
        "version": 1,
        "source": "UNESCO DataHub: Intangible Heritage List (ich001)",
        "source_dataset_url": "https://data.unesco.org/explore/dataset/ich001/",
        "source_api_url": DATASET,
        "source_record_count": len(records),
        "candidate_count": len(candidates),
        "mapped_country_count": len({item["country"] for item in candidates}),
        "mapped_country_inventory_count": len(mapped),
        "unmatched_source_country_codes": sorted(skipped_country_codes),
        "limitations": (
            "Automated concept matches are research leads only. UNESCO lists reflect nominations "
            "and inscription decisions, not a complete or ranked music catalogue. Entries can "
            "describe dances, instruments, festivals, or mixed practices rather than genres. "
            "Inscription years are not musical origin dates. Country associations do not establish "
            "exclusive origin or a precise map region. Review each element before publication."
        ),
        "candidates": candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Offline UNESCO JSON with results; otherwise download the dataset")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.input:
        data = json.loads(args.input.read_text())
        records = data["results"] if isinstance(data, dict) else data
        expected = data.get("total_count") if isinstance(data, dict) else None
        if expected is not None and len(records) != expected:
            raise ValueError(f"Input contains {len(records)} records; expected {expected}")
    else:
        records, _ = fetch_records()
    inventory = json.loads(INVENTORY.read_text())
    result = import_candidates(records, inventory)
    result["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"{result['candidate_count']} leads for {result['mapped_country_count']} mapped countries; no catalogue changes")


if __name__ == "__main__":
    main()
