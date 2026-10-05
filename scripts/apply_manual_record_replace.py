"""Replace one listening-room record with a different album.

Usage:
  python3 scripts/apply_manual_record_replace.py --id record-abc \
    --title 'New Album' \
    --artist 'New Artist' \
    --year 2019 \
    --spotify 'https://open.spotify.com/album/xxxxxxxxxxxxxxxxxxxxxx' \
    --rebuild

The new album gets a new shelf id. Cover and player flags are optional. The
same album in more than one genre needs --genre. A later shelf rebuild reapplies
research/manual_record_replacements.json so the old chart or Rough Guide row
does not return.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "web" / "data" / "genre_records.json"
SELECTIONS = ROOT / "research" / "manual_record_selections.json"
REPLACEMENTS = ROOT / "research" / "manual_record_replacements.json"
ROUGH_GUIDE = ROOT / "research" / "rough_guide_album_records.json"
PLAYER_FIELDS = ("youtube_url", "spotify_url", "apple_music_url")


def helpers():
    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from apply_manual_record_update import (
        back_image_url,
        bust_browser_cache,
        cover_from_link,
        load_selections,
        player_updates,
        running_bind_host,
        write_json,
    )
    from build_genre_record_pages import apply_one_replacement, record_id, record_sort_key, sort_record_lists
    return (
        back_image_url,
        bust_browser_cache,
        cover_from_link,
        load_selections,
        player_updates,
        running_bind_host,
        write_json,
        apply_one_replacement,
        record_id,
        record_sort_key,
        sort_record_lists,
    )


def load_replacements(path: Path = REPLACEMENTS) -> dict:
    if not path.exists():
        return {"version": 1, "replacements": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("replacements")
    if not isinstance(rows, list):
        rows = []
    return {"version": 1, "replacements": rows}


def matching_records(catalogue: dict, record_id: str) -> list[tuple[str, dict]]:
    found = []
    for genre_id, genre in catalogue.get("genres", {}).items():
        for record in genre.get("records", []):
            if record.get("id") == record_id:
                found.append((genre_id, record))
    return found


def replacement_record(title: str, artist: str, year: int, record_id_fn, extras: dict | None = None) -> dict:
    record = {
        "id": record_id_fn(title, artist, year),
        "title": title,
        "artist": artist,
        "year": year,
        "year_source": "manual_replacement",
        "record_source": "manual_replacement",
    }
    if extras:
        record.update(extras)
    return record


def rewrite_rough_guide(payload: dict, genre_id: str, from_id: str, title: str, artist: str, year: int, record_id_fn, extras: dict) -> bool:
    rows = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return False
    for item in rows:
        if not isinstance(item, dict) or item.get("genre_id") != genre_id:
            continue
        if record_id_fn(item.get("title") or "", item.get("artist") or "", item.get("year")) != from_id:
            continue
        item["title"] = title
        item["artist"] = artist
        item["year"] = year
        for field in PLAYER_FIELDS:
            if field in extras:
                item[field] = extras[field]
        return True
    return False


def migrate_selection(selections: dict, from_id: str, to_id: str, extras: dict) -> None:
    records = selections.setdefault("records", {})
    current = dict(records.pop(from_id, None) or {})
    current.update(extras)
    if current:
        records[to_id] = current
    elif to_id in records:
        records[to_id].update(extras)


def replace_shelf_record(
    catalogue: dict,
    replacements: dict,
    selections: dict,
    rough_guide: dict | None,
    from_id: str,
    genre_id: str,
    title: str,
    artist: str,
    year: int,
    extras: dict,
    apply_one_fn,
    record_id_fn,
) -> dict:
    new_id = record_id_fn(title, artist, year)
    if new_id == from_id:
        raise ValueError("title, artist, and year are unchanged")
    current = next(
        (row for row in catalogue.get("genres", {}).get(genre_id, {}).get("records", []) if row.get("id") == from_id),
        {},
    )
    inherited = dict(selections.get("records", {}).get(from_id) or {})
    for field in PLAYER_FIELDS:
        if field not in extras:
            value = inherited.get(field) or current.get(field)
            if isinstance(value, str) and value.startswith("https://"):
                extras[field] = value
    if "cover" not in extras:
        cover = inherited.get("cover") or current.get("cover")
        if isinstance(cover, dict) and isinstance(cover.get("front_url"), str) and cover["front_url"].startswith("https://"):
            extras["cover"] = cover
    for other_genre, genre in catalogue.get("genres", {}).items():
        for row in genre.get("records", []):
            if row.get("id") != new_id:
                continue
            if other_genre == genre_id and row.get("id") == from_id:
                continue
            raise ValueError(f"that album is already on {other_genre}")
    new_record = replacement_record(title, artist, year, record_id_fn, extras)
    apply_one_fn(catalogue.setdefault("genres", {}).setdefault(genre_id, {"records": []}), from_id, new_record)
    replacements.setdefault("replacements", []).append({
        "genre_id": genre_id,
        "from_id": from_id,
        "title": title,
        "artist": artist,
        "year": year,
        **{field: extras[field] for field in PLAYER_FIELDS if field in extras},
        **({"cover": extras["cover"]} if "cover" in extras else {}),
    })
    migrate_selection(selections, from_id, new_id, extras)
    if rough_guide is not None:
        rewrite_rough_guide(rough_guide, genre_id, from_id, title, artist, year, record_id_fn, extras)
    return new_record


def main():
    (
        back_image_url,
        bust_browser_cache,
        cover_from_link,
        load_selections,
        player_updates,
        running_bind_host,
        write_json,
        apply_one_fn,
        record_id,
        _record_sort_key,
        sort_record_lists,
    ) = helpers()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="Shelf record ID to replace")
    parser.add_argument("--genre", help="Genre id when the same record sits on more than one shelf")
    parser.add_argument("--title", required=True)
    parser.add_argument("--artist", required=True)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--image", help="Commons file, direct https image, or Discogs release/master page")
    parser.add_argument("--image-source", help="https page for a non-Commons cover")
    parser.add_argument("--attribution", help="Credit line shown under the cover")
    parser.add_argument("--back", help="Back-cover image URL")
    parser.add_argument("--youtube", help="YouTube watch, share, shorts, or embed URL")
    parser.add_argument("--spotify", help="Spotify album or track URL")
    parser.add_argument("--apple", help="Apple Music album or song URL")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--allow-mvp-lock", action="store_true", help="Override MVP country lock after deliberate review")
    args = parser.parse_args()
    if args.image_source and not args.image:
        parser.error("--image-source requires --image")
    if args.attribution and not args.image and not args.back:
        parser.error("--attribution requires --image or --back")

    catalogue = json.loads(RECORDS.read_text(encoding="utf-8"))
    matches = matching_records(catalogue, args.id)
    if not matches:
        parser.error(f"unknown record ID: {args.id}")
    genre_ids = [genre_id for genre_id, _record in matches]
    if args.genre:
        if args.genre not in genre_ids:
            parser.error(f"{args.id} is not on {args.genre}")
        genre_id = args.genre
    elif len(genre_ids) == 1:
        genre_id = genre_ids[0]
    else:
        parser.error("that record is on more than one genre; pass --genre " + ", ".join(genre_ids))
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from mvp_locks import assert_genre_unlocked, assert_record_unlocked
    assert_record_unlocked(args.id, allow=args.allow_mvp_lock)
    assert_genre_unlocked(genre_id, allow=args.allow_mvp_lock)

    extras = {}
    try:
        extras.update(player_updates(args.youtube, args.spotify, args.apple))
        if args.image:
            extras["cover"] = cover_from_link(args.image, args.image_source, args.attribution)
        if args.back:
            cover = dict(extras.get("cover") or {})
            if not cover.get("front_url"):
                raise ValueError("--back requires a cover; pass --image as well")
            cover["back_url"] = back_image_url(args.back)
            if args.attribution and not args.image:
                cover["attribution"] = args.attribution
            extras["cover"] = cover
    except ValueError as exc:
        parser.error(str(exc))

    replacements = load_replacements()
    selections = load_selections()
    rough_guide = json.loads(ROUGH_GUIDE.read_text(encoding="utf-8")) if ROUGH_GUIDE.exists() else None
    try:
        new_record = replace_shelf_record(
            catalogue,
            replacements,
            selections,
            rough_guide,
            args.id,
            genre_id,
            args.title.strip(),
            args.artist.strip(),
            args.year,
            extras,
            apply_one_fn,
            record_id,
        )
    except ValueError as exc:
        parser.error(str(exc))

    write_json(REPLACEMENTS, replacements)
    write_json(SELECTIONS, selections)
    sort_record_lists(catalogue.get("genres", {}))
    write_json(RECORDS, catalogue)
    if rough_guide is not None:
        write_json(ROUGH_GUIDE, rough_guide)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bust_browser_cache(stamp)
    print(f"replaced {args.id} on {genre_id}")
    print(f"new {new_record['id']}  {new_record['year']}  {new_record['artist']} — {new_record['title']}")
    if "cover" in extras:
        print(f"image: {extras['cover']['front_url']}")
    for field in PLAYER_FIELDS:
        if field in extras:
            print(f"{field}: {extras[field]}")
    if args.rebuild:
        environment = os.environ.copy()
        environment["ATLAS_BIND_HOST"] = running_bind_host()
        subprocess.run(
            ["docker", "compose", "up", "--build", "-d", "--wait"],
            cwd=ROOT,
            env=environment,
            check=True,
        )
        print(f"rebuilt atlas on {environment['ATLAS_BIND_HOST']}:5186")
    else:
        print("shelf data updated; pass --rebuild to refresh the running container")


if __name__ == "__main__":
    main()
