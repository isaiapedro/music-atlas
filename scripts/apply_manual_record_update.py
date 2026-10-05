"""Apply a chosen cover and listening-room players to one shelf record.

Usage:
  python3 scripts/apply_manual_record_update.py --id record-abc \
    --image 'https://commons.wikimedia.org/wiki/File:Example.jpg' \
    --youtube 'https://www.youtube.com/watch?v=xxxxxxxxxxx' \
    --spotify 'https://open.spotify.com/album/xxxxxxxxxxxxxxxxxxxxxx' \
    --apple 'https://music.apple.com/us/album/example/123456789'

Any of --image, --youtube, --spotify, or --apple may be used alone. A Discogs
release or master page saves the cover and the back when Discogs has both. A
cover that is not a Commons file or a Discogs page also needs --image-source.
--back sets the reverse image. --youtube accepts a watch URL or a playlist URL.
--rebuild refreshes the running container after
the shelf data is written.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "web" / "data" / "genre_records.json"
SELECTIONS = ROOT / "research" / "manual_record_selections.json"
PLAYER_FIELDS = ("youtube_url", "spotify_url", "apple_music_url")
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".gif")
SPOTIFY_ID = re.compile(r"^[A-Za-z0-9]{22}$")
APPLE_ID = re.compile(r"^\d{6,}$")
YOUTUBE_PLAYLIST = re.compile(r"^(PL|OLAK5uy_)[A-Za-z0-9_-]{10,}$")


def helpers():
    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from apply_manual_genre_update import file_title_from_image_link, watch_url_from_video_link
    return file_title_from_image_link, watch_url_from_video_link


def https_page(link, label):
    parsed = urlparse(link.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{label} must be https")
    return link.strip()


def is_commons_link(link):
    parsed = urlparse(link.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host.endswith("wikimedia.org"):
        return False
    path = unquote(parsed.path)
    return "/wiki/File:" in path or path == "/w/index.php" or "/wikipedia/commons/" in path


def discogs_target(link):
    parsed = urlparse(link.strip())
    host = (parsed.hostname or "").lower().removeprefix("www.")
    if parsed.scheme != "https" or host != "discogs.com":
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] not in {"release", "master"}:
        return None
    ident = parts[1].split("-", 1)[0]
    if not ident.isdigit() or int(ident) < 1:
        return None
    return parts[0], int(ident)


def discogs_token():
    token = os.environ.get("DISCOGS_TOKEN", "").strip().strip('"').strip("'")
    if token:
        return token
    env_path = ROOT / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "DISCOGS_TOKEN":
            return value.strip().strip('"').strip("'")
    return ""


def cover_from_discogs_payload(kind, ident, payload, attribution=None):
    images = payload.get("images", []) if isinstance(payload, dict) else []
    usable = [
        image for image in images
        if isinstance(image, dict) and isinstance(image.get("uri"), str) and image["uri"].startswith("https://")
    ]
    if not usable:
        raise ValueError("Discogs page has no cover image")
    front = next((image for image in usable if image.get("type") == "primary"), usable[0])
    back = next((image for image in usable if image is not front and image.get("type") == "secondary"), None)
    source = payload.get("uri")
    if not isinstance(source, str) or not source.startswith("https://"):
        source = f"https://www.discogs.com/{kind}/{ident}"
    cover = {
        "front_url": front["uri"],
        "source_url": source,
        "attribution": attribution or "Data provided by Discogs.",
    }
    if back:
        cover["back_url"] = back["uri"]
    return cover


def fetch_discogs_payload(kind, ident):
    token = discogs_token()
    if not token:
        raise ValueError("Discogs token is not configured")
    collection = "releases" if kind == "release" else "masters"
    request = urllib.request.Request(
        f"https://api.discogs.com/{collection}/{ident}",
        headers={
            "Authorization": f"Discogs token={token}",
            "User-Agent": "MusicAtlas/0.1 (manual record cover)",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ValueError("Discogs did not return this release") from exc
    if not isinstance(payload, dict):
        raise ValueError("Discogs did not return this release")
    return payload


def direct_image_url(link):
    parsed = urlparse(https_page(link, "image link"))
    host = (parsed.hostname or "").lower()
    path = unquote(parsed.path).lower()
    if path.endswith(IMAGE_SUFFIXES):
        return link.strip()
    if host == "coverartarchive.org" or host == "archive.org" or host.endswith(".archive.org"):
        return link.strip().split("?", 1)[0]
    raise ValueError("image link must be a Commons file or a direct https image URL")


def cover_from_link(link, source_url=None, attribution=None, discogs_payload=None):
    target = discogs_target(link)
    if target:
        kind, ident = target
        payload = discogs_payload if discogs_payload is not None else fetch_discogs_payload(kind, ident)
        return cover_from_discogs_payload(kind, ident, payload, attribution)
    if is_commons_link(link):
        file_title_from_image_link, _watch = helpers()
        from find_genre_images import commons_file_candidate
        candidate = commons_file_candidate(file_title_from_image_link(link))
        if candidate is None:
            raise ValueError("Commons file is missing or does not have a reusable licence")
        creator = candidate.get("creator") or "Unknown creator"
        credit = attribution or f"{creator}, {candidate['license']}, via Wikimedia Commons"
        return {
            "front_url": candidate["image_url"],
            "source_url": candidate["source_page_url"].replace("File%3A", "File:"),
            "attribution": credit,
        }
    if not source_url:
        raise ValueError("a non-Commons image needs --image-source, or pass a Discogs release page to save the cover and back")
    return {
        "front_url": direct_image_url(link),
        "source_url": https_page(source_url, "image source"),
        "attribution": attribution or "Selected cover.",
    }


def back_image_url(link):
    if is_commons_link(link):
        return cover_from_link(link)["front_url"]
    return direct_image_url(link)


def spotify_url(link):
    parsed = urlparse(https_page(link, "Spotify link"))
    host = (parsed.hostname or "").lower().removeprefix("www.")
    if host != "open.spotify.com":
        raise ValueError("Spotify link must be an open.spotify.com album or track")
    parts = [part for part in parsed.path.split("/") if part]
    if parts and parts[0].startswith("intl-"):
        parts = parts[1:]
    if parts and parts[0] == "embed":
        parts = parts[1:]
    if len(parts) < 2 or parts[0] not in {"album", "track"} or not SPOTIFY_ID.fullmatch(parts[1]):
        raise ValueError("Spotify link must be an album or track URL")
    return f"https://open.spotify.com/{parts[0]}/{parts[1]}"


def apple_music_url(link):
    parsed = urlparse(https_page(link, "Apple Music link"))
    host = (parsed.hostname or "").lower().removeprefix("www.")
    if host != "music.apple.com":
        raise ValueError("Apple Music link must be a music.apple.com album or song")
    parts = [part for part in unquote(parsed.path).split("/") if part]
    kind = next((part for part in parts if part in {"album", "song"}), None)
    if kind is None or not parts or not APPLE_ID.fullmatch(parts[-1]):
        raise ValueError("Apple Music link must end with an album or song id")
    path = parsed.path if parsed.path.startswith("/") else f"/{parsed.path}"
    return f"https://music.apple.com{path.rstrip('/')}"


def youtube_listen_url(link):
    cleaned = https_page(link, "YouTube link").replace("\\?", "?").replace("\\=", "=").replace("\\&", "&")
    parsed = urlparse(cleaned)
    host = (parsed.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    query = parse_qs(parsed.query)
    playlist = (query.get("list") or [""])[0]
    if host in {"youtube.com", "music.youtube.com"} and YOUTUBE_PLAYLIST.fullmatch(playlist):
        return f"https://www.youtube.com/playlist?list={playlist}"
    _, watch_url_from_video_link = helpers()
    return watch_url_from_video_link(cleaned)


def player_updates(youtube=None, spotify=None, apple=None):
    updates = {}
    if youtube:
        updates["youtube_url"] = youtube_listen_url(youtube)
    if spotify:
        updates["spotify_url"] = spotify_url(spotify)
    if apple:
        updates["apple_music_url"] = apple_music_url(apple)
    return updates


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        temporary.write(payload)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def load_selections():
    if not SELECTIONS.exists():
        return {"version": 1, "records": {}}
    payload = json.loads(SELECTIONS.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, dict):
        records = {}
    return {"version": 1, "records": records}


def matching_records(catalogue, record_id):
    found = []
    for genre_id, genre in catalogue.get("genres", {}).items():
        for record in genre.get("records", []):
            if record.get("id") == record_id:
                found.append((genre_id, record))
    return found


def bust_browser_cache(stamp):
    script = ROOT / "web" / "records.js"
    text = script.read_text(encoding="utf-8")
    text, art_count = re.subn(
        r"const ART_ENDPOINT_VERSION = '[^']*';",
        f"const ART_ENDPOINT_VERSION = '{stamp}';",
        text,
        count=1,
    )
    text, data_count = re.subn(r"(genre_records\.json\?v=)[^'\"]+", rf"\g<1>{stamp}", text, count=1)
    if art_count != 1 or data_count != 1:
        raise RuntimeError("listening-room cache markers were not found")
    script.write_text(text, encoding="utf-8")
    page = ROOT / "web" / "records.html"
    page_text = page.read_text(encoding="utf-8")
    page_text = re.sub(r"(styles\.css\?v=)[^\"']+", rf"\g<1>{stamp}", page_text)
    page_text = re.sub(r"(records\.js\?v=)[^\"']+", rf"\g<1>{stamp}", page_text)
    page.write_text(page_text, encoding="utf-8")


def running_bind_host():
    configured = os.environ.get("ATLAS_BIND_HOST")
    if configured:
        return configured
    completed = subprocess.run(
        ["docker", "inspect", "--format", "{{range .Config.Env}}{{println .}}{{end}}", "music_atlas-atlas-1"],
        check=False,
        capture_output=True,
        text=True,
    )
    for line in completed.stdout.splitlines():
        if line.startswith("ATLAS_BIND_HOST="):
            host = line.split("=", 1)[1].strip()
            if host:
                return host
    return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="Shelf record ID, as in genre_records.json")
    parser.add_argument("--image", help="Commons file, direct https image, or Discogs release/master page")
    parser.add_argument("--image-source", help="https page for a non-Commons cover")
    parser.add_argument("--attribution", help="Credit line shown under the cover")
    parser.add_argument("--back", help="Back-cover image URL")
    parser.add_argument("--youtube", help="YouTube watch, playlist, share, shorts, or embed URL")
    parser.add_argument("--spotify", help="Spotify album or track URL")
    parser.add_argument("--apple", help="Apple Music album or song URL")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild and restart the atlas container")
    parser.add_argument("--allow-mvp-lock", action="store_true", help="Override MVP country lock after deliberate review")
    args = parser.parse_args()
    if not args.image and not args.back and not args.youtube and not args.spotify and not args.apple:
        parser.error("choose --image, --back, --youtube, --spotify, or --apple")
    if args.image_source and not args.image:
        parser.error("--image-source requires --image")
    if args.attribution and not args.image and not args.back:
        parser.error("--attribution requires --image or --back")

    catalogue = json.loads(RECORDS.read_text(encoding="utf-8"))
    matches = matching_records(catalogue, args.id)
    if not matches:
        parser.error(f"unknown record ID: {args.id}")
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from mvp_locks import assert_genre_unlocked, assert_record_unlocked, locked_genre_ids
    assert_record_unlocked(args.id, allow=args.allow_mvp_lock)
    for genre_id, _record in matches:
        if genre_id in locked_genre_ids():
            assert_genre_unlocked(genre_id, allow=args.allow_mvp_lock)

    selections = load_selections()
    current = dict(selections["records"].get(args.id) or {})
    try:
        if args.image:
            current["cover"] = cover_from_link(args.image, args.image_source, args.attribution)
        if args.back:
            cover = dict(current.get("cover") or {})
            if not cover.get("front_url"):
                raise ValueError("--back requires a cover; pass --image as well")
            cover["back_url"] = back_image_url(args.back)
            if args.attribution and not args.image:
                cover["attribution"] = args.attribution
            current["cover"] = cover
        current.update(player_updates(args.youtube, args.spotify, args.apple))
    except ValueError as exc:
        parser.error(str(exc))

    selections["records"][args.id] = current
    for _genre_id, record in matches:
        if "cover" in current:
            record["cover"] = current["cover"]
        for field in PLAYER_FIELDS:
            if field in current:
                record[field] = current[field]
    from build_genre_record_pages import sort_record_lists
    sort_record_lists(catalogue.get("genres", {}))
    write_json(SELECTIONS, selections)
    write_json(RECORDS, catalogue)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bust_browser_cache(stamp)
    title = matches[0][1].get("title")
    artist = matches[0][1].get("artist")
    genres = ", ".join(genre_id for genre_id, _record in matches)
    print(f"updated {args.id} — {title} — {artist}")
    print(f"genres: {genres}")
    if "cover" in current:
        print(f"image: {current['cover']['front_url']}")
    for field in PLAYER_FIELDS:
        if field in current:
            print(f"{field}: {current[field]}")
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
