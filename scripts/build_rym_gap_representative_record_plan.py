"""Route Atlas entries without a dedicated saved RYM page to safe discovery work.

The report intentionally separates historical documentation from album discovery.
It makes no new genre, representative, or recording assertions.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"

# These are reviewed editorial discovery lanes from the taxonomy review, not
# equivalence claims.  They tell a researcher where to look after checking the
# local practice in a source.
REFRAME_LANES = {
    "afg-rubab-playing": "Klasik; Pashto Folk Music",
    "arm-duduk-music": "Armenian folk music; duduk repertory",
    "bfa-balafon-music": "Balafon repertory; Mandé music",
    "mng-morin-khuur": "Morin khuur repertory; Mongolian traditional music",
    "kaz-dombra-kuy": "Dombra küy; Kazakh traditional music",
    "idn-gamelan": "Gamelan; Gamelan angklung; gender wayang",
    "khm-pinn-peat": "Pinn peat; Cambodian court music",
    "brn-gulintangan": "Gulintangan; kulintang ensemble traditions",
}
TAXONOMY_ACTIONS = {
    "afg-rubab-playing": "Reframe as Afghan rubab performance traditions; do not merge into the broad Klasik or Pashto Folk Music labels.",
    "arm-duduk-music": "Reframe as Armenian duduk performance traditions; retain a distinct practice instead of merging into Armenian folk music.",
    "bfa-balafon-music": "Reframe as place-qualified balafon performance traditions; assess a Mandé-family browse link only after source review.",
    "mng-morin-khuur": "Reframe as Morin khuur performance traditions; retain the instrument-centred practice rather than a generic folk merge.",
    "kaz-dombra-kuy": "Reframe as Kazakh dombra küy; retain its repertoire distinction rather than merging into generic traditional music.",
    "idn-gamelan": "Use an Indonesian gamelan ensemble-traditions umbrella; assess Gamelan angklung and gender wayang as sourced related forms, not automatic merges.",
    "khm-pinn-peat": "Reframe as Cambodian pinn peat court-ensemble tradition; do not reduce it to a general classical label.",
    "brn-gulintangan": "Reframe as Brunei gulintangan ensemble tradition; evaluate a broader kulintang family only with country-specific evidence.",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ended_before_1980(genre: dict) -> bool:
    return genre.get("timeline_end_status") == "ended" and (genre.get("active_to") or 9999) < 1980


def route(genre: dict) -> tuple[str, str, str, str, str, str, str]:
    """Return treatment, discovery lanes, and publication actions for one gap."""
    kind = genre.get("kind", "").casefold()
    name = genre["name"]
    country = genre["country"]
    reps = genre.get("artists") or []
    existing_reps = (
        "Verify the listed representatives in a local/specialist source, resolve their MusicBrainz IDs, and add any "
        "missing locally documented representatives before beginning record or video discovery."
        if reps else
        "First find named bearers, ensembles, or documented performer communities in a specialist, cultural-"
        "institution, label, archive, or fieldwork source; only then resolve names in MusicBrainz."
    )
    if ended_before_1980(genre):
        return (
            "historical_or_unresolved_origin_video_only",
            f"{country} {name} historical repertory; local archive and discography terms",
            existing_reps,
            "After each representative is verified, search official artist/institutional channels, broadcaster archives, "
            "and authorized fieldwork collections for a practice-specific video. Review performer, practice, and URL before publishing.",
            "No record search or album quota. Retain a reviewed video as contextual material only.",
            "No — historical tradition without a dedicated RYM page.",
            "Keep as a named historical practice; do not merge solely because recordings are scarce.",
        )
    if genre.get("active_from") is None:
        return (
            "historical_or_unresolved_origin_video_only",
            f"{country} {name}; local-language historical and contemporary practice names",
            existing_reps,
            "Treat Before 1940s as an origin-review bucket. After verifying each representative, seek a practice-specific "
            "video from official, institutional, broadcaster, or authorized archival sources.",
            "No record search or album quota while the origin is unresolved and no dedicated RYM page exists.",
            "No — unresolved-origin historical routing.",
            "Keep the existing entry and resolve its period before proposing a merge or a new parent genre.",
        )
    if genre["id"] in REFRAME_LANES or "instrument" in kind or "ensemble" in kind:
        lane = REFRAME_LANES.get(genre["id"], f"{country} {name} repertory; associated ensemble and repertoire names")
        return (
            "instrument_or_ensemble_taxonomy_review",
            lane,
            existing_reps + " Prefer named virtuosi, house ensembles, and repertoire custodians over generic instrument labels.",
            "After representative review, seek one practice-specific video per representative from an official, institutional, "
            "broadcaster, or authorized archive source.",
            "Only after taxonomy resolution, search verified representatives and the confirmed repertoire name in MusicBrainz. "
            "Keep a release group only when credits or specialist evidence establish the practice.",
            "Hold — add a records page only if the taxonomy review confirms a record-bearing genre or repertoire entity.",
            TAXONOMY_ACTIONS.get(genre["id"], "Determine whether this is a distinct named repertoire, a merge with an existing detailed practice, or a justified new broad family; do not decide from an instrument name alone."),
        )
    practice_words = ("tradition", "ritual", "dance", "ceremon", "theatre", "chant", "epic", "poetry", "storytell", "drumming")
    if any(word in kind for word in practice_words):
        return (
            "tradition_or_performance_video_first",
            f"{country} {name}; community, ritual, repertoire, and local-language performance terms",
            existing_reps + " For collective practices, a documented bearer group is an acceptable representative.",
            "After representative review, seek a practice-specific video per representative from an official, institutional, broadcaster, or authorized archive source.",
            "Hold record discovery by default. Search verified bearers and ensembles only if a source establishes a recorded "
            "repertoire or release tradition; then use MusicBrainz, national discographies, label catalogues, and authorized archive metadata.",
            "Hold — no records page unless a documented record-bearing repertoire is established.",
            "Retain as a named practice; use wider families as browse links only unless sources support an editorial merge.",
        )
    return (
        "genre_or_umbrella_representative_first",
        f"{country} {name}; local-language aliases, parent genre, and regional scene terms",
        existing_reps,
        "After representative review, seek a practice-specific video per representative from an official, institutional, broadcaster, or authorized archive source.",
        "Use the verified representatives to find release groups, then confirm a direct genre/repertoire relationship. "
        "A broader RYM chart can suggest candidates but cannot establish equivalence or nationality scope.",
        "Eligible only after scope and record relationships are verified.",
        "Expand representatives first. Then determine whether evidence supports a country-qualified genre, a merge with an existing detailed entry, or a new broad parent; never infer this from a broad chart page.",
    )


def main() -> None:
    gaps = list(csv.DictReader((RESEARCH / "app_genres_without_dedicated_rym_page.csv").open(encoding="utf-8-sig")))
    genres = {genre["id"]: genre for genre in load(ROOT / "web" / "data" / "genres.json")["genres"]}
    rows = []
    for gap in gaps:
        genre = genres[gap["genre_id"]]
        treatment, associations, representative_method, video_method, record_method, records_page, taxonomy_action = route(genre)
        rows.append({
            "genre_id": genre["id"], "country": genre["country"], "name": genre["name"],
            "kind": genre["kind"], "origin_period": gap["origin_period"], "end_period": gap["end_period"],
            "treatment": treatment, "associated_genre_or_repertoire_search_lanes": associations,
            "existing_representatives": "; ".join(genre.get("artists") or []),
            "representative_discovery_method": representative_method,
            "video_discovery_method": video_method,
            "record_discovery_method": record_method,
            "public_records_page": records_page,
            "taxonomy_resolution": taxonomy_action,
        })
    rows.sort(key=lambda row: (row["treatment"], row["country"], row["name"].casefold()))
    out = RESEARCH / "rym_gap_representative_record_plan.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    counts = Counter(row["treatment"] for row in rows)
    summary = RESEARCH / "RYM_GAP_REPRESENTATIVE_RECORD_PLAN.md"
    lines = [
        "# RYM-page gap: representative and record discovery plan", "",
        "This plan covers current Atlas entries with no dedicated user-saved RYM page. It is a research routing aid, "
        "not proof that a search lane is equivalent to the Atlas entry. The associated terms are discovery leads; "
        "all final associations require source review.", "",
        "## Treatment counts", "",
        *[f"- `{name}`: {count}" for name, count in sorted(counts.items())], "",
        "## Rules", "",
        "- Every route begins by verifying and expanding representatives. No record or video is used to manufacture a representative relationship.",
        "- An unresolved origin is displayed as **Before 1940s** for review; it follows the same video-only route as a historical tradition and does not invent an origin year.",
        "- An entry ending before 1980 is a historical-video task, not an album-coverage task, unless it already has a dedicated saved RYM page.",
        "- For instrument and ensemble entries, make a source-backed taxonomy decision—distinct repertoire, existing-entry merge, or new broad family—before any record search or records page.",
        "- Tradition, ritual, dance, theatre, oral, and performance entries are video-first even when their documented window reaches the 1980s or later. They receive a records page only when a source establishes a record-bearing repertoire.",
        "- Genre/umbrella entries need representative expansion before their scope is resolved; a broad RYM chart is never sufficient proof of equivalence or nationality.",
        "- Use MusicBrainz identities and release-group credits to resolve records; use RYM only as a private recommendation signal after the relationship is verified.",
        "- Preserve an authorized or archival non-album performance only as a fallback when fewer than nine official, verified release candidates exist.",
        "",
        f"The row-level plan is in [{out.name}]({out.name}). Regenerate both files with `python3 scripts/{Path(__file__).name}`.",
    ]
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print({"rows": len(rows), "treatments": dict(sorted(counts.items())), "csv": str(out), "summary": str(summary)})


if __name__ == "__main__":
    main()
