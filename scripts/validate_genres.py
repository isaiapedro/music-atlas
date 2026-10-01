"""Check published genre records against the bundled map before release."""
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

DATA = Path(__file__).resolve().parents[1] / "web" / "data"
APPROXIMATE_REGIONS = {
    "north", "north-east", "east", "south-east", "south",
    "south-west", "west", "north-west", "central",
}
IMAGE_PROVIDERS = {"wikimedia_commons", "openverse", "smithsonian_open_access", "institutional"}
REUSABLE_IMAGE_LICENSES = {
    "CC0", "PDM", "Public Domain",
    "CC BY 2.0", "CC BY 2.5", "CC BY 3.0", "CC BY 4.0",
    "CC BY-SA 2.0", "CC BY-SA 2.5", "CC BY-SA 3.0", "CC BY-SA 4.0",
}


def map_keys():
    countries = json.loads((DATA / "countries.geojson").read_text())["features"]
    regions = json.loads((DATA / "regions.geojson").read_text())["features"]
    country_codes = {feature["properties"]["code"] for feature in countries}
    region_names = {}
    for feature in regions:
        props = feature["properties"]
        region_names.setdefault(props["code"], set()).add(props["name"])
    return country_codes, region_names


def valid_source(source):
    """Allow a public URL or a bibliographic citation; never a private file path."""
    if isinstance(source, str):
        return source.startswith("https://")
    if not isinstance(source, dict) or set(source) - {"citation", "url"}:
        return False
    citation = source.get("citation")
    url = source.get("url")
    return (isinstance(citation, str) and bool(citation.strip()) and
            (url is None or (isinstance(url, str) and url.startswith("https://"))))


def valid_image(image):
    """Accept only reviewed, attribution-complete images with reusable licences."""
    if image is None:
        return True
    if not isinstance(image, dict):
        return False
    required = {"image_url", "source_page_url", "title", "creator", "license",
                "attribution", "depicts", "provider", "reviewed_at"}
    if set(image) != required or image["provider"] not in IMAGE_PROVIDERS:
        return False
    if image["license"] not in REUSABLE_IMAGE_LICENSES:
        return False
    if not all(isinstance(image[key], str) and image[key].strip() for key in required - {"provider"}):
        return False
    for field in ("image_url", "source_page_url"):
        parsed = urlparse(image[field])
        if parsed.scheme != "https" or not parsed.netloc:
            return False
    return True

def validate_record(record, country_codes, region_names, current_year=None):
    """Validate one published record; country scope does not claim every region."""
    current_year = current_year or date.today().year
    assert isinstance(record.get("id"), str) and record["id"].strip(), record
    assert record["country"] in country_codes, record["id"]
    assert record["name"] and record["kind"] and record["note"], record["id"]
    assert len(record["note"].strip()) >= 60, f"genre lacks a useful fallback description: {record['id']}"
    generic_prefixes = (
        "Country-wide fill is a coarse association.",
        "Country association used pending",
        "Tripoli continuity does not imply",
        "Moorish-community association, not",
        "Historical Hargeysa association only",
    )
    assert not record["note"].startswith(generic_prefixes), f"generic fallback description: {record['id']}"
    assert record.get("wikipedia_title") is None or (isinstance(record["wikipedia_title"], str) and record["wikipedia_title"].strip()), record["id"]
    wiki_title = record.get("wikipedia_title")
    wiki_language = record.get("wikipedia_language", "en")
    assert wiki_language in {"en", "fr"}, record["id"]
    if not wiki_title:
        assert not record.get("wikipedia_section") and not record.get("wikipedia_focus") and not record.get("wikipedia_url"), record["id"]
    else:
        for field in ("wikipedia_section", "wikipedia_focus"):
            value = record.get(field)
            assert value is None or (isinstance(value, str) and value.strip()), record["id"]
        assert not record.get("wikipedia_focus") or record.get("wikipedia_section"), record["id"]
        if record.get("wikipedia_url"):
            parsed = urlparse(record["wikipedia_url"])
            assert parsed.scheme == "https" and parsed.hostname == f"{wiki_language}.wikipedia.org" and parsed.path.startswith("/wiki/"), record["id"]
    scope = record.get("map_scope")
    assert scope in {"regions", "country", "approximate"}, record["id"]
    mapped_regions = record.get("regions")
    assert isinstance(mapped_regions, list) and len(mapped_regions) == len(set(mapped_regions)), record["id"]
    if scope == "regions":
        assert mapped_regions and set(mapped_regions) <= region_names.get(record["country"], set()), record["id"]
    elif scope == "country":
        assert mapped_regions == [], record["id"]
        assert not record.get("approximate_region"), record["id"]
    else:
        assert mapped_regions == [], record["id"]
        assert record.get("approximate_region") in APPROXIMATE_REGIONS, record["id"]
    start = record["active_from"]
    end = record["active_to"]
    assert start is None or (type(start) is int and 1 <= start <= current_year), record["id"]
    assert end is None or (type(end) is int and (start is None or start <= end) and end <= current_year), record["id"]
    assert record.get("timeline_end_status") in {"present", "unknown", "ended"}, record["id"]
    assert (end is None) == (record["timeline_end_status"] != "ended"), record["id"]
    assert record["start_label"], record["id"]
    areas = record.get("associated_areas", [])
    assert isinstance(areas, list), record["id"]
    seen_area_countries = {record["country"]}
    for area in areas:
        assert isinstance(area, dict) and area.get("country") in country_codes, record["id"]
        assert area["country"] not in seen_area_countries, record["id"]
        seen_area_countries.add(area["country"])
        assert area.get("relationship") in {"practice", "later_scene", "strong_association", "influence_zone"}, record["id"]
        assert area.get("map_scope") in {"regions", "country", "approximate"}, record["id"]
        names = area.get("regions")
        assert isinstance(names, list) and len(names) == len(set(names)), record["id"]
        if area["map_scope"] == "regions":
            assert names and set(names) <= region_names.get(area["country"], set()), record["id"]
        elif area["map_scope"] == "country":
            assert names == [], record["id"]
            assert not area.get("approximate_region"), record["id"]
        else:
            assert names == [], record["id"]
            assert area.get("approximate_region") in APPROXIMATE_REGIONS, record["id"]
        area_start, area_end = area.get("active_from"), area.get("active_to")
        assert area_start is None or (type(area_start) is int and 1 <= area_start <= current_year), record["id"]
        assert area_end is None or (type(area_end) is int and (area_start is None or area_start <= area_end) and area_end <= current_year), record["id"]
        assert area.get("timeline_end_status") in {"present", "unknown", "ended"}, record["id"]
        assert (area_end is None) == (area["timeline_end_status"] != "ended"), record["id"]
        assert area.get("start_label") and area.get("note") and area.get("reviewed_at"), record["id"]
        assert area.get("sources") and all(valid_source(source) for source in area["sources"]), record["id"]
    assert isinstance(record["artists"], list) and len(record["artists"]) <= 3 and all(isinstance(name, str) and name.strip() for name in record["artists"]), record["id"]
    examples = record.get("youtube_examples", [])
    assert isinstance(examples, list), record["id"]
    example_artists = set()
    for example in examples:
        assert isinstance(example, dict), record["id"]
        practice_level = example.get("attribution_basis") in {
            "user-approved practice-level example",
            "user-authorized practice-level example",
            "institutional practice-level example",
        }
        assert example.get("artist") in record["artists"] or practice_level, record["id"]
        assert example.get("title") and example.get("reviewed_at"), record["id"]
        parsed = urlparse(example.get("youtube_url", ""))
        assert parsed.scheme == "https" and parsed.hostname in {"www.youtube.com", "youtube.com"}, record["id"]
        assert parsed.path == "/watch" and re.fullmatch(r"v=[A-Za-z0-9_-]{11}", parsed.query), record["id"]
        assert example["artist"] not in example_artists, record["id"]
        example_artists.add(example["artist"])
    assert record.get("sample") is None, record["id"]
    assert record["sources"] and all(valid_source(source) for source in record["sources"]), record["id"]
    assert valid_image(record.get("image")), record["id"]


def validate(records, country_codes, region_names):
    seen = set()
    for record in records:
        validate_record(record, country_codes, region_names)
        assert record["id"] not in seen, record["id"]
        seen.add(record["id"])


if __name__ == "__main__":
    records = json.loads((DATA / "genres.json").read_text())["genres"]
    country_codes, region_names = map_keys()
    validate(records, country_codes, region_names)
    print(f"{len(records)} published records in {len({item['country'] for item in records})} countries; {len(country_codes)} mapped countries total")
