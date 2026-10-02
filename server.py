"""Same-origin Music Atlas server with an on-demand, rights-aware art proxy."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import IPv4Address, ip_address
from pathlib import Path
import base64
import os
import json
import re
import time
import tempfile
import threading
import unicodedata
from difflib import SequenceMatcher
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

WEB = Path(__file__).resolve().parent / "web"
RECORDS = WEB / "data" / "genre_records.json"
DISCOGS_PATHS = WEB / "data" / "discogs_record_paths.json"
ART_STATUS_PATH = Path(os.getenv(
    "ATLAS_ART_STATUS_PATH", Path(__file__).resolve().parent / ".local" / "discogs" / "runtime" / "record_art_status.json"))
ART_CACHE_TTL = 6 * 60 * 60
SPOTIFY_ART_TTL = 60 * 60
SPOTIFY_TOKEN = {"value": "", "expires": 0.0}
ART_CACHE: dict[str, tuple[float, dict]] = {}
ART_STATUS_LOCK = threading.Lock()
DISCOGS_REQUEST_LOCK = threading.Lock()
DISCOGS_NEXT_REQUEST = 0.0


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_art_status() -> dict[str, dict]:
    try:
        payload = read_json(ART_STATUS_PATH)
    except (OSError, json.JSONDecodeError):
        return {}
    records = payload.get("records", {}) if isinstance(payload, dict) else {}
    return records if isinstance(records, dict) else {}


ART_STATUS = read_art_status()


def remember_art_status(record_id: str, **value: object) -> None:
    """Persist outcomes only: no artwork bytes, URLs, credentials, or API payloads."""
    with ART_STATUS_LOCK:
        ART_STATUS[record_id] = {**value, "updated_at": int(time.time())}
        ART_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=ART_STATUS_PATH.parent,
                                         prefix=".record-art-", delete=False) as stream:
            json.dump({"version": 1, "records": ART_STATUS}, stream, ensure_ascii=False,
                      indent=2, sort_keys=True)
            temporary = Path(stream.name)
        temporary.replace(ART_STATUS_PATH)


def public_record(record_id: str) -> dict | None:
    catalogue = read_json(RECORDS)
    for genre in catalogue.get("genres", {}).values():
        for record in genre.get("records", []):
            if record.get("id") == record_id:
                return record
    return None


def approved_discogs_release(record_id: str) -> int | None:
    if not DISCOGS_PATHS.exists():
        return None
    value = read_json(DISCOGS_PATHS).get("matches", {}).get(record_id, {})
    release_id = value.get("release_id") if isinstance(value, dict) else None
    return release_id if isinstance(release_id, int) and release_id > 0 else None


def remembered_discogs_release(record_id: str) -> int | None:
    value = ART_STATUS.get(record_id, {})
    release_id = value.get("release_id") if isinstance(value, dict) else None
    return release_id if isinstance(release_id, int) and release_id > 0 else None


def request_json(url: str, headers: dict[str, str]) -> dict | None:
    try:
        with urlopen(Request(url, headers=headers), timeout=12) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def normalized(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def discogs_candidate_score(record: dict, candidate: dict) -> float:
    title = normalized(record.get("title"))
    candidate_title = normalized(candidate.get("title"))
    artist = normalized(record.get("artist"))
    title_score = max(SequenceMatcher(None, title, candidate_title).ratio(),
                      1.0 if title and title in candidate_title else 0.0)
    artist_score = max(SequenceMatcher(None, artist, candidate_title).ratio(),
                       1.0 if artist and artist in candidate_title else 0.0)
    year = record.get("year")
    year_score = .5 if year is None else (1.0 if str(year) == str(candidate.get("year") or "") else 0.0)
    return round(title_score * .58 + artist_score * .30 + year_score * .12, 4)


def discogs_request_json(url: str) -> dict | None:
    """Serialize Discogs calls at a deliberately conservative rate."""
    global DISCOGS_NEXT_REQUEST
    token = os.getenv("DISCOGS_TOKEN")
    if not token:
        return None
    with DISCOGS_REQUEST_LOCK:
        delay = DISCOGS_NEXT_REQUEST - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        DISCOGS_NEXT_REQUEST = time.monotonic() + 1.25
        return request_json(url, {"Authorization": f"Discogs token={token}",
                                  "User-Agent": "MusicAtlas/0.1 (on-demand record artwork)"})


def discover_discogs_release(record: dict) -> int | None:
    """Find a high-confidence edition when a visitor opens a genre record shelf."""
    params = {"type": "release", "artist": record.get("artist", ""),
              "release_title": record.get("title", "")}
    if record.get("year") is not None:
        params["year"] = str(record["year"])
    payload = discogs_request_json("https://api.discogs.com/database/search?" + urlencode(params))
    if payload is None:
        return None
    candidates = payload.get("results", []) if payload else []
    if not isinstance(candidates, list):
        return None
    best = max(candidates, key=lambda item: discogs_candidate_score(record, item), default=None)
    if not isinstance(best, dict):
        remember_art_status(record["id"], status="no_match")
        return None
    score = discogs_candidate_score(record, best)
    release_id = best.get("id")
    if score < .95 or not isinstance(release_id, int) or release_id < 1:
        remember_art_status(record["id"], status="needs_review", match_score=score)
        return None
    remember_art_status(record["id"], status="matched", release_id=release_id,
                        match_score=score, source_url=f"https://www.discogs.com{best.get('uri', '')}")
    return release_id


def discogs_art(release_id: int) -> dict | None:
    payload = discogs_request_json(f"https://api.discogs.com/releases/{release_id}")
    images = payload.get("images", []) if payload else []
    usable = [image for image in images if isinstance(image, dict) and image.get("uri")]
    if not usable:
        return None
    front = next((image for image in usable if image.get("type") == "primary"), usable[0])
    # Discogs orders conventional album images front then back, but the API does
    # not classify a back explicitly. A secondary image is therefore optional.
    back = next((image for image in usable if image is not front and image.get("type") == "secondary"), None)
    return {
        "provider": "Discogs",
        "source_url": payload.get("uri") or f"https://www.discogs.com/release/{release_id}",
        "front_url": front["uri"],
        "back_url": back.get("uri") if back else None,
        "attribution": "Data provided by Discogs.",
    }


def musicbrainz_art(release_group_mbid: str | None) -> dict | None:
    if not release_group_mbid:
        return None
    payload = request_json(
        f"https://coverartarchive.org/release-group/{release_group_mbid}",
        {"User-Agent": "MusicAtlas/0.1 (on-demand record artwork)"},
    )
    images = payload.get("images", []) if payload else []
    front = next((image for image in images if image.get("front") and image.get("image")), None)
    back = next((image for image in images if image.get("back") and image.get("image")), None)
    if not front and not back:
        return None
    return {
        "provider": "Cover Art Archive / MusicBrainz",
        "source_url": payload.get("release") or f"https://musicbrainz.org/release-group/{release_group_mbid}",
        "front_url": front.get("image") if front else back["image"],
        "back_url": back.get("image") if back and back is not front else None,
        "attribution": "Cover art provided by the Cover Art Archive via MusicBrainz.",
    }


def spotify_target(url: str | None) -> tuple[str, str] | None:
    parsed = urlparse(url or "")
    host = (parsed.hostname or "").lower().removeprefix("www.")
    if parsed.scheme != "https" or host != "open.spotify.com":
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if parts and parts[0].startswith("intl-"):
        parts = parts[1:]
    if parts and parts[0] == "embed":
        parts = parts[1:]
    if len(parts) < 2 or parts[0] not in {"album", "track"} or not re.fullmatch(r"[A-Za-z0-9]{22}", parts[1]):
        return None
    return parts[0], parts[1]


def spotify_access_token() -> str:
    now = time.time()
    if SPOTIFY_TOKEN["value"] and SPOTIFY_TOKEN["expires"] > now + 30:
        return str(SPOTIFY_TOKEN["value"])
    client_id = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return ""
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    request = Request(
        "https://accounts.spotify.com/api/token",
        data=urlencode({"grant_type": "client_credentials"}).encode(),
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "MusicAtlas/0.1 (on-demand record artwork)",
        },
    )
    try:
        with urlopen(request, timeout=12) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return ""
    token = payload.get("access_token") if isinstance(payload, dict) else ""
    if not isinstance(token, str) or not token:
        return ""
    expires = payload.get("expires_in") if isinstance(payload, dict) else 3600
    SPOTIFY_TOKEN["value"] = token
    SPOTIFY_TOKEN["expires"] = now + (expires if isinstance(expires, int) and expires > 0 else 3600)
    return token


def largest_spotify_image(images: object) -> dict | None:
    if not isinstance(images, list):
        return None
    usable = [
        image for image in images
        if isinstance(image, dict) and isinstance(image.get("url"), str) and image["url"].startswith("https://")
    ]
    if not usable:
        return None
    return max(usable, key=lambda image: image.get("width") if isinstance(image.get("width"), int) else 0)


def spotify_art(record: dict) -> dict | None:
    target = spotify_target(record.get("spotify_url"))
    token = spotify_access_token()
    if not target or not token:
        return None
    kind, ident = target
    payload = request_json(
        f"https://api.spotify.com/v1/{'tracks' if kind == 'track' else 'albums'}/{ident}",
        {"Authorization": f"Bearer {token}", "Accept": "application/json",
         "User-Agent": "MusicAtlas/0.1 (on-demand record artwork)"},
    )
    album = (payload or {}).get("album") if kind == "track" else payload
    if not isinstance(album, dict):
        return None
    image = largest_spotify_image(album.get("images"))
    if not image:
        return None
    external = album.get("external_urls") if isinstance(album.get("external_urls"), dict) else {}
    source = external.get("spotify") if isinstance(external, dict) else ""
    if not isinstance(source, str) or not source.startswith("https://open.spotify.com/"):
        source = f"https://open.spotify.com/album/{ident}" if kind == "album" else f"https://open.spotify.com/track/{ident}"
    return {
        "provider": "Spotify",
        "source_url": source,
        "front_url": image["url"],
        "back_url": None,
        "attribution": "Listen on Spotify",
    }


def selected_cover(record: dict) -> dict | None:
    cover = record.get("cover")
    if not isinstance(cover, dict):
        return None
    front = cover.get("front_url")
    if not isinstance(front, str) or not front.startswith("https://"):
        return None
    back = cover.get("back_url")
    if not isinstance(back, str) or not back.startswith("https://"):
        back = None
    source = cover.get("source_url")
    if not isinstance(source, str) or not source.startswith("https://"):
        source = front
    attribution = cover.get("attribution")
    if not isinstance(attribution, str) or not attribution.strip():
        attribution = "Selected cover."
    return {
        "provider": "Selected cover",
        "source_url": source,
        "front_url": front,
        "back_url": back,
        "attribution": attribution.strip(),
    }


def record_art(record_id: str) -> dict:
    now = time.monotonic()
    cached = ART_CACHE.get(record_id)
    if cached and cached[0] > now:
        return cached[1]
    record = public_record(record_id)
    if not record:
        return {"available": False}
    selected = selected_cover(record)
    if selected:
        result = {"available": True, **selected}
        ART_CACHE[record_id] = (now + ART_CACHE_TTL, result)
        return result
    discogs_id = approved_discogs_release(record_id) or remembered_discogs_release(record_id)
    if not discogs_id:
        discogs_id = discover_discogs_release(record)
    art = discogs_art(discogs_id) if discogs_id else None
    if discogs_id and art:
        remember_art_status(record_id, status="resolved", release_id=discogs_id,
                            provider="Discogs", source_url=art["source_url"])
    elif discogs_id:
        remember_art_status(record_id, status="no_art", release_id=discogs_id)
    art = art or musicbrainz_art(record.get("musicbrainz_release_group_mbid"))
    art = art or spotify_art(record)
    result = {"available": bool(art), **(art or {})}
    ttl = SPOTIFY_ART_TTL if result.get("provider") == "Spotify" else ART_CACHE_TTL
    ART_CACHE[record_id] = (now + ttl, result)
    return result


def bind_host(value: str) -> str:
    """Accept loopback or one literal RFC 1918-style LAN address, never a wildcard."""
    try:
        address = ip_address(value)
    except ValueError as error:
        raise ValueError("ATLAS_BIND_HOST must be a literal IPv4 address") from error
    if not isinstance(address, IPv4Address):
        raise ValueError("ATLAS_BIND_HOST must be an IPv4 address")
    if address == IPv4Address("127.0.0.1"):
        return str(address)
    if not (address.is_private and not address.is_loopback and not address.is_link_local
            and not address.is_unspecified and not address.is_multicast and not address.is_reserved):
        raise ValueError("ATLAS_BIND_HOST must be loopback or a private LAN IPv4 address")
    return str(address)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/record-art":
            record_id = parse_qs(parsed.query).get("record", [""])[0]
            if not record_id.startswith("record-") or len(record_id) > 64:
                self.send_error(400, "A valid record id is required")
                return
            body = record_art(record_id)
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            max_age = SPOTIFY_ART_TTL if body.get("provider") == "Spotify" else ART_CACHE_TTL
            self.send_header("Cache-Control", f"private, max-age={max_age}" if body.get("available") else "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()


if __name__ == "__main__":
    host = bind_host(os.getenv("ATLAS_BIND_HOST", "127.0.0.1"))
    ThreadingHTTPServer((host, 5186), Handler).serve_forever()
