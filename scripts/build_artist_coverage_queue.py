"""Create the private evidence queue for the three-representative artist target."""
import json
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(value, temporary, ensure_ascii=False, indent=2)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def main():
    catalogue = json.loads((ROOT / "research" / "genre_catalogue.json").read_text(encoding="utf-8"))
    candidates = []
    for genre in catalogue["entries"]:
        if genre["status"] != "published" or len(genre["artists"]) >= 3:
            continue
        candidates.append({
            "genre_id": genre["id"], "genre": genre["name"], "country": genre["country"],
            "current_representatives": genre["artists"], "needed": 3 - len(genre["artists"]),
            "acceptable_representatives": ["performer", "composer", "ensemble", "lineage bearer", "documented community bearer"],
            "admission_rule": "Add only a genre-specific representative supported by a specialist, community, archival, label, or artist source; do not use a search result or generic national association alone.",
        })
    output = {"generated_at": date.today().isoformat(), "target_per_genre": 3, "candidates": candidates}
    path = ROOT / ".local" / "artist_coverage_queue.json"
    write(path, output)
    print(f"wrote {len(candidates)} private artist-coverage rows to {path}")


if __name__ == "__main__":
    main()
