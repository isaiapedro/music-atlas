"""Create a private, dossier-driven institutional image-review queue.

The queue contains only existing public source leads for currently unillustrated
genres. It never treats a source page as a reusable image or publishes anything.
"""
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
OUT = ROOT / ".local" / "institutional_image_candidates.json"


def family(url):
    host = urlparse(url).hostname or ""
    if "ich.unesco.org" in host:
        return "UNESCO intangible heritage"
    if any(part in host for part in ("museum", "archives", "library", "folkways", "smithsonian", "culture", "gov.")):
        return "archive, museum, library, cultural institution, or public body"
    if any(part in host for part in ("edu", "ac.")):
        return "university or research institution"
    return "other cited public source"


entries = json.loads(CATALOGUE.read_text(encoding="utf-8"))["entries"]
rows = []
for entry in entries:
    if entry["status"] != "published" or entry.get("image"):
        continue
    urls = []
    for source in entry.get("sources", []):
        url = source if isinstance(source, str) else source.get("url") if isinstance(source, dict) else None
        if isinstance(url, str) and url.startswith("https://"):
            urls.append(url)
    if urls:
        rows.append({
            "genre_id": entry["id"], "country": entry["country"], "name": entry["name"],
            "leads": [{"url": url, "source_family": family(url)} for url in dict.fromkeys(urls)],
            "review_status": "pending",
            "acceptance_rule": "Accept only a practice-specific image with an explicit CC0, public-domain, CC BY, or CC BY-SA licence and an English caption or translatable source caption.",
        })
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"generated_at": date.today().isoformat(), "candidates": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {len(rows)} institutional lead records to {OUT}")
