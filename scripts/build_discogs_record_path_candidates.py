"""Build a private, resumable Discogs release-path review list for Atlas records.

The output intentionally excludes images, ratings, want/have counts and raw API
responses. It is a matching worklist, not an approved public mapping. Review a
candidate's edition manually before copying its release ID into
web/data/discogs_record_paths.json.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "web" / "data" / "genre_records.json"
DEFAULT_OUTPUT = ROOT / ".local" / "discogs" / "record_path_candidates.csv"
API = "https://api.discogs.com/database/search"
FIELDS = ("record_id", "title", "artist", "year", "candidate_count", "discogs_release_id",
          "discogs_url", "candidate_title", "candidate_artist", "candidate_year", "country",
          "format", "match_score", "status", "query_error")


def normalized(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def candidate_score(record: dict, candidate: dict) -> float:
    record_title = normalized(record["title"])
    candidate_title = normalized(candidate.get("title"))
    title = max(SequenceMatcher(None, record_title, candidate_title).ratio(),
                1.0 if record_title and record_title in candidate_title else 0.0)
    artist = max(SequenceMatcher(None, normalized(record["artist"]), normalized(candidate.get("title"))).ratio(),
                 1.0 if normalized(record["artist"]) in normalized(candidate.get("title")) else 0.0)
    year = record.get("year")
    year_score = 0.5 if year is None else (1.0 if str(year) == str(candidate.get("year") or "") else 0.0)
    return round(title * 0.58 + artist * 0.30 + year_score * 0.12, 4)


def select_candidate(record: dict, results: list[dict]) -> tuple[dict | None, float]:
    if not results:
        return None, 0.0
    candidate = max(results, key=lambda item: candidate_score(record, item))
    return candidate, candidate_score(record, candidate)


def records() -> list[dict]:
    payload = json.loads(RECORDS.read_text(encoding="utf-8"))
    unique = {}
    for group in payload.get("genres", {}).values():
        for record in group.get("records", []):
            unique.setdefault(record["id"], record)
    return [unique[key] for key in sorted(unique)]


def existing_rows(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as stream:
        return {row["record_id"]: row for row in csv.DictReader(stream)}


def search(record: dict, token: str) -> tuple[list[dict], str]:
    params = {"type": "release", "artist": record["artist"], "release_title": record["title"]}
    if record.get("year") is not None:
        params["year"] = str(record["year"])
    request = Request(API + "?" + urlencode(params), headers={
        "Authorization": f"Discogs token={token}",
        "User-Agent": "MusicAtlas/0.1 (private record-edition matching)"})
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response).get("results", []), ""
    except HTTPError as error:
        return [], f"HTTP {error.code}"
    except (URLError, TimeoutError) as error:
        return [], str(error)


def row_for(record: dict, results: list[dict], error: str) -> dict:
    candidate, score = select_candidate(record, results)
    if error:
        status = "request_error"
    elif not candidate:
        status = "no_result"
    elif score >= 0.95 and str(record.get("year") or "") == str(candidate.get("year") or ""):
        status = "strong_candidate_review_required"
    else:
        status = "needs_review"
    return {
        "record_id": record["id"], "title": record["title"], "artist": record["artist"],
        "year": record.get("year") or "", "candidate_count": len(results),
        "discogs_release_id": candidate.get("id", "") if candidate else "",
        "discogs_url": f"https://www.discogs.com{candidate['uri']}" if candidate and candidate.get("uri") else "",
        "candidate_title": candidate.get("title", "") if candidate else "",
        "candidate_artist": candidate.get("artists_sort", "") if candidate else "",
        "candidate_year": candidate.get("year", "") if candidate else "",
        "country": candidate.get("country", "") if candidate else "",
        "format": ", ".join(candidate.get("format", [])) if candidate else "",
        "match_score": score if candidate else "", "status": status, "query_error": error,
    }


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent,
                                     prefix=f".{path.name}.", delete=False) as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader(); writer.writerows(rows)
        temporary = Path(stream.name)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=0, help="maximum new API calls (0 means all)")
    parser.add_argument("--interval", type=float, default=1.1, help="minimum seconds between calls")
    parser.add_argument("--retry-errors", action="store_true")
    parser.add_argument("--background", action="store_true", help="continue the resumable pass after this shell exits")
    args = parser.parse_args()
    token = os.getenv("DISCOGS_TOKEN")
    if not token:
        raise SystemExit("Missing DISCOGS_TOKEN; put the personal access token in the environment.")
    if args.background:
        command = [sys.executable, str(Path(__file__)), "--output", str(args.output),
                   "--interval", str(args.interval)]
        if args.limit:
            command.extend(("--limit", str(args.limit)))
        if args.retry_errors:
            command.append("--retry-errors")
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True, env=os.environ.copy())
        print(json.dumps({"started": True, "pid": process.pid, "output": str(args.output)}))
        return
    prior = existing_rows(args.output)
    output = list(prior.values())
    calls = 0
    for record in records():
        previous = prior.get(record["id"])
        if previous and (previous["status"] != "request_error" or not args.retry_errors):
            continue
        if args.limit and calls >= args.limit:
            break
        started = time.monotonic()
        results, error = search(record, token)
        output = [row for row in output if row["record_id"] != record["id"]]
        output.append(row_for(record, results, error))
        calls += 1
        write_rows(args.output, sorted(output, key=lambda row: row["record_id"]))
        delay = args.interval - (time.monotonic() - started)
        if delay > 0:
            time.sleep(delay)
    summary = {"output": str(args.output), "records": len(records()), "saved": len(output), "new_calls": calls,
               "strong_candidates": sum(row["status"] == "strong_candidate_review_required" for row in output),
               "needs_review": sum(row["status"] == "needs_review" for row in output),
               "no_result": sum(row["status"] == "no_result" for row in output)}
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
