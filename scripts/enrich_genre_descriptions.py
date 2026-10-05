"""Draft source-backed genre descriptions; publish only explicitly reviewed drafts.

Usage:
  python3 scripts/enrich_genre_descriptions.py --queue /tmp/genre_descriptions.json
  python3 scripts/enrich_genre_descriptions.py --apply /tmp/reviewed_descriptions.json

The review file is a copy of the queue with ``reviewed: true`` set on approved
items. Editors may revise ``description`` before approval. The script never
turns an unreviewed dossier claim into public prose automatically.
"""
import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
CATALOGUE = RESEARCH / "genre_catalogue.json"
ARTICLE_CATALOGUE = RESEARCH / "wiki_articles.json"
GENERIC_PREFIXES = (
    "Country-wide fill is a coarse association.",
    "The source identifies a country association but not a defensible subnational mapping.",
)


def write_json(path, value):
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=f".{path.name}.", delete=False) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    temporary.replace(path)


def clean(value):
    return " ".join((value or "").split())


def is_generic(value):
    value = clean(value)
    return not value or value.startswith((
        "Country scope is deliberately", "The source identifies", "Country-wide fill",
        "No ", "Dates describe", "Source-backed", "Mapped association:",
    ))


def catalogue_target(entry):
    return entry.get("status") == "published" and entry.get("note", "").startswith(GENERIC_PREFIXES)


def dossier_index():
    result = {}
    for path in sorted((RESEARCH / "countries").glob("*.json")):
        dossier = json.loads(path.read_text(encoding="utf-8"))
        for candidate in dossier.get("candidates", []):
            if candidate.get("publication_status") == "published":
                result[candidate.get("publication_id", candidate.get("id"))] = (candidate, path)
    return result


def proposed_description(candidate):
    geography = clean(candidate.get("geographic_relationship", {}).get("description"))
    if len(geography) >= 65 and not is_generic(geography):
        return geography
    return ""


def source_refs(candidate):
    refs = []
    for source in candidate.get("sources", []):
        document = source.get("acquired_document_id") or source.get("url") or source.get("citation")
        locator = source.get("page") or source.get("section")
        claim = clean(source.get("claim") or source.get("supports"))
        if document and locator and claim:
            refs.append({"document": document, "locator": locator, "claim": claim})
    return refs


def wikipedia_draft(entry, articles):
    article = articles.get(entry["id"])
    if not article or not entry.get("wikipedia_title"):
        return None
    if (article.get("requested_title") or article.get("title")) != entry["wikipedia_title"]:
        return None
    extract = clean(article.get("extract"))
    if not extract or not article.get("revision_id") or not article.get("url"):
        return None
    # A short excerpt is a research prompt, never an automatically published note.
    words = extract.split()
    draft = " ".join(words[:20]).rstrip(",;:")
    if len(words) > 20:
        draft += "…"
    revision_url = article["url"].split("#", 1)[0] + "?oldid=" + quote(str(article["revision_id"]))
    return {"draft_excerpt": draft, "article_title": article["title"],
            "article_url": article["url"], "revision_url": revision_url,
            "license": article.get("license"), "license_url": article.get("license_url"),
            "attribution": f"Wikipedia contributors, {article['title']}, revision {article['revision_id']}"}


def fingerprint(entry, candidate):
    material = {"id": entry["id"], "note": entry.get("note"), "candidate": candidate}
    return hashlib.sha256(json.dumps(material, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def build_queue(entries, dossiers, articles=None):
    articles = articles or {}
    rows = []
    for entry in entries:
        if not catalogue_target(entry):
            continue
        candidate, path = dossiers.get(entry["id"], ({}, None))
        refs = source_refs(candidate)
        description = proposed_description(candidate) if refs else ""
        wiki = wikipedia_draft(entry, articles)
        rows.append({
            "id": entry["id"], "name": entry["name"],
            "status": "ready_for_review" if description else ("wikipedia_review" if wiki else "needs_research"),
            "description": description, "reviewed": False,
            "source_refs": refs,
            "wikipedia": wiki,
            "dossier": str(path.relative_to(ROOT)) if path else None,
            "fingerprint": fingerprint(entry, candidate),
        })
    return rows


def apply_reviews(entries, dossiers, reviews):
    by_id = {entry["id"]: entry for entry in entries}
    changed = 0
    for row in reviews:
        if row.get("reviewed") is not True:
            continue
        entry = by_id.get(row.get("id"))
        if not entry or not catalogue_target(entry):
            raise ValueError(f"stale or unknown catalogue target: {row.get('id')}")
        candidate, _ = dossiers.get(entry["id"], ({}, None))
        if row.get("fingerprint") != fingerprint(entry, candidate):
            raise ValueError(f"source changed; regenerate review queue: {entry['id']}")
        refs = source_refs(candidate)
        saved_articles = json.loads(ARTICLE_CATALOGUE.read_text(encoding="utf-8")).get("genres", {}) if ARTICLE_CATALOGUE.exists() else {}
        wiki = wikipedia_draft(entry, saved_articles)
        if not refs and not wiki:
            raise ValueError(f"no page-cited source or exact saved Wikipedia article: {entry['id']}")
        description = clean(row.get("description"))
        if len(description) < 60 or is_generic(description):
            raise ValueError(f"description too short or generic: {entry['id']}")
        entry["note"] = description
        entry.setdefault("research", {})["description_audit"] = {
            "status": "source_checked", "source_refs": refs,
            "wikipedia_attribution": wiki if wiki else None,
        }
        changed += 1
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--queue", type=Path, help="write drafts and source evidence for review")
    group.add_argument("--apply", type=Path, help="apply explicitly reviewed descriptions")
    args = parser.parse_args()
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    dossiers = dossier_index()
    if args.queue:
        articles = json.loads(ARTICLE_CATALOGUE.read_text(encoding="utf-8")).get("genres", {}) if ARTICLE_CATALOGUE.exists() else {}
        rows = build_queue(data["entries"], dossiers, articles)
        write_json(args.queue, rows)
        ready = sum(row["status"] == "ready_for_review" for row in rows)
        wiki = sum(row["wikipedia"] is not None for row in rows)
        print(f"queued {len(rows)} generic published genres; {ready} have page-cited dossier drafts; {wiki} have exact saved Wikipedia leads")
    else:
        from mvp_locks import locked_genre_ids
        reviews = json.loads(args.apply.read_text(encoding="utf-8"))
        locked = locked_genre_ids()
        if isinstance(reviews, list):
            before = len(reviews)
            reviews = [row for row in reviews if row.get("id") not in locked]
            skipped = before - len(reviews)
        else:
            skipped = 0
        changed = apply_reviews(data["entries"], dossiers, reviews)
        if changed:
            write_json(CATALOGUE, data)
        print(f"applied {changed} reviewed genre descriptions")
        if skipped:
            print(f"skipped {skipped} MVP-locked genre rows; see research/mvp_country_locks.json")


if __name__ == "__main__":
    main()
