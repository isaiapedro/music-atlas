"""Build Atlas city points and population records from UN WUP 2025.

Download the official WUP DEGURBA city CSV gzip separately and pass its path.
The generated ledger and point layer contain only WUP cities in mapped Atlas
countries; older Natural Earth, Wikidata, and census city fallbacks are
discarded.
"""
import argparse
import csv
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WUP_SOURCE = "https://population.un.org/wup/downloads"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="WUP2025 DEGURBA Cities CSV gzip")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--output", type=Path, default=ROOT / "web/data/place_population_overrides.json")
    args = parser.parse_args()

    countries = json.loads((ROOT / "web/data/countries.geojson").read_text())["features"]
    mapped_codes = {feature["properties"]["code"] for feature in countries}
    overrides = {}
    rows = []
    with gzip.open(args.input, "rt", encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            if row.get("Year") == str(args.year) and row["ISO3_Code"] in mapped_codes:
                rows.append(row)

    features = []
    for row in rows:
        code, name, city_code = row["ISO3_Code"], row["City_Name"], int(row["City_Code"])
        key = f"{code}|{name}|{city_code}"
        population = round(float(row["Pop"]) * 1000)
        overrides[key] = {
            "population": population,
            "year": args.year,
            "scope": "DEGURBA city",
            "source": "UN World Urbanization Prospects 2025",
            "source_url": WUP_SOURCE,
            "un_city_code": city_code,
            "plausibility": row.get("Pop_plausibility") or None,
        }
        features.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "feature": "Admin-0 capital" if row.get("Capital") == "1" else "Populated place",
                "population": population,
                "rank": None,
                "code": code,
                "population_key": key,
                "un_city_code": city_code,
            },
            "geometry": {"type": "Point", "coordinates": [
                round(float(row["PWCent_Longitude"]), 6),
                round(float(row["PWCent_Latitude"]), 6),
            ]},
        })

    args.output.write_text(json.dumps(dict(sorted(overrides.items())), ensure_ascii=False, indent=2) + "\n")
    places_output = ROOT / "web/data/populated_places.geojson"
    places_output.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                                        ensure_ascii=False, separators=(",", ":")))
    print(f"wrote {len(features)} WUP {args.year} cities and {len(overrides)} population records")


if __name__ == "__main__":
    main()
