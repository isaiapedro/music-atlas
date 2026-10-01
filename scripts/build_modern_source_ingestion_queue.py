"""Build the source-ingestion queue behind the 1950s–present roadmap.

It reports documentation gaps, never a claim that an empty decade lacked music.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
MODERN_DECADES = (1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def period_groups(visible: set[int]) -> list[str]:
    groups = []
    if not any(year in visible for year in (1950, 1960, 1970)):
        groups.append("1950–1979")
    if not any(year in visible for year in (1980, 1990)):
        groups.append("1980–1999")
    if 2000 not in visible:
        groups.append("2000–2009")
    if 2010 not in visible:
        groups.append("2010–2019")
    if 2020 not in visible:
        groups.append("2020–present")
    return groups


def priority(visible: set[int], document_count: int) -> str:
    if not any(year >= 1950 for year in visible):
        return "P0 — no modern visibility"
    if 2000 not in visible and 2010 not in visible and 2020 not in visible:
        return "P1 — no 2000s–present visibility"
    if document_count == 0:
        return "P1 — no acquired source bundle"
    if 2020 not in visible:
        return "P2 — current-period verification missing"
    return "P3 — complete remaining period/source audit"


def material_needed(missing: list[str], document_count: int) -> str:
    needs = []
    if document_count == 0:
        needs.append("one lawful national/regional history source with a chapter or article for the mapped area")
    if "1950–1979" in missing or "1980–1999" in missing:
        needs.append("a postwar national or city-scene chronology (1950s–1990s), ideally scholarly and local-language searchable")
    if any(period in missing for period in ("2000–2009", "2010–2019", "2020–present")):
        needs.append("a 2000s–present scene source: thesis/article, broadcaster archive, label/discography catalogue, festival programme, or cultural-policy record")
    needs.append("representative evidence: performer/ensemble names linked by a source to the named practice or scene")
    needs.append("local-language aliases, scripts, city/region names, and migration/diaspora terms for repeatable discovery")
    return "; ".join(needs)


def main() -> None:
    plan = load(RESEARCH / "country_decade_plan.json")["countries"]
    genres = load(ROOT / "web" / "data" / "genres.json")["genres"]
    by_country = defaultdict(list)
    for genre in genres:
        by_country[genre["country"]].append(genre)
        for area in genre.get("associated_areas") or []:
            by_country[area["country"]].append(genre)
    rows = []
    for country in plan:
        visible = set(country["currently_visible_decades"])
        missing = period_groups(visible)
        docs = country["acquired_documents"]
        modern_names = sorted({genre["name"] for genre in by_country[country["code"]]
                               if genre.get("active_from") is not None and genre["active_from"] >= 1950})
        rows.append({
            "priority": priority(visible, len(docs)), "country": country["code"], "name": country["name"],
            "research_lane": country["research_lane"], "dossier_status": country["inventory_status"],
            "modern_visible_decades": ";".join(str(year) for year in sorted(visible & set(MODERN_DECADES))),
            "missing_modern_periods": ";".join(missing) or "none — verify evidence quality",
            "current_modern_genres": "; ".join(modern_names) or "none with documented 1950s-or-later onset",
            "acquired_source_ids": "; ".join(document["id"] for document in docs) or "none",
            "current_source_need": country["source_need"],
            "material_to_ingest": material_needed(missing, len(docs)),
            "research_action_after_ingestion": "Read exact local passages; log claim-level identity/place/period and representatives in the country dossier; only then compare resulting candidates with the catalogue.",
        })
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    rows.sort(key=lambda row: (order[row["priority"][:2]], row["research_lane"], row["country"]))
    out = RESEARCH / "modern_source_ingestion_queue.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    counts = Counter(row["priority"] for row in rows)
    no_modern = sum(not row["modern_visible_decades"] for row in rows)
    no_2000 = sum("2000–2009" in row["missing_modern_periods"] for row in rows)
    no_2020 = sum("2020–present" in row["missing_modern_periods"] for row in rows)
    no_documents = sum(row["acquired_source_ids"] == "none" for row in rows)
    summary = RESEARCH / "MODERN_SOURCE_INGESTION_GAP_REVISION.md"
    summary.write_text("\n".join([
        "# 1950s–present source-ingestion gap revision", "",
        "This revises the implementation-roadmap gap set. It measures documentation and review coverage, not whether a country had music in a decade. Visibility in the map remains a discovery indicator until a dossier records claim-level evidence.", "",
        "## Current queue", "",
        f"- {no_modern} mapped areas have no 1950s–present visible cell.",
        f"- {no_2000} lack a 2000s cell; {no_2020} lack a 2020s cell.",
        f"- {no_documents} have no acquired source bundle in the current plan.",
        f"- Priority distribution: {', '.join(f'{label}={count}' for label, count in sorted(counts.items()))}.", "",
        "## What must be ingested", "",
        "1. A postwar national or city-scene chronology for 1950s–1990s gaps, with the relevant chapter/article and local terminology.",
        "2. A 2000s–present scene source for every current-period gap: scholarly thesis/article where possible, plus broadcaster, label, festival, cultural-policy, or discography metadata for date and representative discovery.",
        "3. A community/minority or regional source where the national overview would flatten local practice, and a cross-border/migration source where applicable.",
        "4. A representative and media trail: named performers/ensembles connected by a source to the form, then authorized video and record metadata only after that relationship is reviewed.",
        "",
        "## Integration order", "",
        "Ingest source packets by priority; read and log the exact passages in country dossiers; derive candidates from the documented names, scenes, artists, labels and cities; compare them against existing shared families; then route distinct candidates to the catalog integrator. This replaces broad tag-first genre discovery for the modern gaps.", "",
        f"The country-level queue is [{out.name}]({out.name}). Regenerate it with `python3 scripts/{Path(__file__).name}` after each country-decade or source-intake update.",
    ]) + "\n", encoding="utf-8")
    print({"countries": len(rows), "no_modern": no_modern, "no_2000": no_2000, "no_2020": no_2020, "no_documents": no_documents, "priorities": dict(sorted(counts.items())), "csv": str(out), "summary": str(summary)})


if __name__ == "__main__":
    main()
