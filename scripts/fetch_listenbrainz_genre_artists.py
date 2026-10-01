"""Rank strongly genre-associated MusicBrainz artists with ListenBrainz popularity.

This is discovery data, not proof that an artist represents a genre. Raw
ListenBrainz totals and MusicBrainz genre-tag evidence are retained separately.
Only repeated direct artist tags or exact Atlas representative matches are eligible.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / ".local/musicbrainz/catalog.sqlite3"
DEFAULT_CATALOGUE = ROOT / "research/genre_catalogue.json"
DEFAULT_OUT = ROOT / ".local/listenbrainz/genre_artist_popularity.json"
API = "https://api.listenbrainz.org/1/popularity/artist"
USER_AGENT = "MusicAtlas/0.1 (genre-artist discovery; ListenBrainz API client)"
GENERIC_REPRESENTATIVE = re.compile(
    r"\b(performers?|practitioners?|communities|community singers|singers|dancers|drummers|"
    r"musicians|players|puppeteers|bearers|villagers|vocalists?|poets?|masters?[- ]disciple|traditions?)\b", re.I
)


def norm(value: str) -> str:
    import unicodedata
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def load_artists(db_path: Path) -> list[dict]:
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    rows = db.execute("""
        SELECT g.id AS genre_id, g.name AS genre, g.country,
               a.mbid AS artist_mbid, a.name AS artist,
               MAX(ga.score) AS genre_tag_score,
               MAX(CASE WHEN ga.basis = 'artist tag' THEN ga.score END) AS artist_tag_score,
               GROUP_CONCAT(DISTINCT ga.basis) AS genre_tag_basis
        FROM genre_artist ga
        JOIN atlas_genre g ON g.id = ga.genre_id
        JOIN artist a ON a.id = ga.artist_id
        WHERE a.mbid IS NOT NULL AND a.mbid != ''
          AND lower(trim(a.name)) != 'various artists'
        GROUP BY g.id, a.id
        ORDER BY g.name, a.name
    """).fetchall()
    db.close()
    return [dict(row) for row in rows]


def load_musicbrainz_covered_genre_ids(db_path: Path) -> set[str]:
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    ids = {row[0] for row in db.execute("SELECT id FROM atlas_genre WHERE tag_id IS NOT NULL")}
    db.close()
    return ids


def app_representatives(db_path: Path, catalogue_path: Path, covered_genre_ids: set[str]) -> tuple[list[dict], list[dict]]:
    """Resolve app-listed representatives for genres without a matched MB tag.

    Exact normalized-name matches in the local MusicBrainz dump are accepted as
    identifiers only when unique. Generic role/community labels stay as manual
    name searches and are never sent as if they were individual artists.
    """
    catalogue = json.loads(catalogue_path.read_text(encoding="utf-8"))
    missing = [g for g in catalogue["entries"]
               if g.get("status") == "published" and g["id"] not in covered_genre_ids]
    names = {norm(name) for genre in missing for name in genre.get("artists", []) if name}
    matches: dict[str, set[tuple[str, str]]] = defaultdict(set)
    artist_table = db_path.parent / "dumps/mbdump.tar.bz2.tables/artist"
    if artist_table.exists() and names:
        with artist_table.open(encoding="utf-8") as stream:
            for line in stream:
                cells = line.rstrip("\n").split("\t")
                if len(cells) > 2 and cells[1] and norm(cells[2]) in names:
                    matches[norm(cells[2])].add((cells[1], cells[2]))
    else:
        db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        for mbid, name in db.execute("SELECT mbid,name FROM artist WHERE mbid IS NOT NULL"):
            if name and norm(name) in names:
                matches[norm(name)].add((mbid, name))
        db.close()

    resolved, unresolved = [], []
    for genre in missing:
        for name in dict.fromkeys(genre.get("artists", [])):
            if not name:
                continue
            row = {
                "genre_id": genre["id"], "genre": genre["name"], "country": genre["country"],
                "artist": name, "artist_mbid": None, "genre_tag_score": None,
                "artist_tag_score": None,
                "genre_tag_basis": "Atlas app representative", "artist_source": "Atlas representative",
                "listenbrainz_listens": None, "listenbrainz_listeners": None,
            }
            if GENERIC_REPRESENTATIVE.search(name):
                row["artist_match_status"] = "generic representative; manual name search only"
                unresolved.append(row)
                continue
            candidates = matches.get(norm(name), set())
            if len(candidates) == 1:
                mbid, canonical_name = next(iter(candidates))
                row.update(artist=canonical_name, artist_mbid=mbid,
                           artist_match_status="unique exact MusicBrainz name match")
                resolved.append(row)
            else:
                row["artist_match_status"] = (
                    "ambiguous exact MusicBrainz name" if candidates else "no exact MusicBrainz name match"
                )
                unresolved.append(row)
    return resolved, unresolved


def fetch_batch(mbids: list[str], timeout: int = 30) -> list[dict]:
    request = urllib.request.Request(
        API,
        data=json.dumps({"artist_mbids": mbids}).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    if not isinstance(payload, list):
        raise ValueError("ListenBrainz popularity endpoint returned a non-list response")
    return payload


def collect(db_path: Path, output: Path, batch_size: int = 100, delay: float = 1.1,
            catalogue_path: Path = DEFAULT_CATALOGUE, per_genre: int = 20,
            min_artist_tag_score: int = 2) -> dict:
    if not 1 <= batch_size <= 100:
        raise ValueError("batch_size must be between 1 and 100")
    if not 1 <= per_genre <= 20:
        raise ValueError("per_genre must be between 1 and 20")
    if min_artist_tag_score < 1:
        raise ValueError("min_artist_tag_score must be at least 1")
    artists = load_artists(db_path)
    covered_genre_ids = load_musicbrainz_covered_genre_ids(db_path)
    representatives, unresolved = app_representatives(db_path, catalogue_path, covered_genre_ids)
    known_keys = {(row["genre_id"], row["artist_mbid"]) for row in artists}
    for row in representatives:
        if (row["genre_id"], row["artist_mbid"]) not in known_keys:
            artists.append(row)
            known_keys.add((row["genre_id"], row["artist_mbid"]))
    by_mbid = {row["artist_mbid"]: row for row in artists}
    by_mbid.pop(None, None)
    popularity: dict[str, dict] = {}
    cache_path = output.with_suffix(".cache.json")
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            popularity.update({k: v for k, v in cached.items() if k in by_mbid})
        except (OSError, json.JSONDecodeError):
            pass

    missing = [mbid for mbid in by_mbid if mbid not in popularity]
    for offset in range(0, len(missing), batch_size):
        batch = missing[offset:offset + batch_size]
        results = fetch_batch(batch)
        for result in results:
            mbid = result.get("artist_mbid")
            if mbid in batch:
                popularity[mbid] = {
                    "total_listen_count": result.get("total_listen_count"),
                    "total_user_count": result.get("total_user_count"),
                }
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(popularity, ensure_ascii=False), encoding="utf-8")
        print(f"queried {min(offset + len(batch), len(missing))}/{len(missing)} artists", flush=True)
        if offset + batch_size < len(missing) and delay > 0:
            time.sleep(delay)

    groups: dict[str, list[dict]] = defaultdict(list)
    for row in artists:
        metrics = popularity.get(row["artist_mbid"], {})
        groups[row["genre_id"]].append({
            **row,
            "listenbrainz_listens": metrics.get("total_listen_count"),
            "listenbrainz_listeners": metrics.get("total_user_count"),
        })
    for rows in groups.values():
        rows.sort(key=lambda x: (
            x["listenbrainz_listens"] is not None,
            x["listenbrainz_listens"] or 0,
            x["listenbrainz_listeners"] or 0,
            x["genre_tag_score"] or 0,
        ), reverse=True)

    app_catalogue = json.loads(catalogue_path.read_text(encoding="utf-8"))
    published = [g for g in app_catalogue["entries"] if g.get("status") == "published"]
    unresolved_by_genre: dict[str, list[dict]] = defaultdict(list)
    for row in unresolved:
        unresolved_by_genre[row["genre_id"]].append(row)
    def is_qualified(row: dict) -> bool:
        return (
            (row.get("artist_tag_score") or 0) >= min_artist_tag_score
            or row.get("artist_match_status") == "unique exact MusicBrainz name match"
        )

    genre_details = []
    for app_genre in sorted(published, key=lambda g: g["name"].casefold()):
        genre_id = app_genre["id"]
        rows = groups.get(genre_id, [])
        rows.extend(unresolved_by_genre.get(genre_id, []))
        rows.sort(key=lambda x: (
            x["listenbrainz_listens"] is not None,
            x["listenbrainz_listens"] or 0,
            x["listenbrainz_listeners"] or 0,
            x["genre_tag_score"] or 0,
        ), reverse=True)
        qualified = [row for row in rows if is_qualified(row)]
        covered = sum(row["listenbrainz_listens"] is not None for row in qualified)
        ranked_rows = [{**row, "musicbrainz_genre_covered": genre_id in covered_genre_ids}
                       for row in qualified
                       if row.get("artist_mbid") and row.get("listenbrainz_listens") is not None][:per_genre]
        manual_searches = [{**row, "musicbrainz_genre_covered": genre_id in covered_genre_ids}
                           for row in rows if row.get("artist_source") == "Atlas representative"
                           and row.get("listenbrainz_listens") is None]
        genre_details.append({
            "genre_id": genre_id,
            "genre": app_genre["name"],
            "country": app_genre["country"],
            "artist_count": len(rows),
            "qualified_artist_count": len(qualified),
            "listenbrainz_coverage": covered,
            "musicbrainz_genre_covered": genre_id in covered_genre_ids,
            "top_artists": ranked_rows,
            "manual_name_searches": manual_searches,
        })

    artist_rows_by_name: dict[str, list[dict]] = defaultdict(list)
    for item in artists:
        if item.get("artist"):
            artist_rows_by_name[norm(item["artist"])].append(item)
    app_representative_genres: dict[str, list[dict]] = defaultdict(list)
    for app_genre in published:
        for name in dict.fromkeys(app_genre.get("artists", [])):
            if name:
                app_representative_genres[norm(name)].append({
                    "genre_id": app_genre["id"], "genre": app_genre["name"],
                    "country": app_genre["country"], "source": "Atlas app representative",
                    "artist_mbid": None, "listenbrainz_listens": None,
                })
    no_listen_genres = []
    for detail, app_genre in zip(genre_details, sorted(published, key=lambda g: g["name"].casefold())):
        if detail["listenbrainz_coverage"]:
            continue
        names = list(dict.fromkeys(name for name in app_genre.get("artists", []) if name))
        listed_elsewhere, not_listed_elsewhere = [], []
        for name in names:
            if GENERIC_REPRESENTATIVE.search(name):
                not_listed_elsewhere.append(name)
                continue
            other = {}
            for match in artist_rows_by_name.get(norm(name), []):
                if match["genre_id"] != app_genre["id"]:
                    other[(match["genre_id"], "MusicBrainz artist association")] = {
                        "genre": match["genre"], "country": match["country"],
                        "source": "MusicBrainz artist association",
                        "artist_mbid": match.get("artist_mbid"),
                        "listenbrainz_listens": popularity.get(match.get("artist_mbid"), {}).get("total_listen_count"),
                    }
            for match in app_representative_genres.get(norm(name), []):
                if match["genre_id"] != app_genre["id"]:
                    other[(match["genre_id"], "Atlas app representative")] = {
                        "genre": match["genre"], "country": match["country"],
                        "source": "Atlas app representative", "artist_mbid": match["artist_mbid"],
                        "listenbrainz_listens": match["listenbrainz_listens"],
                    }
            if other:
                listed_elsewhere.append({"artist": name, "other_genres": list(other.values())})
            else:
                not_listed_elsewhere.append(name)
        no_listen_genres.append({
            "genre_id": app_genre["id"], "genre": app_genre["name"], "country": app_genre["country"],
            "app_defined_artists": names,
            "artists_listed_elsewhere": listed_elsewhere,
            "artists_not_found_elsewhere": not_listed_elsewhere,
        })
    output_payload = {
        "source": "ListenBrainz popularity API + local MusicBrainz genre associations",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "interpretation": (
            "Ranked artists require a repeated direct MusicBrainz artist genre tag "
            f"(score >= {min_artist_tag_score}) or a unique exact Atlas representative match "
            "for a genre without a matched MusicBrainz genre. Listen counts are global activity, "
            "not genre-specific popularity, nationality, or proof of genre membership."
        ),
        "minimum_direct_artist_tag_score": min_artist_tag_score,
        "artist_ids_queried": len(by_mbid),
        "artists_with_listen_data": sum(
            popularity.get(mbid, {}).get("total_listen_count") is not None for mbid in by_mbid
        ),
        "genre_count": len(genre_details),
        "app_representatives_added": len(representatives) + len(unresolved),
        "app_representatives_with_listenbrainz_id": len(representatives),
        "app_representatives_pending_name_search": len(unresolved),
        "top_artists_per_genre": per_genre,
        "genres_without_listenbrainz_artists": len(no_listen_genres),
        "genres": genre_details,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(output_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    csv_path = output.with_suffix(".csv")
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        fields = ["genre_id", "genre", "country", "rank", "artist", "artist_mbid",
                  "listenbrainz_listens", "listenbrainz_listeners", "genre_tag_score", "genre_tag_basis",
                  "artist_tag_score",
                  "artist_source", "artist_match_status", "musicbrainz_genre_covered"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for genre in genre_details:
            for rank, artist in enumerate(genre["top_artists"], 1):
                writer.writerow({"rank": rank, **{field: artist.get(field) for field in fields if field != "rank"}})
    missing_csv = output.with_name("genres_without_listenbrainz_artists.csv")
    with missing_csv.open("w", newline="", encoding="utf-8") as stream:
        fields = ["genre_id", "genre", "country", "app_defined_artists",
                  "artists_listed_elsewhere", "artists_not_found_elsewhere"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for item in no_listen_genres:
            writer.writerow({
                "genre_id": item["genre_id"], "genre": item["genre"], "country": item["country"],
                "app_defined_artists": "; ".join(item["app_defined_artists"]),
                "artists_listed_elsewhere": "; ".join(
                    f"{match['artist']} → " + ", ".join(
                        f"{g['genre']} ({g['country']}; {g['source']}; "
                        f"{g['listenbrainz_listens'] if g['listenbrainz_listens'] is not None else 'no ListenBrainz count'})"
                        for g in match["other_genres"]
                    ) for match in item["artists_listed_elsewhere"]
                ),
                "artists_not_found_elsewhere": "; ".join(item["artists_not_found_elsewhere"]),
            })
    score_csv = output.with_name("genre_artist_popularity_by_tag_score.csv")
    score_rows = [{
        **row,
        "listenbrainz_listens": popularity.get(row["artist_mbid"], {}).get("total_listen_count"),
        "listenbrainz_listeners": popularity.get(row["artist_mbid"], {}).get("total_user_count"),
    } for row in artists if row.get("artist_tag_score") is not None]
    score_rows.sort(key=lambda row: (
        row["genre"].casefold(),
        0 if row["artist_tag_score"] >= 3 else 1 if row["artist_tag_score"] == 2 else 2,
        -(row.get("listenbrainz_listens") or 0),
        row["artist"].casefold(),
    ))
    with score_csv.open("w", newline="", encoding="utf-8") as stream:
        fields = ["genre_id", "genre", "country", "artist", "artist_mbid",
                  "artist_tag_score", "score_band", "listenbrainz_listens",
                  "listenbrainz_listeners", "genre_tag_basis"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in score_rows:
            score = row["artist_tag_score"]
            writer.writerow({
                **{field: row.get(field) for field in fields if field != "score_band"},
                "score_band": "3+" if score >= 3 else str(score),
            })
    return output_payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--catalogue", type=Path, default=DEFAULT_CATALOGUE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--delay", type=float, default=1.1)
    parser.add_argument("--per-genre", type=int, default=20, choices=range(1, 21))
    parser.add_argument("--min-artist-tag-score", type=int, default=2,
                        help="minimum repeated direct MusicBrainz artist-tag score (default: 2)")
    args = parser.parse_args()
    result = collect(args.db, args.output, args.batch_size, args.delay, args.catalogue,
                     args.per_genre, args.min_artist_tag_score)
    print(json.dumps({k: result[k] for k in (
        "artist_ids_queried", "artists_with_listen_data", "genre_count",
        "app_representatives_added", "app_representatives_with_listenbrainz_id",
        "app_representatives_pending_name_search"
    )}, indent=2))
    print(args.output)


if __name__ == "__main__":
    main()
