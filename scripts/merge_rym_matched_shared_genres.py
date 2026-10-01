"""Consolidate verified cross-country copies of one shared genre entity.

For Fijirī and Khalījī, a matching saved RYM page is an additional identity check.
For other explicitly shared entries, same genre identity plus reciprocal,
independently sourced country links are required. RYM is not geography evidence.
Unmatched genre identities are never deleted by this script.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research/genre_catalogue.json"
RYM_DB = ROOT / ".local/rym/chart_catalogue.sqlite3"
GROUPS = {
    "kwt-fijiri": {"kwt-fijiri", "qat-fijiri", "bhr-fjiri", "sau-fijiri"},
    "sau-khaliji": {"sau-khaliji", "are-khaliji", "bhr-khaliji", "kwt-khaliji", "qat-khaliji"},
    "kor-arirang": {"kor-arirang", "prk-arirang"},
    "ind-baul": {"ind-baul", "bgd-baul-songs"},
    "ben-gelede-chants": {"ben-gelede-chants", "tgo-gelede-chants"},
    "dza-imzad": {"dza-imzad", "mli-imzad-music", "ner-imzad-music"},
    "gmb-kankurang-music": {"gmb-kankurang-music", "sen-kankurang-music"},
    "gab-mvet-oyeng": {"gab-mvet-oyeng", "cmr-mvet-oyeng", "cog-mvet-oyeng"},
    "ago-san-musical-bow": {"ago-san-musical-bow", "bwa-san-musical-bow-context", "nam-san-musical-bow"},
    "kwt-arda": {"kwt-arda", "qat-arda"},
    "lbn-ataba-mijana": {"lbn-ataba-mijana", "psx-ataba-mijana"},
}
ID_REDIRECTS = {
    "qat-fijiri": "kwt-fijiri", "bhr-fjiri": "kwt-fijiri", "sau-fijiri": "kwt-fijiri",
    "are-khaliji": "sau-khaliji", "bhr-khaliji": "sau-khaliji",
    "kwt-khaliji": "sau-khaliji", "qat-khaliji": "sau-khaliji",
    "prk-arirang": "kor-arirang", "bgd-baul-songs": "ind-baul",
    "tgo-gelede-chants": "ben-gelede-chants", "mli-imzad-music": "dza-imzad",
    "ner-imzad-music": "dza-imzad", "sen-kankurang-music": "gmb-kankurang-music",
    "cmr-mvet-oyeng": "gab-mvet-oyeng", "cog-mvet-oyeng": "gab-mvet-oyeng",
    "bwa-san-musical-bow-context": "ago-san-musical-bow", "nam-san-musical-bow": "ago-san-musical-bow",
    "qat-arda": "kwt-arda", "psx-ataba-mijana": "lbn-ataba-mijana",
}
SHARED_NOTES = {
    "kwt-fijiri": "Fijirī is a Gulf maritime song tradition associated with seafaring and pearl-diving communities. Sources document practice across Bahrain, Kuwait, Qatar, and eastern Saudi Arabia; the map records these supported associations and does not imply an exclusive origin.",
    "sau-khaliji": "Khalījī is commercially circulating popular music associated with the Arabian Peninsula and Gulf. The reviewed sources identify Saudi Arabia, Kuwait, Bahrain, Qatar, and the UAE among its principal settings and describe its emergence in public circulation around the 1980s; this is not an exact origin date.",
    "kor-arirang": "Arirang is a family of Korean songs with regional and historical variations. UNESCO documents an orally transmitted lyrical singing tradition in both North and South Korea, including traditional, symphonic and modern arrangements.",
    "ind-baul": "Baul songs are devotional songs associated with Baul communities in the Bengal region. Sources document the same living tradition in India and Bangladesh; the map records those associations without assigning exclusive ownership.",
    "ben-gelede-chants": "Gélédé is a music, dance and masked-performance tradition associated with Yoruba-Nago communities. Its practice crosses present-day Benin, Nigeria and Togo; country boundaries do not define the tradition.",
    "dza-imzad": "Imzad is a Tuareg musical tradition centred on the bowed imzad, historically played by women and associated with singing and poetry. Sources document related practice across Algeria, Mali and Niger.",
    "gmb-kankurang-music": "Kankurang is a Manding initiation and performance tradition involving music, dance and a masked figure. Its documented practice crosses The Gambia and Senegal.",
    "gab-mvet-oyeng": "Mvet oyeng is a Central African musical storytelling and performance tradition associated with Fang communities. Its documented practice crosses present-day Gabon, Cameroon and the Republic of the Congo.",
    "ago-san-musical-bow": "San musical-bow traditions encompass community-specific songs and bow practices across Southern Africa. The map links the independently documented Angola, Botswana and Namibia associations without presenting them as separate national genres.",
    "kwt-arda": "ʿArḍa is a Gulf performance tradition combining poetry, song, percussion and coordinated movement. The reviewed entries document related practice in Kuwait and Qatar.",
    "lbn-ataba-mijana": "ʿAtābā and mījānā are paired Levantine vocal forms used in folk singing and recordings. Sources describe shared practice in Lebanon and Palestine while preserving locally specific performance histories.",
}

PAGE_REQUIRED = {"kwt-fijiri", "sau-khaliji"}


def display_key(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    value = re.sub(r"\b(music|dance|song|songs|chant|chants|tradition|traditions|style|genre|the)\b", " ", value)
    return " ".join(dict.fromkeys(re.findall(r"[a-z0-9]+", value)))


def primary_area(entry):
    area = {key: entry[key] for key in ("country", "map_scope", "regions", "active_from", "active_to", "start_label", "note", "sources")}
    if entry.get("approximate_region"):
        area["approximate_region"] = entry["approximate_region"]
    area["relationship"] = "practice"
    area["reviewed_at"] = entry.get("research", {}).get("reviewed_at", "2026-09-30")
    area["timeline_end_status"] = entry["timeline_end_status"]
    return area


def area_quality(area):
    return (len(area.get("regions", [])), len(area.get("sources", [])), len(area.get("note", "")))


def merge_group(entries, canonical_id, ids):
    members = [entry for entry in entries if entry["id"] in ids]
    if {entry["id"] for entry in members} != ids:
        raise ValueError(f"expected all explicit members for {canonical_id}; found {[e['id'] for e in members]}")
    if len({display_key(entry["name"]) for entry in members}) != 1:
        raise ValueError(f"members do not share one normalized genre identity: {canonical_id}")
    countries = {entry["country"] for entry in members}
    for member in members:
        linked = {area["country"] for area in member.get("associated_areas", [])}
        missing = countries - {member["country"]} - linked
        if missing:
            raise ValueError(f"member {member['id']} lacks existing cross-country links to {sorted(missing)}")
    base = next(entry.copy() for entry in members if entry["id"] == canonical_id)
    best_description = max(members, key=lambda e: (len(e.get("note", "")), len(e.get("sources", []))))
    base["name"] = best_description["name"]
    base["kind"] = best_description["kind"]
    base["note"] = SHARED_NOTES.get(canonical_id, best_description["note"])
    if best_description.get("wikipedia_title"):
        for key in ("wikipedia_title", "wikipedia_language", "wikipedia_section", "wikipedia_focus", "wikipedia_url"):
            if key in best_description:
                base[key] = best_description[key]
            else:
                base.pop(key, None)

    source_records = {}
    sources = []
    for member in members:
        source_records[member["id"]] = {
            "country": member["country"], "name": member["name"], "note": member["note"],
            "sources": member.get("sources", []), "research": member.get("research", {}),
        }
        for source in member.get("sources", []):
            if source not in sources:
                sources.append(source)
    base["sources"] = sources

    areas = {}
    for member in members:
        candidate_areas = [primary_area(member), *member.get("associated_areas", [])]
        for area in candidate_areas:
            code = area["country"]
            if code == base["country"]:
                continue
            if code not in areas or area_quality(area) > area_quality(areas[code]):
                areas[code] = area
    base["associated_areas"] = [areas[code] for code in sorted(areas)]

    artists = list(dict.fromkeys(name for member in members for name in member.get("artists", [])))
    videos = []
    seen_video_urls = set()
    seen_video_artists = set()
    for member in members:
        for video in member.get("youtube_examples", []):
            if video["youtube_url"] not in seen_video_urls and video["artist"] not in seen_video_artists:
                seen_video_urls.add(video["youtube_url"])
                seen_video_artists.add(video["artist"])
                videos.append(video)
    # The published schema allows three representative artists. Preserve the
    # rest in the audit record while retaining all linked examples' attributions.
    artists = list(dict.fromkeys([*artists, *(video["artist"] for video in videos)]))
    base["artists"] = artists[:3]
    base["youtube_examples"] = [video for video in videos if video["artist"] in base["artists"]]
    base["image"] = next((entry.get("image") for entry in members if entry.get("image")), None)
    research_source = best_description.get("research", {})
    base["research"] = dict(research_source)
    base["research"]["shared_entity_merge"] = {
        "reviewed_at": "2026-09-30",
        "canonical_id": canonical_id,
        "former_ids": sorted(ids - {canonical_id}),
        "basis": "User-directed single shared musical entity; same display identity and reciprocal cross-country links; matching saved RYM chart page used only to confirm that a corresponding category was collected.",
        "area_evidence_and_original_descriptions": source_records,
        "all_representative_artists_before_schema_limit": artists,
        "all_original_youtube_examples": [video for member in members for video in member.get("youtube_examples", [])],
    }
    return base


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write the consolidated source catalogue")
    args = parser.parse_args()
    if not RYM_DB.exists():
        raise SystemExit("Import saved RYM charts first with scripts/import_rym_chart_pages.py")
    db = sqlite3.connect(RYM_DB)
    page_keys = {display_key(row[0]) for row in db.execute("SELECT chart_label FROM chart_page")}
    db.close()
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    entries = data["entries"]
    merged = []
    removed_ids = set()
    for canonical_id, ids in GROUPS.items():
        members = [entry for entry in entries if entry["id"] in ids]
        existing = next((entry for entry in entries if entry["id"] == canonical_id), None)
        if len(members) == 1 and existing and existing.get("research", {}).get("shared_entity_merge"):
            if args.apply:
                existing["note"] = SHARED_NOTES[canonical_id]
                audit = existing["research"]["shared_entity_merge"]
                audit.setdefault("all_original_youtube_examples", list(existing.get("youtube_examples", [])))
                unique_examples = []
                seen_artists = set()
                for example in existing.get("youtube_examples", []):
                    if example["artist"] not in seen_artists and len(seen_artists) < 3:
                        seen_artists.add(example["artist"])
                        unique_examples.append(example)
                existing["youtube_examples"] = unique_examples
                existing["artists"] = list(dict.fromkeys([*existing.get("artists", []), *sorted(seen_artists)]))[:3]
                existing["youtube_examples"] = [video for video in existing["youtube_examples"]
                                                 if video["artist"] in existing["artists"]]
                print(f"UPDATE shared description: {canonical_id}")
            else:
                print(f"PREVIEW shared description: {canonical_id}")
            continue
        if not members:
            continue
        if canonical_id in PAGE_REQUIRED and display_key(members[0]["name"]) not in page_keys:
            raise ValueError(f"no saved RYM chart category matches {canonical_id}; refusing to merge")
        if any(entry.get("status") != "published" for entry in members):
            raise ValueError(f"unpublished member found in {canonical_id}; refusing to merge")
        merged.append(merge_group(entries, canonical_id, ids))
        removed_ids.update(ids - {canonical_id})
        print(f"{'MERGE' if args.apply else 'PREVIEW'} {canonical_id}: {', '.join(sorted(ids))} -> one entity, {len(merged[-1]['associated_areas']) + 1} areas")
    if args.apply:
        replacement = []
        by_id = {entry["id"]: entry for entry in merged}
        for entry in entries:
            if entry["id"] in by_id:
                replacement.append(by_id[entry["id"]])
            elif entry["id"] not in removed_ids:
                replacement.append(entry)
        data["entries"] = replacement
        CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for path in sorted((ROOT / "research/countries").glob("*.json")):
            dossier = json.loads(path.read_text(encoding="utf-8"))
            changed = False
            for candidate in dossier.get("candidates", []):
                redirect = ID_REDIRECTS.get(candidate.get("id")) or ID_REDIRECTS.get(candidate.get("publication_id"))
                if redirect:
                    candidate["publication_id"] = redirect
                    changed = True
            if changed:
                path.write_text(json.dumps(dossier, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        mapping_path = ROOT / "research/musicbrainz_genre_mappings.json"
        if mapping_path.exists():
            mappings = json.loads(mapping_path.read_text(encoding="utf-8"))
            for mapping in mappings.get("mappings", []):
                mapping["atlas_ids"] = list(dict.fromkeys(ID_REDIRECTS.get(value, value)
                                                            for value in mapping.get("atlas_ids", [])))
            mapping_path.write_text(json.dumps(mappings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {CATALOGUE}; consolidated {len(removed_ids)} duplicate IDs without deleting unmatched genre identities")


if __name__ == "__main__":
    main()
