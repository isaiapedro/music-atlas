"""Normalize and rank unofficial RYM data without publishing scraped responses.

MusicBrainz remains the identity source. RYM contributes discovery and ranking
signals only. Input is a saved Parse get_charts/get_artist_details response;
this command deliberately makes no paid or authenticated network request.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / ".local/musicbrainz/catalog.sqlite3"
DEFAULT_OUT = ROOT / ".local/rym"


def norm(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def number(value, default=0):
    try:
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace(",", "")
        match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*([kKmMbB]?)", text)
        if not match:
            return default
        amount = float(match.group(1))
        multiplier = {"": 1, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000}[match.group(2).casefold()]
        return amount * multiplier
    except (TypeError, ValueError):
        return default


def parse_year(value):
    if isinstance(value, int) and 1900 <= value <= datetime.now().year + 1:
        return value
    match = re.search(r"\b(19\d{2}|20\d{2})\b", str(value or ""))
    return int(match.group(1)) if match else None


def parse_items(payload):
    """Accept common Parse response wrappers and return chart/release rows."""
    if isinstance(payload, list):
        return payload
    for key in ("items", "releases", "albums", "results"):
        if isinstance(payload.get(key), list):
            return payload[key]
    data = payload.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("discography"), list):
            return data["discography"]
        return parse_items(data)
    raise ValueError("No release list found in the saved provider response")


def artist_index(db, genre_id):
    rows = db.execute(
        """SELECT DISTINCT a.mbid,a.name,a.sort_name,ga.score
           FROM genre_artist ga JOIN artist a ON a.id=ga.artist_id
           WHERE ga.genre_id=?""", (genre_id,)
    )
    index = {}
    for mbid, name, sort_name, score in rows:
        for candidate in (name, sort_name):
            key = norm(candidate)
            if key and (key not in index or score > index[key]["tag_score"]):
                index[key] = {"mbid": mbid, "name": name, "tag_score": score}
    return index


def normalize_releases(payload, genre_id, db):
    artists = artist_index(db, genre_id)
    seen = set()
    normalized = []
    for raw in parse_items(payload):
        artist_name = raw.get("artist") or raw.get("artist_name") or raw.get("artistName") or ""
        release_name = raw.get("release_name") or raw.get("title") or raw.get("album") or ""
        release_url = raw.get("release_url") or raw.get("albumUrl") or raw.get("url") or ""
        identity = release_url or f"{norm(artist_name)}|{norm(release_name)}"
        if not release_name or identity in seen:
            continue
        seen.add(identity)
        artist = artists.get(norm(artist_name))
        genres = raw.get("genres") or raw.get("primary_genres") or []
        if isinstance(genres, str):
            genres = [genres]
        year = parse_year(raw.get("year") or raw.get("releaseYear") or raw.get("date") or raw.get("released"))
        normalized.append({
            "atlas_genre_id": genre_id,
            "provider": "rateyourmusic-via-parse",
            "rym_release_url": release_url,
            "rym_artist_url": raw.get("artist_url") or raw.get("artistUrl") or "",
            "title": release_name,
            "artist": artist_name,
            "musicbrainz_artist_mbid": artist["mbid"] if artist else None,
            "musicbrainz_artist_name": artist["name"] if artist else None,
            "artist_match": "exact_normalized" if artist else "unmatched",
            "musicbrainz_genre_tag_score": artist["tag_score"] if artist else None,
            "year": year,
            "decade": year // 10 * 10 if year else None,
            "average_rating": number(raw.get("average_rating", raw.get("averageRating", raw.get("rating"))), None),
            "rating_count": int(number(raw.get("rating_count", raw.get("ratingCount", raw.get("ratings_count"))), 0)),
            "review_count": int(number(raw.get("reviews_count", raw.get("reviewCount", raw.get("review_count"))), 0)),
            "primary_genres": raw.get("primary_genres") or raw.get("primaryGenres") or [],
            "genres": genres,
            "chart_rank": int(number(raw.get("rank"), 0)) or None,
            "collected_at": raw.get("fetched_at") or payload.get("fetched_at") if isinstance(payload, dict) else None,
        })
    return normalized


def percentile(values, fraction):
    values = sorted(values)
    if not values:
        return 0
    return values[round((len(values) - 1) * fraction)]


def rank_releases(rows, per_decade=9, hold_min_score=.62):
    rated = [r for r in rows if r["average_rating"] is not None and r["rating_count"] > 0]
    if not rated:
        return [], [], rows, {"genre_mean": None, "minimum_confidence": None}
    genre_mean = sum(r["average_rating"] * r["rating_count"] for r in rated) / sum(r["rating_count"] for r in rated)
    confidence = max(25, percentile([r["rating_count"] for r in rated], .25))
    max_ratings = max(r["rating_count"] for r in rated)
    max_reviews = max(r["review_count"] for r in rated) or 1
    for row in rows:
        rating, count = row["average_rating"], row["rating_count"]
        if rating is None or count <= 0:
            row.update({"bayesian_rating": None, "selection_score": 0.0})
            continue
        bayes = (count / (count + confidence)) * rating + (confidence / (count + confidence)) * genre_mean
        engagement = math.log1p(count) / math.log1p(max_ratings)
        reviews = math.log1p(row["review_count"]) / math.log1p(max_reviews)
        score = .70 * (bayes / 5) + .20 * engagement + .10 * reviews
        row.update({"bayesian_rating": round(bayes, 4), "selection_score": round(score, 6)})
    selected = []
    for decade in sorted({r["decade"] for r in rows if r["decade"] is not None}):
        candidates = [r for r in rows if r["decade"] == decade and r["artist_match"] != "unmatched"]
        selected.extend(sorted(candidates, key=lambda r: (-r["selection_score"], -r["rating_count"], r["title"]))[:per_decade])
    holds = sorted(
        [dict(r, hold_reason="high_scoring_release_without_reliable_year", review_status="pending")
         for r in rows if r["decade"] is None
         and r["selection_score"] >= hold_min_score
         and r["average_rating"] is not None
         and r["average_rating"] >= genre_mean
         and r["rating_count"] >= confidence
         and r["artist_match"] != "unmatched"],
        key=lambda r: -r["selection_score"],
    )
    selected_ids = {r["rym_release_url"] or (r["artist"], r["title"]) for r in selected}
    hold_ids = {r["rym_release_url"] or (r["artist"], r["title"]) for r in holds}
    remainder = [r for r in rows if (r["rym_release_url"] or (r["artist"], r["title"])) not in selected_ids | hold_ids]
    metadata = {"genre_mean": round(genre_mean, 4), "minimum_confidence": confidence}
    return selected, holds, remainder, metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Saved Parse JSON response")
    parser.add_argument("--genre-id", required=True)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--per-decade", type=int, default=9)
    parser.add_argument("--hold-min-score", type=float, default=.62)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    with sqlite3.connect(args.db) as db:
        rows = normalize_releases(payload, args.genre_id, db)
    selected, holds, remainder, scoring = rank_releases(rows, args.per_decade, args.hold_min_score)
    generated = datetime.now(timezone.utc).isoformat()
    output = {"generated_at": generated, "status": "private_review_candidates", "atlas_genre_id": args.genre_id,
              "source": "unofficial RYM data supplied as a saved Parse response", "scoring": scoring,
              "selected_by_decade": selected, "undated_hold": holds, "not_selected": remainder}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    target = args.output_dir / f"{args.genre_id}.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"normalized": len(rows), "selected": len(selected), "undated_hold": len(holds),
                      "unmatched_artists": sum(r["artist_match"] == "unmatched" for r in rows), "output": str(target)}, indent=2))


if __name__ == "__main__":
    main()
