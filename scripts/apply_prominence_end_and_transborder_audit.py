"""Bound open timelines as approximate prominence windows and connect shared forms.

The resulting end dates are display estimates, not extinction dates. Run from the
project root after the geography/start audit and before static-data generation.
"""
import json
import re
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
CURRENT_YEAR = 2026

# Same named practice independently reviewed in each listed catalogue entry.
SHARED_GROUPS = [
    ["prk-arirang", "kor-arirang"],
    ["ind-baul", "bgd-baul-songs"],
    ["kwt-fijiri", "qat-fijiri", "bhr-fjiri", "sau-fijiri"],
    ["ben-gelede-chants", "tgo-gelede-chants"],
    ["dza-imzad", "mli-imzad-music", "ner-imzad-music"],
    ["gmb-kankurang-music", "sen-kankurang-music"],
    ["sau-khaliji", "kwt-khaliji", "qat-khaliji", "are-khaliji", "bhr-khaliji"],
    ["gab-mvet-oyeng", "cmr-mvet-oyeng", "cog-mvet-oyeng", "gnq-mvet-oyeng"],
    ["ago-san-musical-bow", "bwa-san-musical-bow-context", "nam-san-musical-bow"],
    ["kwt-arda", "qat-arda"],
    ["psx-ataba-mijana", "lbn-ataba-mijana"],
    ["tjk-shashmaqom", "uzb-shashmaqom"],
    ["ken-taarab", "tza-taarab", "com-taarab"],
]


def rounded_years(value):
    text = json.dumps(value, ensure_ascii=False)
    years = [int(year) for year in re.findall(r"\b(?:1[0-9]{3}|20[0-2][0-9])\b", text)]
    return [min(CURRENT_YEAR, year // 10 * 10) for year in years]


def estimated_end(record):
    start = record.get("active_from")
    if start is None:
        return None, "Start is unresolved, so no defensible prominence window can be calculated."
    later_hints = [year for year in rounded_years({
        "label": record.get("start_label"), "note": record.get("note"),
        "research": record.get("research"), "sources": record.get("sources"),
    }) if year > start]
    normal_window = min(CURRENT_YEAR, start + 40)
    if later_hints:
        hinted = max(later_hints)
        # A remote current source proves later documentation, not continuous popularity.
        # Keep the display window compact unless the source itself supplies a nearer endpoint.
        end = min(hinted, normal_window) if normal_window > start else hinted
        basis = f"Later source/date wording includes the {hinted // 10 * 10}s; the display window is conservatively capped at four decades."
    else:
        end = normal_window
        basis = "No later activity boundary is stated; a four-decade prominence/documentation window is used as the editorial fallback."
    if end < start:
        end = start
    return end, basis


def bound_record(record):
    if record.get("active_to") is not None:
        return
    end, basis = estimated_end(record)
    if end is None:
        return
    record["active_to"] = end
    record["timeline_end_status"] = "ended"
    record.setdefault("research", {})["prominence_end_audit"] = (
        f"Approximate end-of-prominence/display estimate, not an extinction date. {basis}"
    )


def area_from_peer(peer):
    area = {
        "country": peer["country"],
        "map_scope": peer["map_scope"],
        "regions": peer.get("regions", []),
        "relationship": "practice",
        "active_from": peer.get("active_from"),
        "active_to": peer.get("active_to"),
        "start_label": peer["start_label"],
        "note": (
            f"The same reviewed tradition is independently documented in {peer['country']}. "
            "Any directional region is a uniform, non-boundary locator; the association does not imply exclusive origin or uniform national practice."
        ),
        "sources": peer["sources"],
        "reviewed_at": "2026-09-28",
        "timeline_end_status": peer["timeline_end_status"],
    }
    if peer.get("approximate_region"):
        area["approximate_region"] = peer["approximate_region"]
    return area


def connect_group(group, entries):
    peers = [entries[ident] for ident in group]
    countries = [entry["country"] for entry in peers]
    assert len(countries) == len(set(countries)), f"shared group repeats country: {group}"
    for entry in peers:
        existing = {area["country"] for area in entry.get("associated_areas", [])}
        for peer in peers:
            if peer["country"] != entry["country"] and peer["country"] not in existing:
                entry.setdefault("associated_areas", []).append(area_from_peer(peer))
                existing.add(peer["country"])
        entry.setdefault("research", {})["transborder_audit"] = (
            "All independently reviewed countries carrying this same tradition are linked as associated areas. "
            "Map regions are representational and are not asserted cultural boundaries."
        )


def write_json(path, value):
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=f".{path.name}.", delete=False) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    temporary.replace(path)


def main():
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    entries = {entry["id"]: entry for entry in data["entries"] if entry["status"] == "published"}
    missing = {ident for group in SHARED_GROUPS for ident in group} - set(entries)
    assert not missing, f"missing shared published entries: {sorted(missing)}"
    for entry in entries.values():
        bound_record(entry)
        for area in entry.get("associated_areas", []):
            if area.get("active_to") is None:
                end, basis = estimated_end(area)
                if end is not None:
                    area["active_to"] = end
                    area["timeline_end_status"] = "ended"
                    area["note"] += f" Approximate prominence end; not an extinction claim. {basis}"
    for group in SHARED_GROUPS:
        connect_group(group, entries)
    write_json(CATALOGUE, data)


if __name__ == "__main__":
    main()
