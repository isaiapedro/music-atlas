"""Reduce Natural Earth populated places to mapped national capital points."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "web" / "data"
countries = json.loads((DATA / "countries.geojson").read_text())
codes = {feature["properties"]["code"] for feature in countries["features"]}
places = json.loads((DATA / "capitals.source.geojson").read_text())
capitals = []
for feature in places["features"]:
    props = feature["properties"]
    if props.get("ADM0CAP") != 1 or props.get("ADM0_A3") not in codes:
        continue
    capitals.append({
        "code": props["ADM0_A3"],
        "name": props.get("NAME_EN") or props["NAME"],
        "coordinates": [round(value, 3) for value in feature["geometry"]["coordinates"]],
    })

(DATA / "capitals.json").write_text(json.dumps(capitals, ensure_ascii=False, separators=(",", ":")))
print(len(capitals), "capital points for", len({item["code"] for item in capitals}), "country records")
