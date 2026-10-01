"""Create private, manually reviewed YouTube discovery batches.

The output deliberately contains search queries rather than guessed YouTube
URLs. It never calls YouTube and never changes the public catalogue.
"""
import json
import tempfile
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
BATCH_SIZE = 20


def source_url(source):
    return source if isinstance(source, str) else source.get("url")


def priority(entry):
    hosts = [urlparse(url).netloc.lower() for source in entry.get("sources", []) if (url := source_url(source))]
    if any("unesco.org" in host for host in hosts):
        return 0, "UNESCO ICH"
    if any(any(term in host for term in ("gov.", "gouv.", "go.", "ac.", "edu.", "museum", "archive", "library", "folkways")) for host in hosts):
        return 1, "institutional"
    return 2, "other source"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(value, temporary, ensure_ascii=False, indent=2)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def main():
    entries = json.loads((ROOT / "research" / "genre_catalogue.json").read_text(encoding="utf-8"))["entries"]
    candidates = []
    for entry in entries:
        if entry["status"] != "published" or entry.get("youtube_examples"):
            continue
        rank, source_kind = priority(entry)
        candidates.append({
            "genre_id": entry["id"], "genre": entry["name"], "country": entry["country"],
            "source_kind": source_kind,
            "source_urls": [url for source in entry.get("sources", []) if (url := source_url(source))],
            "manual_search_query": f'{entry["name"]} {"UNESCO" if source_kind == "UNESCO ICH" else "official"} YouTube',
            "fallback_plan": [
                "Search the exact source/element title plus its publisher or channel name.",
                "Retry with the entry's local-script name, aliases, transliterations, and source-language title from its country dossier.",
                "Search the cited cultural institution, archive, label, broadcaster, or official artist channel for a full-performance or element film.",
                "For a collective practice, search for a source-described bearer group or performance role rather than forcing an individual artist name.",
                "Check whether an official upload exists but embedding is disabled; record it as link-only, not an app embed.",
                "If no exact, rights-holder or institutional match is found after these checks, record no_match with queries, sources, date, and reason; do not substitute a country-level or instrument-only video.",
            ],
            "_rank": rank,
        })
    candidates.sort(key=lambda row: (row["_rank"], row["country"], row["genre"].casefold()))
    for row in candidates:
        row.pop("_rank")
    batches = [candidates[index:index + BATCH_SIZE] for index in range(0, len(candidates), BATCH_SIZE)]
    output = {"generated_at": date.today().isoformat(), "batch_size": BATCH_SIZE, "total_candidates": len(candidates), "batches": batches}
    path = ROOT / ".local" / "youtube_search_batches.json"
    write(path, output)
    print(f"wrote {len(batches)} private batches / {len(candidates)} candidates to {path}")


if __name__ == "__main__":
    main()
