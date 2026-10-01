"""Make one explicitly authorized Parse RYM request and save the raw response privately."""
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://api.parse.bot/scraper/4543201b-0c81-4415-b1a4-83478db54412"
ALLOWED_ENDPOINTS = {"get_charts", "get_artist_details", "get_release_details", "search", "get_genres", "get_genre_details"}
ENDPOINT_PARAMETERS = {
    "get_charts": {"page", "year", "location", "chart_type", "media_type"},
    "get_artist_details": {"url"},
    "get_release_details": {"url"},
    "search": {"query", "search_type"},
    "get_genres": set(),
    "get_genre_details": {"url"},
}


def build_request(endpoint, parameters, api_key):
    if endpoint not in ALLOWED_ENDPOINTS:
        raise ValueError(f"Unsupported endpoint: {endpoint}")
    url = f"{BASE}/{endpoint}?{urllib.parse.urlencode(parameters)}"
    return urllib.request.Request(url, headers={"X-API-Key": api_key, "Accept": "application/json",
                                                "User-Agent": "MusicAtlas-RYMPilot/1.0"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("endpoint", choices=sorted(ALLOWED_ENDPOINTS))
    parser.add_argument("--param", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--api-key-env", default="PARSE_API_KEY")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-live-request", action="store_true",
                        help="Required acknowledgement: this makes exactly one potentially billable request")
    args = parser.parse_args()
    if not args.allow_live_request:
        raise SystemExit("Refusing live request without --allow-live-request")
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"Missing API key environment variable: {args.api_key_env}")
    parameters = {}
    for item in args.param:
        if "=" not in item:
            raise SystemExit(f"Invalid --param {item!r}; expected KEY=VALUE")
        key, value = item.split("=", 1)
        if key not in ENDPOINT_PARAMETERS[args.endpoint]:
            allowed = ", ".join(sorted(ENDPOINT_PARAMETERS[args.endpoint]))
            raise SystemExit(f"Unsupported parameter {key!r} for {args.endpoint}; documented parameters: {allowed}")
        parameters[key] = value
    request = build_request(args.endpoint, parameters, api_key)
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = json.load(response)
    output = args.output or ROOT / ".local/rym/raw" / f"parse-{args.endpoint}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
