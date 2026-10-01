"""Apply the reviewed Batch 8 YouTube video allowlist to the genre catalogue."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
REVIEWED_AT = "2026-09-28"
PROMOTIONS = {
    "mys-malaysian-popular-music-1950s-1990s": ("P. Ramlee", "Getaran Jiwa — P. Ramlee", "6L1_empGNvg"),
    "nga-fuji": ("Adewale Ayuba", "Adewale Ayuba — Fuji Musik", "sLh6L-9ZIRE"),
    "phl-manila-sound-1980s": ("Manila Sound performers", "OPM 70s and 80s | Manila Sound", "hHMbX7gc72o"),
    "qat-fijiri": ("Ghalali traditional music and dance group", "Fijiri song by the Ghalali traditional music and dance group", "rx_2Ye00-kA"),
    "qat-arda": ("Qatar Navigation (Milaha)", "Ardha Qatar’s traditional folk dance", "qqgWUhbllYU"),
    "sau-fijiri": ("Ghalali traditional music and dance group", "Fijiri song by the Ghalali traditional music and dance group", "rx_2Ye00-kA"),
    "sen-mbalax": ("Youssou N'Dour", "Fay Bor — Youssou N'Dour", "gFqWV7AVKwY"),
    "sen-yela": ("Batch Gueye", "YELA — Batch Gueye", "-jKDnNkvmA8"),
}

def main() -> None:
    data = json.loads(CATALOGUE.read_text())
    found = set()
    for entry in data["entries"]:
        promotion = PROMOTIONS.get(entry["id"])
        if not promotion:
            continue
        artist, title, video_id = promotion
        if artist not in entry["artists"] and len(entry["artists"]) < 3:
            entry["artists"].append(artist)
        if artist not in entry["artists"]:
            raise SystemExit(f"representative not in roster: {entry['id']}")
        entry["youtube_examples"] = [{"artist": artist, "title": title, "youtube_url": f"https://www.youtube.com/watch?v={video_id}", "reviewed_at": REVIEWED_AT}]
        entry["research"]["sample"] = "Reviewed direct YouTube example; attribution basis is recorded in Batch 8 search log."
        found.add(entry["id"])
    missing = sorted(set(PROMOTIONS) - found)
    if missing:
        raise SystemExit(f"catalogue entries not found: {', '.join(missing)}")
    CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"promoted {len(found)} Batch 8 YouTube examples")

if __name__ == "__main__":
    main()
