"""Apply a manually chosen image, description, or video to one published genre.

Usage:
  python3 scripts/apply_manual_genre_update.py --id afg-contemporary \
    --image 'https://commons.wikimedia.org/wiki/File:Example.jpg' \
    --description 'Quoted source text of at least 60 characters.' \
    --description-url 'https://example.org/article' \
    --video 'https://www.youtube.com/watch?v=xxxxxxxxxxx'

Any of --image, --description, or --video may be used alone. --description and
--description-url are a pair. --rebuild refreshes the running container after
the catalogue and browser data are written.
"""
import argparse
import json
import re
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
USER_AGENT = "MusicAtlasManualSelection/1.0 (local editorial update)"
YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
GENERIC_NOTE_PREFIXES = (
    "Country-wide fill is a coarse association.",
    "Country association used pending",
    "Tripoli continuity does not imply",
    "Moorish-community association, not",
    "Historical Hargeysa association only",
)


def file_title_from_image_link(link):
    parsed = urlparse(link.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host.endswith("wikimedia.org"):
        raise ValueError("image link must be an https Wikimedia Commons file or upload URL")
    path = unquote(parsed.path)
    if host.endswith("commons.wikimedia.org") and "/wiki/File:" in path:
        title = path.split("/wiki/File:", 1)[1]
    elif host.endswith("commons.wikimedia.org") and path == "/w/index.php":
        raw_title = parse_qs(parsed.query).get("title", [""])[0]
        if not raw_title.startswith("File:"):
            raise ValueError("image link must point at a Commons File: page")
        title = unquote(raw_title[5:])
    elif "/wikipedia/commons/" in path:
        title = Path(path).name
    else:
        raise ValueError("image link must be a Commons file page or a Commons upload URL")
    title = title.split("#", 1)[0].strip()
    if not title or "/" in title:
        raise ValueError("image link did not contain a Commons file name")
    return title


def watch_url_from_video_link(link):
    parsed = urlparse(link.strip())
    host = (parsed.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    if parsed.scheme != "https":
        raise ValueError("video link must be https")
    video_id = ""
    if host in {"youtu.be", "youtube.com"}:
        if host == "youtu.be":
            video_id = unquote(parsed.path.strip("/").split("/")[0])
        elif parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            parts = [part for part in parsed.path.split("/") if part]
            if parts and parts[0] in {"embed", "shorts", "live"} and len(parts) > 1:
                video_id = parts[1]
    if not YOUTUBE_ID.fullmatch(video_id):
        raise ValueError("video link must be a YouTube watch, share, shorts, or embed URL")
    return f"https://www.youtube.com/watch?v={video_id}"


def image_record(candidate, depicts=None, reviewed_at=None):
    chosen = " ".join((depicts or "").split())
    if len(chosen) < 20:
        title = candidate.get("title") or "Selected image"
        chosen = f"{title}, selected from the Commons file page."
    creator = candidate.get("creator") or "Unknown creator"
    provider = candidate["provider"]
    via = "Wikimedia Commons" if provider == "wikimedia_commons" else "Openverse"
    return {
        "image_url": candidate["image_url"],
        "source_page_url": candidate["source_page_url"].replace("File%3A", "File:"),
        "title": candidate.get("title") or "Untitled",
        "creator": creator,
        "license": candidate["license"],
        "attribution": f"{creator}, {candidate['license']}, via {via}",
        "depicts": chosen[:240],
        "provider": provider,
        "reviewed_at": reviewed_at or date.today().isoformat(),
    }


def prefer_source(sources, url):
    kept = []
    for source in sources or []:
        if source == url or (isinstance(source, dict) and source.get("url") == url):
            continue
        kept.append(source)
    return [url, *kept]


def apply_description(genre, text, url):
    note = text.strip()
    if len(note) < 60:
        raise ValueError("description must be at least 60 characters")
    if note.startswith(GENERIC_NOTE_PREFIXES):
        raise ValueError("description is a generic fallback, not a selected source text")
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("description link must be https")
    genre["note"] = note
    genre["sources"] = prefer_source(genre.get("sources"), url.strip())
    genre["prefer_local_note"] = True


def apply_video(genre, watch_url, title, artist, reviewed_at=None):
    watch_url = watch_url_from_video_link(watch_url)
    title = title.strip()
    artist = artist.strip()
    if not title or not artist:
        raise ValueError("video needs a title and an artist or channel name")
    selected_id = parse_qs(urlparse(watch_url).query)["v"][0]
    kept = []
    for example in genre.get("youtube_examples") or []:
        example_url = example.get("youtube_url", "")
        example_id = parse_qs(urlparse(example_url).query).get("v", [""])[0]
        if example_id == selected_id or example.get("artist") == artist:
            continue
        kept.append(example)
    kept.append({
        "artist": artist,
        "title": title,
        "youtube_url": watch_url,
        "reviewed_at": reviewed_at or date.today().isoformat(),
        "attribution_basis": "user-approved practice-level example",
    })
    genre["youtube_examples"] = kept


def write_json(path, value):
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        temporary.write(payload)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def bust_browser_cache(stamp):
    app = ROOT / "web" / "app.js"
    app_text = app.read_text(encoding="utf-8")
    updated, count = re.subn(r"const dataVersion = '[^']*';", f"const dataVersion = '{stamp}';", app_text, count=1)
    if count != 1:
        raise RuntimeError("browser data version marker was not found")
    app.write_text(updated, encoding="utf-8")
    index = ROOT / "web" / "index.html"
    index_text = index.read_text(encoding="utf-8")
    index_text = re.sub(r"(styles\.css\?v=)[^\"']+", rf"\g<1>{stamp}", index_text)
    index_text = re.sub(r"(app\.js\?v=)[^\"']+", rf"\g<1>{stamp}", index_text)
    index.write_text(index_text, encoding="utf-8")


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def youtube_details(watch_url):
    endpoint = "https://www.youtube.com/oembed?" + urllib.parse.urlencode({"url": watch_url, "format": "json"})
    payload = fetch_json(endpoint)
    title = (payload.get("title") or "").strip()
    artist = (payload.get("author_name") or "").strip()
    if not title or not artist:
        raise ValueError("YouTube did not return a title and channel name; pass --video-title and --video-artist")
    return title, artist


def publish():
    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from build_static_data import build_coverage, build_genres
    from validate_genres import map_keys, validate_record
    return build_genres, build_coverage, map_keys, validate_record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="Published genre ID")
    parser.add_argument("--image", help="Commons file page or Commons upload URL")
    parser.add_argument("--depicts", help="Short depiction caption. Defaults to the file title.")
    parser.add_argument("--description", help="Description text shown on the genre panel")
    parser.add_argument("--description-url", help="https page the description is quoted from")
    parser.add_argument("--video", help="YouTube watch, share, shorts, or embed URL")
    parser.add_argument("--video-title", help="Override the title returned by YouTube")
    parser.add_argument("--video-artist", help="Override the channel name returned by YouTube")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild and restart the atlas container")
    args = parser.parse_args()
    if bool(args.description) != bool(args.description_url):
        parser.error("--description and --description-url must be used together")
    if not args.image and not args.description and not args.video:
        parser.error("choose --image, --description, or --video")
    if bool(args.video_title) != bool(args.video_artist):
        parser.error("--video-title and --video-artist must be used together")
    if (args.video_title or args.video_artist) and not args.video:
        parser.error("--video-title and --video-artist require --video")

    catalogue = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    genre = next((entry for entry in catalogue["entries"] if entry.get("id") == args.id), None)
    if genre is None:
        parser.error(f"unknown genre ID: {args.id}")
    if genre.get("status") != "published":
        parser.error(f"{args.id} is not published")

    if args.image:
        from find_genre_images import commons_file_candidate
        candidate = commons_file_candidate(file_title_from_image_link(args.image))
        if candidate is None:
            parser.error("Commons file is missing or does not have a reusable licence")
        genre["image"] = image_record(candidate, args.depicts)
    if args.description:
        apply_description(genre, args.description, args.description_url)
    if args.video:
        watch_url = watch_url_from_video_link(args.video)
        if args.video_title:
            title, artist = args.video_title, args.video_artist
        else:
            title, artist = youtube_details(watch_url)
        apply_video(genre, watch_url, title, artist)

    _, _, map_keys, validate_record = publish()
    country_codes, region_names = map_keys()
    public = {key: value for key, value in genre.items() if key not in {"status", "research"}}
    try:
        validate_record(public, country_codes, region_names)
    except AssertionError as exc:
        parser.error(f"selected genre failed validation: {exc}")
    write_json(CATALOGUE, catalogue)
    build_genres, build_coverage, _, _ = publish()
    published = build_genres(False)
    if args.id not in {item["id"] for item in published}:
        parser.error("genre was held back from browser data")
    build_coverage(published, False)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bust_browser_cache(stamp)
    print(f"updated {args.id}")
    if args.image:
        print(f"image: {genre['image']['source_page_url']}")
    if args.description:
        print(f"description: {args.description_url}")
    if args.video:
        chosen = genre["youtube_examples"][-1]
        print(f"video: {chosen['title']} — {chosen['artist']} — {chosen['youtube_url']}")
    if args.rebuild:
        import os
        import subprocess
        environment = os.environ.copy()
        environment.setdefault("ATLAS_BIND_HOST", "127.0.0.1")
        subprocess.run(
            ["docker", "compose", "up", "--build", "-d", "--wait"],
            cwd=ROOT,
            env=environment,
            check=True,
        )
        print(f"rebuilt atlas on {environment['ATLAS_BIND_HOST']}:5186")
    else:
        print("browser data updated; pass --rebuild to refresh the running container")


if __name__ == "__main__":
    main()
