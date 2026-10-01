"""Audit post-1940 Atlas gaps against current data and local Arts source notes.

This is deliberately conservative: an Arts note that does not name a practice
is an acquisition/review gap, never evidence that the published Atlas entry is
irrelevant.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"

# These notes explicitly name the same entry or provide a tightly bounded
# related source lead. The relationship is kept visible rather than silently
# treating an adjacent genre as equivalence.
EXACT_ARTS_LEADS = {
    "aze-azerbaijani-rap": (
        "direct",
        "knowledge/arts/wiki/papers/turkic-soundscapes-sultanova-rancier-2018.md",
        "Chapter 5 discusses Azerbaijani rap and the 2000/2001 Dəyirman releases; it warns not to equate rap with meyxana.",
    ),
    "sol-heello-hees-hargeysa": (
        "direct",
        "knowledge/arts/wiki/papers/johnson-development-heello-modern-somali-poetry.md",
        "The source identifies the belwo-to-heello change around Hargeysa and dates the first Heello period to c. 1948–1955.",
    ),
    "khm-chapei-dang-veng": (
        "direct",
        "knowledge/arts/wiki/papers/unesco-chapei-source-set-2015-2016.md",
        "The Cambodian inventory and nomination identify Chapei Dang Veng and its storytelling/safeguarding context.",
    ),
    "cod-musique-moderne-zaireoise": (
        "related",
        "knowledge/arts/wiki/papers/unesco-congolese-rumba-inventories-2019-2020.md",
        "Congolese rumba is a related urban-music lead, not proof that musique moderne zaïroise is equivalent to rumba.",
    ),
}

REGIONAL_ARTS_LEADS = {
    "AFG": "Garland South Asia (Afghanistan chapter)",
    "AGO": "Garland Africa (southern Africa coverage)",
    "AZE": "Turkic Soundscapes (Azerbaijan case studies)",
    "BGD": "Garland South Asia (Bangladesh chapter)",
    "BRN": "Garland Southeast Asia (Borneo/Brunei chapter)",
    "BTN": "Garland South Asia (regional baseline; Bhutan is not a dedicated chapter)",
    "CAF": "Garland Africa (Central African Republic chapter)",
    "CIV": "Garland Handbook of African Music (West Africa coverage)",
    "CMR": "Garland Africa (Central Africa coverage)",
    "COD": "Garland Africa (Central Africa coverage)",
    "DJI": "Garland Africa (Somalia/East Africa context)",
    "GNQ": "Garland Africa (Central Africa coverage)",
    "GHA": "Garland Africa and Handbook (West Africa/Ghana context)",
    "IRN": "Bloomsbury MENA genres source set",
    "KAZ": "Turkic Soundscapes and Smithsonian Central Asian Music overview",
    "KHM": "Garland Southeast Asia (Cambodia chapter)",
    "LAO": "Garland Southeast Asia (Laos chapter)",
    "LBN": "Bloomsbury MENA genres source set",
    "LBR": "Garland Handbook of African Music (West Africa/Kru context)",
    "MAR": "Bloomsbury MENA genres source set",
    "MLI": "Garland Africa (North/West Africa and Tuareg context)",
    "MMR": "Garland Southeast Asia (Myanmar/Burma chapter)",
    "MYS": "Garland Southeast Asia (peninsular Malaysia chapter)",
    "NAM": "Garland Africa (southern Africa coverage)",
    "NGA": "Garland Africa and Handbook (West Africa/Yoruba popular music)",
    "NPL": "Garland South Asia (Nepal chapter)",
    "PAK": "Garland South Asia (Pakistan chapters)",
    "PHL": "Garland Southeast Asia (Philippines chapter)",
    "PRK": "No dedicated local Arts source note currently indexed",
    "SAU": "Bloomsbury MENA genres source set",
    "SDN": "Garland Africa (Sudan chapter)",
    "SDS": "Garland Africa (Sudan/East Africa context)",
    "SGP": "Garland Southeast Asia (Singapore chapter)",
    "STP": "Garland Africa/Handbook regional coverage; country-specific evidence still needed",
    "TCD": "Garland Africa regional coverage; country-specific evidence still needed",
    "THA": "Garland Southeast Asia (Thailand chapter)",
    "TLS": "Garland Southeast Asia offers indirect Timor-Leste context only",
    "TUR": "Bloomsbury MENA genres source set and Turkic Soundscapes",
    "UZB": "Smithsonian Central Asian Music overview and Turkic Soundscapes",
    "VNM": "Garland Southeast Asia (Vietnam chapter)",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def is_post_1940(genre: dict) -> bool:
    """Modern discovery scope: documented onset from 1940 onward."""
    start = genre.get("active_from")
    if start is None:
        return False
    return start >= 1940 and (genre.get("timeline_end_status") != "ended" or (genre.get("active_to") or 0) >= 1940)


def post_ingestion_action(treatment: str) -> str:
    if treatment == "instrument_or_ensemble_taxonomy_review":
        return "After records are ingested, review associated repertoire tags and representatives; decide distinct practice vs documented merge vs justified broad family."
    if treatment == "genre_or_umbrella_representative_first":
        return "After representative expansion, compare artist/release tags and places; retain, merge, or propose a broader parent only with source support."
    if treatment == "tradition_or_performance_video_first":
        return "First establish whether the practice has a documented record-bearing repertoire. If it does, use verified artist/release relationships and recurrent regional tags for candidate discovery; otherwise retain video-only treatment."
    return "Keep video-only; do not derive a new album genre from a historical or unresolved-origin practice without separate modern evidence."


def main() -> None:
    gaps = {row["genre_id"]: row for row in csv.DictReader((RESEARCH / "app_genres_without_dedicated_rym_page.csv").open(encoding="utf-8-sig"))}
    routes = {row["genre_id"]: row for row in csv.DictReader((RESEARCH / "rym_gap_representative_record_plan.csv").open(encoding="utf-8-sig"))}
    current = load(ROOT / "web" / "data" / "genres.json")["genres"]
    rows = []
    for genre in current:
        if genre["id"] not in gaps or not is_post_1940(genre):
            continue
        lead_type, arts_path, arts_note = EXACT_ARTS_LEADS.get(genre["id"], ("regional", "", ""))
        if not arts_path:
            arts_path = "knowledge/arts/wiki/concepts/world-music-source-map.md"
            arts_note = REGIONAL_ARTS_LEADS.get(genre["country"], "No directly applicable local Arts source note is indexed; retain current project evidence and add an acquisition lead.")
        route = routes[genre["id"]]
        rows.append({
            "genre_id": genre["id"], "country": genre["country"], "name": genre["name"], "kind": genre["kind"],
            "current_catalogue_status": "retained — currently published Atlas entry",
            "documented_period": f"{gaps[genre['id']]['origin_period']} to {gaps[genre['id']]['end_period']}",
            "arts_wiki_match": lead_type, "arts_wiki_path": arts_path, "arts_wiki_relevance_note": arts_note,
            "representative_count": len(genre.get("artists") or []),
            "current_gap_treatment": route["treatment"],
            "relevance_decision": "retain pending post-ingestion review; lack of an exact Arts note is not a removal signal",
            "post_record_ingestion_action": post_ingestion_action(route["treatment"]),
        })
    rows.sort(key=lambda row: (row["country"], row["name"].casefold()))
    out = RESEARCH / "post_1940s_rym_gap_relevance_audit.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    direct = sum(row["arts_wiki_match"] == "direct" for row in rows)
    related = sum(row["arts_wiki_match"] == "related" for row in rows)
    summary = RESEARCH / "POST_RECORD_INGESTION_GENRE_DISCOVERY_PLAN.md"
    summary.write_text("\n".join([
        "# Post-record-ingestion genre discovery and taxonomy revision", "",
        f"The relevance audit covers {len(rows)} current Atlas gaps with a documented onset from the 1940s onward. "
        f"{direct} have a direct local Arts wiki lead and {related} have a qualified related lead. Remaining regional coverage is a source-routing aid, not a match.", "",
        "## Sequence", "",
        "1. Finish ingesting and identity-reviewing records for the existing eligible entries.",
        "2. For each retained entry, verify/expand representatives before using its artist and release relationships.",
        "3. Compare recurrent, region-specific tags, artists, labels, and release places to the current Atlas list. Create candidate genres only where a coherent named practice has country/region and period evidence.",
        "4. Send each candidate to the relevant country dossier; do not promote it from a tag, an RYM page, or a single recording alone.",
        "5. Revisit historical, instrument/ensemble, and umbrella entries using the completed representative/record evidence: historical entries remain video-only; instrument/ensemble entries receive a taxonomy decision; umbrella entries require scope review.",
        "",
        "## Audit rule", "",
        "Every audited row remains a current published Atlas entry. An exact local Arts wiki note strengthens the next review route; a regional or absent note creates an acquisition task, never an automatic removal.", "",
        f"See [{out.name}]({out.name}) for the row-level comparison. Regenerate with `python3 scripts/{Path(__file__).name}` after the gap and representative plans are refreshed.",
    ]) + "\n", encoding="utf-8")
    print({"rows": len(rows), "direct_arts_leads": direct, "related_arts_leads": related, "csv": str(out), "summary": str(summary)})


if __name__ == "__main__":
    main()
