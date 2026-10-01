"""Build a review queue for Atlas genres without exact MusicBrainz tag matches.

Names from Wikidata are discovery metadata. Fuzzy similarity never publishes or
associates a genre automatically; every result is emitted for editorial review.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import math
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / ".local/musicbrainz/catalog.sqlite3"
TAG_TABLE = ROOT / ".local/musicbrainz/dumps/mbdump-derived.tar.bz2.tables/tag"
WIKIDATA = ROOT / ".local/musicbrainz/wikidata_genre_entities.json"
MAPPINGS = ROOT / "research/musicbrainz_genre_mappings.json"
OUT = ROOT / ".local/musicbrainz/unmatched_genre_review.json"
REPORT = ROOT / ".local/musicbrainz/unmatched_genre_review.md"
CSV_OUT = ROOT / ".local/musicbrainz/unmatched_genre_review.csv"
BEST_OUT = ROOT / ".local/musicbrainz/best_genre_comparisons.csv"


def norm(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def token_score(left, right):
    a, b = set(left.split()), set(right.split())
    if not a or not b:
        return 0.0
    return 2 * len(a & b) / (len(a) + len(b))


def similarity(left, right):
    if left == right:
        return 1.0
    sequence = difflib.SequenceMatcher(None, left, right).ratio()
    tokens = token_score(left, right)
    containment = min(len(left), len(right)) / max(len(left), len(right)) if left in right or right in left else 0
    return max(sequence, tokens * 0.97, containment * 0.9)


def grams(value):
    compact = value.replace(" ", "_")
    return {compact[i:i + 3] for i in range(max(1, len(compact) - 2))}


def generated_variants(name):
    """Conservative search forms, clearly distinguished from sourced aliases."""
    values = []
    suffixes = (" songs", " song", " music", " dance", " tradition", " musical tradition", " style")
    n = norm(name)
    for suffix in suffixes:
        if n.endswith(suffix) and len(n) > len(suffix) + 2:
            values.append(n[:-len(suffix)].strip())
    values.extend((n.replace(" and ", " & "), n.replace(" & ", " and ")))
    return sorted({v for v in values if v and v != n})


def load_tags():
    tags = []
    with TAG_TABLE.open(encoding="utf-8") as stream:
        for line in stream:
            row = line.rstrip("\n").split("\t")
            tags.append({"id": int(row[0]), "name": row[1], "normalized": norm(row[1]),
                         "ref_count": 0 if row[2] == r"\N" else int(row[2])})
    return tags


def wikidata_names(entity):
    names = []
    if not entity:
        return names
    for language, value in entity.get("labels", {}).items():
        names.append((value["value"], language, "wikidata_label"))
    for language, aliases in entity.get("aliases", {}).items():
        names.extend((value["value"], language, "wikidata_alias") for value in aliases)
    return names


def claim_values(entity, property_id):
    values = []
    for claim in (entity or {}).get("claims", {}).get(property_id, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, str):
            values.append(value)
    return sorted(set(values))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB)
    parser.add_argument("--wikidata", type=Path, default=WIKIDATA)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--csv", type=Path, default=CSV_OUT)
    parser.add_argument("--best-csv", type=Path, default=BEST_OUT)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--threshold", type=float, default=0.58)
    args = parser.parse_args()
    catalogue = json.loads((ROOT / "research/genre_catalogue.json").read_text(encoding="utf-8"))
    articles = json.loads((ROOT / "research/wiki_articles.json").read_text(encoding="utf-8"))["genres"]
    entities = json.loads(args.wikidata.read_text(encoding="utf-8")) if args.wikidata.exists() else {"entities": {}}
    entities = entities.get("entities", entities)
    mapping_payload = json.loads(MAPPINGS.read_text(encoding="utf-8"))
    approved = {atlas_id: mapping for mapping in mapping_payload["mappings"] for atlas_id in mapping["atlas_ids"]}
    db = sqlite3.connect(args.db)
    matched = {r[0] for r in db.execute("SELECT id FROM atlas_genre WHERE tag_id IS NOT NULL")}
    tags = load_tags()
    gram_index = defaultdict(set)
    tag_name_index = defaultdict(set)
    for index, tag in enumerate(tags):
        tag_name_index[tag["normalized"]].add(index)
        for gram in grams(tag["normalized"]):
            gram_index[gram].add(index)
    output = {"generated_at": date.today().isoformat(), "status": "editorial_review_required",
              "method": {"auto_association": False, "threshold": args.threshold, "candidate_limit": args.limit,
                         "warning": "Similarity and Wikidata aliases are discovery signals, not genre identity evidence."},
              "summary": {}, "genres": []}
    source_counts = defaultdict(int)
    for genre in catalogue["entries"]:
        if genre["status"] != "published" or genre["id"] in matched:
            continue
        article = articles.get(genre["id"]) or {}
        qid = (article.get("wikidata_url") or "").rsplit("/", 1)[-1] or None
        raw_names = [(genre["name"], "en", "atlas_name")]
        for value in (genre.get("wikipedia_title"), article.get("title")):
            if value:
                raw_names.append((value, "en", "reviewed_article_title"))
        entity = entities.get(qid)
        raw_names.extend(wikidata_names(entity))
        raw_names.extend((value, None, "generated_search_form") for value in generated_variants(genre["name"]))
        dedup = {}
        for value, language, source in raw_names:
            key = norm(value)
            if not key:
                continue
            current = dedup.get((key, language))
            if current is None or current[2] == "generated_search_form":
                dedup[(key, language)] = (value, language, source)
        names = list(dedup.values())
        for _, _, source in names:
            source_counts[source] += 1
        possible = set()
        fuzzy_names = [row for row in names if row[1] == "en" or row[2] != "wikidata_label" and row[2] != "wikidata_alias"]
        exact_names = defaultdict(list)
        for row in names:
            exact_names[norm(row[0])].append(row)
        for value, _, _ in fuzzy_names:
            normalized = norm(value)
            name_grams = grams(normalized)
            overlaps = Counter(index for gram in name_grams for index in gram_index[gram])
            minimum = max(1, math.ceil(len(name_grams) * 0.35))
            possible.update(index for index, count in overlaps.items() if count >= minimum)
        for value, _, _ in names:
            possible.update(tag_name_index[norm(value)])
        candidates = {}
        for tag_index in possible:
            tag = tags[tag_index]
            best = None
            comparison_names = fuzzy_names + exact_names.get(tag["normalized"], [])
            for value, language, source in comparison_names:
                score = similarity(norm(value), tag["normalized"])
                if score < args.threshold or (min(len(norm(value)), len(tag["normalized"])) < 4 and score < 1):
                    continue
                rank = (score, math.log10(tag["ref_count"] + 1) / 20)
                if best is None or rank > best[0]:
                    best = (rank, value, language, source)
            if best:
                candidates[tag["id"]] = {"musicbrainz_tag_id": tag["id"], "musicbrainz_tag": tag["name"],
                    "tag_ref_count": tag["ref_count"], "similarity": round(best[0][0], 4),
                    "matched_name": best[1], "matched_language": best[2], "name_source": best[3],
                    "match_type": "alternate_name_exact" if best[0][0] == 1 else "fuzzy",
                    "decision": "pending", "review_note": ""}
        ranked = sorted(candidates.values(), key=lambda x: (x["similarity"], math.log10(x["tag_ref_count"] + 1)), reverse=True)[:args.limit]
        mapping = approved.get(genre["id"])
        if mapping:
            accepted = {norm(value) for value in mapping["accepted_names"]}
            approved_rows = []
            for candidate in ranked:
                if norm(candidate["musicbrainz_tag"]) in accepted:
                    candidate["decision"] = "approve"
                    candidate["review_note"] = "Explicitly approved canonical/alternate mapping."
                    approved_rows.append(candidate)
            if not approved_rows:
                ranked.insert(0, {"musicbrainz_tag_id": None, "musicbrainz_tag": mapping["canonical_name"],
                    "tag_ref_count": 0, "similarity": 1.0, "matched_name": mapping["canonical_name"],
                    "matched_language": None, "name_source": "editorial_mapping",
                    "match_type": "editorial_approved_canonical", "decision": "approve",
                    "review_note": mapping.get("qualification", "Explicitly approved canonical mapping; no exact dump tag exists.")})
            ranked.sort(key=lambda row: (row["decision"] == "approve", row["similarity"], math.log10(row["tag_ref_count"] + 1)), reverse=True)
            ranked = ranked[:args.limit]
        output["genres"].append({"atlas_id": genre["id"], "country": genre["country"], "atlas_name": genre["name"],
            "wikidata_id": qid, "wikidata_url": article.get("wikidata_url"),
            "identifiers": {"musicbrainz_genre_mbids": claim_values(entity, "P8052"),
                            "unesco_ich_ids": claim_values(entity, "P4431")},
            "approved_mapping": mapping,
            "names": [{"value": n, "language": lang, "source": source} for n, lang, source in sorted(names, key=lambda x: (x[2], x[1] or "", x[0]))],
            "candidates": ranked, "genre_decision": "pending", "genre_review_note": ""})
    output["summary"] = {"unmatched_genres": len(output["genres"]),
                         "with_wikidata_entity": sum(bool(g["wikidata_id"] and g["wikidata_id"] in entities) for g in output["genres"]),
                         "with_candidates": sum(bool(g["candidates"]) for g in output["genres"]),
                         "without_candidates": sum(not g["candidates"] for g in output["genres"]),
                         "name_source_counts": dict(sorted(source_counts.items()))}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = ["# Unmatched Atlas genre → MusicBrainz review queue", "",
              f"Generated {output['generated_at']}. No candidate is approved automatically.", "",
              f"- Unmatched genres: {output['summary']['unmatched_genres']}",
              f"- Genres with candidates: {output['summary']['with_candidates']}",
              f"- Genres without candidates: {output['summary']['without_candidates']}", ""]
    for genre in output["genres"]:
        report.extend((f"## {genre['country']} — {genre['atlas_name']}", "",
                       f"Atlas ID: `{genre['atlas_id']}` · Wikidata: {genre['wikidata_id'] or 'none'} · Decision: **pending**", ""))
        mbids = genre["identifiers"]["musicbrainz_genre_mbids"]
        if mbids:
            report.append("MusicBrainz genre MBID(s): " + ", ".join(f"`{value}`" for value in mbids)); report.append("")
        sourced = [n for n in genre["names"] if n["source"] != "generated_search_form"]
        report.append("Names: " + "; ".join(f"{n['value']} [{n['language'] or 'und'}, {n['source']}]" for n in sourced[:30]))
        if len(sourced) > 30:
            report.append(f"\n_…and {len(sourced)-30} additional multilingual names in the JSON queue._")
        report.extend(("", "| Candidate tag | Similarity | Tag uses | Matched name/source | Decision |",
                       "|---|---:|---:|---|---|"))
        for candidate in genre["candidates"]:
            report.append(f"| {candidate['musicbrainz_tag']} | {candidate['similarity']:.2f} | {candidate['tag_ref_count']} | {candidate['matched_name']} / {candidate['name_source']} | pending |")
        if not genre["candidates"]:
            report.append("| _No candidate above threshold_ |  |  |  | pending research |")
        report.append("")
    args.report.write_text("\n".join(report) + "\n", encoding="utf-8")
    with args.csv.open("w", encoding="utf-8", newline="") as stream:
        fields = ("country","atlas_id","atlas_name","wikidata_id","musicbrainz_genre_mbids",
                  "candidate_tag","similarity","tag_ref_count","matched_name","matched_language",
                  "name_source","match_type","decision","review_note")
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for genre in output["genres"]:
            blank = {key:"" for key in ("musicbrainz_tag","similarity","tag_ref_count","matched_name",
                                          "matched_language","name_source","match_type","review_note")}
            blank["decision"] = "pending"
            for candidate in genre["candidates"] or [blank]:
                writer.writerow({"country":genre["country"],"atlas_id":genre["atlas_id"],"atlas_name":genre["atlas_name"],
                    "wikidata_id":genre["wikidata_id"] or "","musicbrainz_genre_mbids":"|".join(genre["identifiers"]["musicbrainz_genre_mbids"]),
                    "candidate_tag":candidate["musicbrainz_tag"],"similarity":candidate["similarity"],
                    "tag_ref_count":candidate["tag_ref_count"],"matched_name":candidate["matched_name"],
                    "matched_language":candidate["matched_language"] or "","name_source":candidate["name_source"],
                    "match_type":candidate["match_type"],"decision":candidate["decision"],"review_note":candidate["review_note"]})
    with args.best_csv.open("w", encoding="utf-8", newline="") as stream:
        fields = ("country","atlas_id","atlas_genre","comparative_musicbrainz_genre","similarity",
                  "tag_ref_count","matched_name","name_source","match_type","musicbrainz_genre_mbids","status")
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for genre in output["genres"]:
            best = genre["candidates"][0] if genre["candidates"] else None
            writer.writerow({"country":genre["country"],"atlas_id":genre["atlas_id"],"atlas_genre":genre["atlas_name"],
                "comparative_musicbrainz_genre":best["musicbrainz_tag"] if best else "",
                "similarity":best["similarity"] if best else "","tag_ref_count":best["tag_ref_count"] if best else "",
                "matched_name":best["matched_name"] if best else "","name_source":best["name_source"] if best else "",
                "match_type":best["match_type"] if best else "",
                "musicbrainz_genre_mbids":"|".join(genre["identifiers"]["musicbrainz_genre_mbids"]),
                "status":"approved" if best and best["decision"] == "approve" else ("pending validation" if best else "no candidate above threshold")})
    print(json.dumps(output["summary"], indent=2))
    print(f"wrote review queue to {args.out}")
    print(f"wrote human review report to {args.report}")
    print(f"wrote editable validation sheet to {args.csv}")
    print(f"wrote one-row-per-genre comparison list to {args.best_csv}")


if __name__ == "__main__":
    main()
