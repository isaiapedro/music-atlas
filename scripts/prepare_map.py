"""Build the small, browser-ready Africa/Asia map from Natural Earth GeoJSON."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "web" / "data"
CONTINENTS = {"Africa", "Asia"}


def compact_coordinates(value):
    if value and isinstance(value[0], (int, float)):
        return [round(value[0], 3), round(value[1], 3)]
    return [compact_coordinates(item) for item in value]


countries = json.loads((ROOT / "countries.source.geojson").read_text())
selected = []
codes = set()
for feature in countries["features"]:
    props = feature["properties"]
    if props.get("CONTINENT") not in CONTINENTS:
        continue
    code = props["ADM0_A3"]
    codes.add(code)
    selected.append({"type": "Feature", "properties": {"code": code, "name": props["NAME_EN"], "continent": props["CONTINENT"]}, "geometry": {"type": feature["geometry"]["type"], "coordinates": compact_coordinates(feature["geometry"]["coordinates"])}})

regions = json.loads((ROOT / "regions.source.geojson").read_text())
selected_regions = []
for feature in regions["features"]:
    props = feature["properties"]
    if props.get("adm0_a3") not in codes or not feature.get("geometry"):
        continue
    selected_regions.append({"type": "Feature", "properties": {"code": props["adm0_a3"], "name": props.get("name_en") or props["name"]}, "geometry": {"type": feature["geometry"]["type"], "coordinates": compact_coordinates(feature["geometry"]["coordinates"])}})

for name, features in (("countries.geojson", selected), ("regions.geojson", selected_regions)):
    (ROOT / name).write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, separators=(",", ":")))
    print(name, len(features), (ROOT / name).stat().st_size)
