"""Audit persistent country research without mistaking candidates for coverage.

Run from the project root: python3 scripts/research_progress.py
Use --json for a machine-readable queue and progress report.
"""

import argparse
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
DATA = ROOT / "web" / "data"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit():
    mapped = {item["properties"]["code"]: item["properties"]["name"]
              for item in read(DATA / "countries.geojson")["features"]}
    inventory = read(RESEARCH / "country_inventory.json")["countries"]
    catalogue = read(RESEARCH / "genre_catalogue.json")["entries"]
    pilots = read(RESEARCH / "pilot_candidates.json")["candidates"]
    discovery_path = RESEARCH / "unesco_candidates.json"
    discovery = read(discovery_path).get("candidates", []) if discovery_path.exists() else []
    wikidata_path = RESEARCH / "wikidata_candidates.json"
    wikidata = read(wikidata_path).get("candidates", []) if wikidata_path.exists() else []
    acquired_index = ROOT / ".local" / "acquired_sources" / "index.json"
    acquired_ids = {item["id"] for item in read(acquired_index)["documents"]} if acquired_index.exists() else set()
    rows = {row["code"]: row for row in inventory}
    assert len(rows) == len(inventory), "duplicate inventory country"
    assert set(rows) == set(mapped), "inventory and map country codes differ"
    assert all(row["status"] in {"unreviewed", "starter_only", "reviewed"} for row in inventory)
    ids = [item["id"] for item in catalogue] + [item["id"] for item in pilots]
    assert len(ids) == len(set(ids)), "duplicate candidate/catalogue ID"
    assert all(item["country"] in mapped for item in catalogue + pilots)
    assert all(item["country"] in mapped and item.get("review_status") == "unreviewed" for item in discovery), "automated lead asserted review or unmapped country"
    assert all(item["country"] in mapped and item.get("review_status") == "unreviewed" for item in wikidata), "Wikidata lead asserted review or unmapped country"
    published = Counter(item["country"] for item in catalogue if item["status"] == "published")
    candidate_pairs = {(item["country"], item["name"].casefold()) for item in catalogue if item["status"] != "published"}
    candidate_pairs.update((item["country"], item["name"].casefold()) for item in pilots)
    dossier_dir = RESEARCH / "countries"
    dossiers = {}
    multi_domain = set()
    period_audited = set()
    for path in sorted(dossier_dir.glob("*.json")) if dossier_dir.exists() else []:
        dossier = read(path)
        code = dossier["code"]
        assert code in mapped and path.stem == code, f"invalid dossier: {path}"
        assert code not in dossiers, f"duplicate dossier: {code}"
        assert dossier.get("coverage_note") and dossier.get("gaps"), f"dossier lacks coverage limits: {code}"
        for candidate in dossier.get("candidates", []):
            assert candidate.get("publication_status") in {"candidate", "reviewed", "published"}, f"invalid candidate status: {code}"
            assert candidate.get("sources") and all(
                source.get("url", "").startswith("https://") or
                (source.get("citation") and (source.get("supports") or source.get("claim"))) or
                (source.get("acquired_document_id") in acquired_ids and
                 (source.get("page") or source.get("section")) and
                 (source.get("supports") or source.get("claim")))
                for source in candidate["sources"]), f"candidate lacks traceable source: {code}"
            if candidate["publication_status"] != "published":
                candidate_pairs.add((code, candidate["name"].casefold()))
        domains = {urlparse(source["url"]).hostname for candidate in dossier.get("candidates", [])
                   for source in candidate.get("sources", []) if source.get("url")}
        if len(domains) >= 2:
            multi_domain.add(code)
        if dossier.get("periods") and all(period.get("status") in {"reviewed", "evidence_unavailable"}
                                           for period in dossier["periods"]):
            period_audited.add(code)
        dossiers[code] = dossier
    assert all(item["country"] in dossiers for item in pilots), "pilot candidate lacks country dossier"
    published_ids = {item["id"] for item in catalogue if item["status"] == "published"}
    for item in catalogue:
        if item["status"] != "published":
            continue
        candidates = dossiers[item["country"]].get("candidates", [])
        assert any((candidate["id"] == item["id"] or candidate.get("publication_id") == item["id"])
                   and candidate.get("publication_status") == "published" for candidate in candidates), \
            f"published layer lacks matching reviewed dossier candidate: {item['id']}"
    for code, dossier in dossiers.items():
        for candidate in dossier.get("candidates", []):
            if candidate.get("publication_status") == "published":
                assert candidate.get("publication_id", candidate["id"]) in published_ids, \
                    f"dossier claims unpublished layer is live: {code}/{candidate['id']}"
    candidates = Counter(code for code, _ in candidate_pairs)
    automated = Counter(item["country"] for item in discovery)
    wikidata_counts = Counter(item["country"] for item in wikidata)
    assert all(rows[code]["status"] != "reviewed" or code in dossiers for code in rows), "reviewed country lacks dossier"
    countries = []
    for code in sorted(mapped):
        status = rows[code]["status"]
        countries.append({"code": code, "name": mapped[code], "status": status,
                          "has_dossier": code in dossiers, "multiple_source_domains": code in multi_domain,
                          "period_audited": code in period_audited, "published_genres": published[code],
                          "candidate_leads": candidates[code], "unesco_leads": automated[code],
                          "wikidata_leads": wikidata_counts[code],
                          "gaps": rows[code].get("gaps", [])})
    return {"mapped_countries": len(mapped), "national_overviews_reviewed": sum(row["status"] == "reviewed" for row in inventory),
            "countries_with_dossiers": len(dossiers), "countries_with_published_genres": sum(bool(count) for count in published.values()),
            "countries_with_three_or_more_genres": sum(count >= 3 for count in published.values()),
            "dossiers_with_multiple_source_domains": len(multi_domain),
            "dossiers_with_period_audit": len(period_audited),
            "countries_with_candidate_leads": sum(bool(count) for count in candidates.values()),
            "countries_with_unesco_leads": sum(bool(count) for count in automated.values()),
            "countries_with_wikidata_leads": sum(bool(count) for count in wikidata_counts.values()),
            "published_genres": sum(published.values()),
            "published_genres_with_dated_start": sum(item["status"] == "published" and item["active_from"] is not None for item in catalogue),
            "unpublished_candidate_leads": sum(candidates.values()),
            "unesco_unreviewed_leads": sum(automated.values()),
            "wikidata_unreviewed_leads": sum(wikidata_counts.values()),
            "countries": countries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="include every country in JSON")
    args = parser.parse_args()
    result = audit()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for key in ("mapped_countries", "national_overviews_reviewed", "countries_with_dossiers",
                    "dossiers_with_multiple_source_domains", "dossiers_with_period_audit", "countries_with_candidate_leads",
                    "countries_with_unesco_leads", "countries_with_wikidata_leads", "countries_with_published_genres", "countries_with_three_or_more_genres",
                    "published_genres", "published_genres_with_dated_start", "unpublished_candidate_leads", "unesco_unreviewed_leads",
                    "wikidata_unreviewed_leads"):
            print(f"{key.replace('_', ' ')}: {result[key]}")
        untouched = [row["code"] for row in result["countries"] if not row["has_dossier"] and not row["candidate_leads"] and not row["published_genres"]]
        print("countries without dossier or candidate: " + (", ".join(untouched) if untouched else "none"))


if __name__ == "__main__":
    main()
