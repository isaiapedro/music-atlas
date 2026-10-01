"""Update saved country population facts from UN WUP 2025 Level 1 data."""
import argparse
import csv
import gzip
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "research/wiki_articles.json", ROOT / "web/data/articles.json"]
CODE_ALIASES = {"PSX": "PSE", "SDS": "SSD", "SAH": "ESH"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--year", type=int, default=2025)
    args = parser.parse_args()
    totals = defaultdict(float)
    with gzip.open(args.input, "rt", encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            if (row.get("Year") == str(args.year)
                    and row.get("LocTypeName") == "Country/Area"
                    and row.get("Category") == "Total"):
                try:
                    totals[row["ISO3_Code"]] += float(row["Pop"]) * 1000
                except (KeyError, ValueError):
                    pass
    updated = 0
    for path in FILES:
        snapshot = json.loads(path.read_text())
        file_updates = 0
        for code, article in snapshot["countries"].items():
            if not article:
                continue
            population = totals.get(CODE_ALIASES.get(code, code))
            article["population"] = ({"value": round(population), "year": args.year,
                                      "source": "UN World Urbanization Prospects 2025"}
                                     if population else None)
            file_updates += bool(population)
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
        updated = file_updates
    print(f"updated {updated} country populations from WUP {args.year}")


if __name__ == "__main__":
    main()
