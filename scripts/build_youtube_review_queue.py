"""Create a private, artist-first queue for manually reviewing YouTube examples.

YouTube links are reviewed one at a time. The script does not call or scrape
YouTube: platform search, channel ownership, and genre fit need human review.
"""
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
        if genre["status"] != "published" or not genre["artists"]:
            continue
        represented = {example["artist"] for example in genre["youtube_examples"]}
        missing = [artist for artist in genre["artists"] if artist not in represented]
        if not missing:
            continue
        candidates.append({
            "genre_id": genre["id"], "genre": genre["name"],
            "artists": [{"name": artist, "query": f"{artist} {genre['name']} official"} for artist in missing],
            "review_requirements": [
                "Prefer an Official Artist Channel, the artist's verified channel, or a rights-holder/label channel.",
                "Confirm the specific video represents the mapped genre; a title or algorithmic recommendation is insufficient.",
                "Record artist, title, canonical https://www.youtube.com/watch?v=<11-character-id> URL, and review date.",
                "Use YouTube's embed only; do not download, copy, or re-host video or audio.",
            ],
        })
    output = {"generated_at": date.today().isoformat(), "provider": "manual YouTube review", "candidates": candidates}
    path = ROOT / ".local" / "youtube_review_queue.json"
    write(path, output)
    print(f"wrote {len(candidates)} private YouTube review rows to {path}")


if __name__ == "__main__":
    main()
