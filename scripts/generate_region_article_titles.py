"""Generate deterministic Wikipedia-title proposals for every mapped region.

The canonical ``research/region_article_titles.json`` file is editorial data.
This script therefore writes a separate proposal file by default and never
claims that a syntactically plausible title has been verified on Wikipedia.

Usage:
  python3 scripts/generate_region_article_titles.py
  python3 scripts/generate_region_article_titles.py --check
  python3 scripts/generate_region_article_titles.py --output /tmp/region-title-proposals.json
"""

import argparse
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "data"
RESEARCH = ROOT / "research"
DEFAULT_OUTPUT = RESEARCH / "region_article_title_proposals.json"
CANONICAL = RESEARCH / "region_article_titles.json"

# Wikipedia commonly uses these shorter country labels in article titles.
COUNTRY_QUALIFIERS = {
    "CHN": "China",
    "CIV": "Ivory Coast",
    "COD": "Democratic Republic of the Congo",
    "COG": "Republic of the Congo",
    "GMB": "the Gambia",
    "KOR": "South Korea",
    "PRK": "North Korea",
    "PSX": "Palestine",
    "TLS": "East Timor",
    "TWN": "Taiwan",
}

# These labels are particularly likely to be disambiguation pages or ordinary
# words even when they occur only once in this particular map snapshot.
GENERIC_NAMES = {
    "Capital", "Central", "Centre", "East", "Eastern", "North", "Northern",
    "North East", "North West", "South", "Southern", "South East",
    "South West", "West", "Western",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def atlas_rows():
    countries = {
        feature["properties"]["code"]: feature["properties"]["name"]
        for feature in read(WEB / "countries.geojson")["features"]
    }
    rows = {
        (feature["properties"]["code"], feature["properties"]["name"])
        for feature in read(WEB / "regions.geojson")["features"]
    }
    return countries, sorted(rows)


def generate():
    countries, rows = atlas_rows()
    reviewed = read(CANONICAL) if CANONICAL.exists() else {}
    name_country_count = Counter(name for _, name in rows)
    proposals = {}

    for code, name in rows:
        key = f"{code}|{name}"
        country = COUNTRY_QUALIFIERS.get(code, countries[code])
        ambiguous = name_country_count[name] > 1 or name in GENERIC_NAMES
        if key in reviewed:
            title = reviewed[key]
            strategy = "reviewed_override"
        elif ambiguous:
            title = f"{name}, {country}"
            strategy = "country_qualified"
        else:
            title = name
            strategy = "exact_region_name"
        proposals[key] = {
            "title": title,
            "strategy": strategy,
            "reviewed": strategy == "reviewed_override",
            "country": country,
        }

    strategy_counts = Counter(row["strategy"] for row in proposals.values())
    return {
        "version": 1,
        "status": "proposals_require_wikipedia_resolution",
        "region_key_count": len(proposals),
        "geometry_feature_count": len(read(WEB / "regions.geojson")["features"]),
        "strategy_counts": dict(sorted(strategy_counts.items())),
        "proposals": proposals,
    }


def serialized(payload):
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true",
                        help="fail if the output is absent or differs from a fresh generation")
    args = parser.parse_args()
    if args.output.resolve() == CANONICAL.resolve():
        parser.error("refusing to overwrite the reviewed canonical mapping")
    payload = generate()
    expected = serialized(payload)
    if args.check:
        assert args.output.exists(), f"missing generated proposals: {args.output}"
        assert args.output.read_text(encoding="utf-8") == expected, (
            f"{args.output} is stale; rerun generate_region_article_titles.py"
        )
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(expected, encoding="utf-8")
    print(f"region keys: {payload['region_key_count']}")
    print(f"geometry features: {payload['geometry_feature_count']}")
    for strategy, count in payload["strategy_counts"].items():
        print(f"{strategy}: {count}")


if __name__ == "__main__":
    main()
