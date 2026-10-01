"""Build country-scoped Natural Earth amenity layers for the browser.

The downloaded 10m shapefiles are intentionally kept outside the application
repository. Run this script with ``--source-dir`` pointing at their extracted
directory. It emits compact, public-domain GeoJSON beside the existing map
assets and keeps only features whose representative point falls inside one of
the mapped Africa/Asia country geometries.
"""
import argparse
import json
from pathlib import Path

import shapefile


def point_in_ring(point, ring):
    x, y = point
    inside = False
    for index, (x1, y1) in enumerate(ring):
        x2, y2 = ring[index - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def point_in_geometry(point, geometry):
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    return any(point_in_ring(point, polygon[0]) and not any(point_in_ring(point, hole) for hole in polygon[1:]) for polygon in polygons)


def representative(shape):
    points = shape.points
    return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))


def compact(value):
    if value and isinstance(value[0], (int, float)):
        return [round(value[0], 3), round(value[1], 3)]
    return [compact(item) for item in value]


def country_for(point, countries):
    for feature in countries:
        if point_in_geometry(point, feature["geometry"]):
            return feature["properties"]["code"]
    return None


def convert(source_dir, output_dir, basename, kind, fields):
    reader = shapefile.Reader(str(source_dir / basename))
    names = [field[0] for field in reader.fields[1:]]
    features = []
    for shape, record in zip(reader.shapes(), reader.records()):
        point = representative(shape)
        code = country_for(point, countries)
        if not code:
            continue
        row = {key: record[names.index(source)] for key, source in fields.items() if source in names}
        row["code"] = code
        source_geometry = shape.__geo_interface__
        geometry = {"type": "Point", "coordinates": [round(point[0], 3), round(point[1], 3)]} if kind == "Point" else {"type": source_geometry["type"], "coordinates": compact(source_geometry["coordinates"])}
        features.append({"type": "Feature", "properties": row, "geometry": geometry})
    target = output_dir / basename.replace("ne_10m_", "").replace("_landscan", "")
    target = target.with_suffix(".geojson")
    target.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, separators=(",", ":")))
    print(target.name, len(features))


parser = argparse.ArgumentParser()
parser.add_argument("--source-dir", type=Path, required=True)
parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "web" / "data")
args = parser.parse_args()
countries = json.loads((args.output_dir / "countries.geojson").read_text())["features"]
args.output_dir.mkdir(parents=True, exist_ok=True)
convert(args.source_dir, args.output_dir, "ne_10m_populated_places", "Point", {"name": "NAME", "feature": "FEATURECLA", "population": "POP_MAX", "population_min": "POP_MIN", "wikidata_id": "WIKIDATAID", "rank": "SCALERANK"})
convert(args.source_dir, args.output_dir, "ne_10m_urban_areas", "Polygon", {"area_sqkm": "area_sqkm", "rank": "scalerank"})
convert(args.source_dir, args.output_dir, "ne_10m_rivers_lake_centerlines", "Line", {"name": "name_en", "feature": "featurecla", "rank": "scalerank"})
convert(args.source_dir, args.output_dir, "ne_10m_lakes", "Polygon", {"name": "name_en", "feature": "featurecla", "rank": "scalerank"})
convert(args.source_dir, args.output_dir, "ne_10m_geography_regions_elevation_points", "Point", {"name": "name_en", "feature": "featurecla", "elevation_m": "elevation", "rank": "scalerank"})
