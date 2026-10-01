"""Build reviewed-place population overrides from linked Wikidata entities.

Natural Earth supplies the point inventory and Wikidata IDs, but its modeled
POP_MAX values are deliberately not published as inhabitant counts. Existing
official overrides win over Wikidata. Places without a usable P1082 statement
remain unnamed numerically in the UI rather than falling back to POP_MAX.
"""
import argparse
import json
import struct
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def dbf_rows(path):
    data = path.read_bytes()
    count = struct.unpack("<I", data[4:8])[0]
    header_size = struct.unpack("<H", data[8:10])[0]
    record_size = struct.unpack("<H", data[10:12])[0]
    fields, offset = [], 32
    while data[offset] != 13:
        descriptor = data[offset:offset + 32]
        fields.append((descriptor[:11].split(b"\0")[0].decode(), descriptor[16]))
        offset += 32
    positions, start = [], 1
    for name, length in fields:
        positions.append((name, start, length))
        start += length
    for index in range(count):
        record = data[header_size + index * record_size:header_size + (index + 1) * record_size]
        if record[:1] == b"*":
            continue
        yield {name: record[position:position + length].decode("latin1").strip() for name, position, length in positions}


def statement_year(statement):
    qualifiers = statement.get("qualifiers", {}).get("P585", [])
    try:
        return int(qualifiers[0]["datavalue"]["value"]["time"][1:5])
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def latest_population(entity):
    candidates = []
    for statement in entity.get("claims", {}).get("P1082", []):
        try:
            amount = int(float(statement["mainsnak"]["datavalue"]["value"]["amount"]))
        except (KeyError, TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        year = statement_year(statement)
        if year is None:
            continue
        preferred = statement.get("rank") == "preferred"
        candidates.append((preferred, year, amount, year))
    return max(candidates, default=None)


def fetch_entities(ids):
    query = urllib.parse.urlencode({
        "action": "wbgetentities", "ids": "|".join(ids), "props": "claims|labels",
        "languages": "en", "format": "json", "formatversion": "2",
    })
    request = urllib.request.Request(
        "https://www.wikidata.org/w/api.php?" + query,
        headers={"User-Agent": "MusicAtlas/1.0 (offline population data builder)"},
    )
    for attempt in range(7):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                entities = json.load(response)["entities"]
                return list(entities.values()) if isinstance(entities, dict) else entities
        except HTTPError as error:
            if error.code != 429 or attempt == 6:
                raise
            time.sleep(2 ** (attempt + 1))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--natural-earth-dbf", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "web/data/place_population_overrides.json")
    parser.add_argument("--delay", type=float, default=.2)
    args = parser.parse_args()

    places = json.loads((ROOT / "web/data/populated_places.geojson").read_text())["features"]
    by_position = {(round(feature["geometry"]["coordinates"][0], 3), round(feature["geometry"]["coordinates"][1], 3)): feature for feature in places}
    linked = {}
    for row in dbf_rows(args.natural_earth_dbf):
        try:
            position = (round(float(row["LONGITUDE"]), 3), round(float(row["LATITUDE"]), 3))
        except ValueError:
            continue
        feature = by_position.get(position)
        qid = row.get("WIKIDATAID", "")
        if feature and qid.startswith("Q"):
            linked[qid] = f'{feature["properties"]["code"]}|{feature["properties"]["name"]}'

    overrides = json.loads(args.output.read_text()) if args.output.exists() else {}
    official_keys = {key for key, value in overrides.items() if value.get("source") != "Wikidata"}
    ids = sorted(linked)
    added = 0
    for start in range(0, len(ids), 25):
        batch = ids[start:start + 25]
        for entity in fetch_entities(batch):
            qid = entity.get("id")
            key = linked.get(qid)
            if not key or key in official_keys:
                continue
            population = latest_population(entity)
            if not population:
                overrides.pop(key, None)
                continue
            _, _, amount, year = population
            overrides[key] = {
                "population": amount,
                "year": year,
                "scope": "Wikidata place",
                "source": "Wikidata",
                "source_url": f"https://www.wikidata.org/wiki/{qid}",
                "wikidata_id": qid,
            }
            added += 1
        args.output.write_text(json.dumps(dict(sorted(overrides.items())), ensure_ascii=False, indent=2) + "\n")
        time.sleep(args.delay)

    args.output.write_text(json.dumps(dict(sorted(overrides.items())), ensure_ascii=False, indent=2) + "\n")
    print(f"linked Natural Earth places: {len(linked)}; Wikidata populations written: {added}; total overrides: {len(overrides)}")


if __name__ == "__main__":
    main()
