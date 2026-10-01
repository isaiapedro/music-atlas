"""Build readable RYM-page coverage gaps for new candidates and published genres."""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"

# Saved RYM headings that are direct name variants of an existing Atlas record.
# Broader umbrella pages (for example, Arabic Folk Music) are deliberately absent.
DIRECT_PAGE_ALIASES = {
    "garba": ["ind-garba"],
    "dohori": ["npl-lok-dohori"],
    "quan ho": ["vnm-quan-ho"],
    "tassu": ["sen-taasu"],
    "timbila": ["moz-chopi-timbila"],
    "turkish mevlevi music": ["tur-mevlevi-ayin"],
    "shaabi": ["egy-shaabi"],
}
DIRECT_CLASSIFICATIONS = {
    "exact_name_candidate", "shortened_name_candidate", "transliteration_candidate",
    "translated_name_candidate",
}


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dedicated_page_ids(crosswalk: list[dict]) -> set[str]:
    ids = set()
    for row in crosswalk:
        if row["classification"] in DIRECT_CLASSIFICATIONS:
            ids.update(json.loads(row["atlas_genre_id_candidates"]))
        ids.update(DIRECT_PAGE_ALIASES.get(norm(row["rym_chart_label"]), []))
    return ids


def period(entry: dict) -> tuple[str, str]:
    start = entry.get("active_from")
    start_label = entry.get("start_label") or "start unresolved"
    # The interface has one inclusive historical bucket before the 1940s. An
    # unresolved origin is routed there for review, without inventing a year.
    origin = f"{start} — {start_label}" if start is not None else "Before 1940s"
    if entry.get("timeline_end_status") == "ended":
        end = str(entry.get("active_to") or "Ended year unresolved")
    elif entry.get("timeline_end_status") == "present":
        end = "Present"
    else:
        end = "Last prominence unresolved"
    return origin, end


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    crosswalk = list(csv.DictReader((RESEARCH / "rym_chart_page_crosswalk.csv").open(encoding="utf-8-sig")))
    page_labels = {norm(row["rym_chart_label"]) for row in crosswalk}
    candidates = read_json(RESEARCH / "rym_new_genre_candidates.json")["proposed_main_genres"]
    new_rows = []
    for candidate in candidates:
        if norm(candidate["name"]) not in page_labels:
            refs = candidate["rym_references"]
            new_rows.append({
                "candidate_id": candidate["id"], "name": candidate["name"],
                "country_codes": ";".join(candidate["country_codes"]),
                "kind": candidate["kind"], "main_genre_assessment": candidate["main_genre_assessment"],
                "rym_tag_references": "; ".join(
                    f"{ref['label']} (primary {ref['primary_occurrences']}, secondary {ref['secondary_occurrences']})"
                    for ref in refs),
                "status": candidate["status"], "next_review": candidate["next_review"],
            })
    new_rows.sort(key=lambda row: row["name"])

    published = read_json(ROOT / "web" / "data" / "genres.json")["genres"]
    covered = dedicated_page_ids(crosswalk)
    app_rows = []
    for genre in published:
        if genre["id"] in covered:
            continue
        origin, end = period(genre)
        videos = genre.get("youtube_examples") or []
        artists = genre.get("artists") or []
        app_rows.append({
            "genre_id": genre["id"], "country": genre["country"], "name": genre["name"],
            "kind": genre["kind"], "origin_period": origin, "end_period": end,
            "reviewed_videos": len(videos), "has_reviewed_video": "yes" if videos else "no",
            "representative_count": len(artists), "representatives": "; ".join(artists),
            "rym_status": "no dedicated saved RYM chart page",
        })
    app_rows.sort(key=lambda row: (row["country"], row["name"].casefold()))

    new_path = RESEARCH / "new_genres_without_dedicated_rym_page.csv"
    app_path = RESEARCH / "app_genres_without_dedicated_rym_page.csv"
    write_csv(new_path, new_rows, list(new_rows[0]) if new_rows else [])
    write_csv(app_path, app_rows, list(app_rows[0]) if app_rows else [])
    print({"new_genres_without_dedicated_page": len(new_rows),
           "app_genres_without_dedicated_page": len(app_rows),
           "new_output": str(new_path), "app_output": str(app_path)})


if __name__ == "__main__":
    main()
