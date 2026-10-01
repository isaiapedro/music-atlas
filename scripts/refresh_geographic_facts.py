"""Refresh saved country and region population/area facts from Wikidata."""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "research/wiki_articles.json", ROOT / "web/data/articles.json"]
UNITS = {
    "http://www.wikidata.org/entity/Q712226": 1,
    "http://www.wikidata.org/entity/Q25343": 0.000001,
    "http://www.wikidata.org/entity/Q35852": 0.01,
    "http://www.wikidata.org/entity/Q232291": 2.589988,
}


def year(claim):
    try:
        return int(claim["qualifiers"]["P585"][0]["datavalue"]["value"]["time"][1:5])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def quantity(entity, prop, require_date=False):
    values = []
    for claim in entity.get("claims", {}).get(prop, []):
        try:
            raw = claim["mainsnak"]["datavalue"]["value"]
            amount = float(raw["amount"])
        except (KeyError, TypeError, ValueError):
            continue
        dated = year(claim)
        if require_date and dated is None:
            continue
        values.append((dated or 0, claim.get("rank") == "preferred", amount, raw.get("unit")))
    return max(values, default=None)


def fetch(ids):
    query = urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(ids),
                                    "props": "claims", "format": "json", "formatversion": "2"})
    request = urllib.request.Request("https://www.wikidata.org/w/api.php?" + query,
                                     headers={"User-Agent": "MusicAtlas/1.0 geographic fact refresh"})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                entities = json.load(response)["entities"]
                return list(entities.values()) if isinstance(entities, dict) else entities
        except HTTPError as error:
            if error.code != 429 or attempt == 7:
                raise
            time.sleep(2 ** (attempt + 1))


def main():
    snapshots = [json.loads(path.read_text()) for path in FILES]
    linked = {}
    for scope in ("countries", "regions"):
        for key, article in snapshots[0][scope].items():
            if not article:
                continue
            match = re.search(r"/wiki/(Q\d+)$", article.get("wikidata_url") or "")
            if match:
                linked.setdefault(match.group(1), []).append((scope, key))
    updated = 0
    ids = sorted(linked)
    for start in range(0, len(ids), 25):
        for entity in fetch(ids[start:start + 25]):
            population = quantity(entity, "P1082", require_date=True)
            area = quantity(entity, "P2046")
            area_km2 = round(area[2] * UNITS[area[3]], 2) if area and area[3] in UNITS else None
            for scope, key in linked.get(entity.get("id"), []):
                for snapshot in snapshots:
                    article = snapshot[scope][key]
                    article["population"] = ({"value": round(population[2]), "year": population[0]}
                                               if population else None)
                    article["area_km2"] = area_km2
                updated += 1
        for path, snapshot in zip(FILES, snapshots):
            path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
        time.sleep(1)
    print(f"refreshed {updated} geographic records from {len(ids)} Wikidata entities")


if __name__ == "__main__":
    main()
