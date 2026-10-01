"""Apply only explicitly reviewed artist evidence from a private candidate queue.

MusicBrainz search scores rank discovery results; they do not establish that an
artist represents a genre. Queue rows need approved_artists and --apply to write.
"""

import argparse
import json
import tempfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
DEFAULT_QUEUE = ROOT / ".local" / "artist_candidates.json"
MAX_ARTISTS = 3
REJECTED_PAIRS = {
    ("gnb-tina", "Tina Turner"),
    ("nga-waka", "DJ Whoo Kid"),
    ("bhr-arda", "Arda Aykut"),
}


def reviewed_artist(item):
    if not isinstance(item, dict):
        return False
    name = item.get("name")
    evidence = item.get("evidence_url")
    citation = item.get("citation")
    note = item.get("review_note")
    reviewed_at = item.get("reviewed_at")
    return (isinstance(name, str) and bool(name.strip()) and
            isinstance(note, str) and bool(note.strip()) and
            isinstance(reviewed_at, str) and bool(reviewed_at.strip()) and
            ((isinstance(evidence, str) and urlparse(evidence).scheme == "https") or
             (isinstance(citation, str) and bool(citation.strip()))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--apply", action="store_true", help="write only explicitly reviewed artists")
    args = parser.parse_args()
    if not args.queue.exists():
        print(f"No artist candidates queue found at {args.queue}")
        return

    candidates = json.loads(args.queue.read_text(encoding="utf-8")).get("candidates", [])
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    by_id = {entry["id"]: entry for entry in data["entries"]}
    ready, unresolved, already_attributed = [], 0, 0
    for row in candidates:
        genre_id = row.get("genre_id")
        entry = by_id.get(genre_id)
        if not entry or entry["status"] != "published":
            continue
        if entry.get("artists"):
            already_attributed += 1
            continue
        approved = row.get("approved_artists", [])
        if not approved:
            unresolved += 1
            continue
        if not isinstance(approved, list) or len(approved) > MAX_ARTISTS:
            raise ValueError(f"invalid approved artist list: {genre_id}")
        if not all(reviewed_artist(item) and (genre_id, item["name"]) not in REJECTED_PAIRS
                   for item in approved):
            raise ValueError(f"unreviewed or rejected artist association: {genre_id}")
        names = [item["name"].strip() for item in approved]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate reviewed artist: {genre_id}")
        ready.append((entry, approved, names))

    print(f"ready={len(ready)} unresolved={unresolved} already_attributed={already_attributed}")
    if not args.apply:
        print("Use --apply after reviewing the queued evidence and approved_artists fields.")
        return
    for entry, approved, names in ready:
        entry["artists"] = names
        entry.setdefault("research", {})["artist_evidence"] = approved
    if ready:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=CATALOGUE.parent,
                                         prefix=f".{CATALOGUE.name}.", delete=False) as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            temporary = Path(handle.name)
        temporary.replace(CATALOGUE)
    print(f"Applied reviewed artists to {len(ready)} genres")


if __name__ == "__main__":
    main()
