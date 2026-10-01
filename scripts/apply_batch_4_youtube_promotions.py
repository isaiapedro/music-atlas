"""Apply the reviewed Batch 4 YouTube video allowlist to the genre catalogue."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
REVIEWED_AT = "2026-09-28"

PROMOTIONS = {
    "cpv-funana": ("Funaná performers", "Dancing Funaná in Praia", "_e1Pp6jkNV0"),
    "eth-tizita": ("Meklit", "Meklit feat. Brandee Younger — Tizita", "RQ05UI0cAlc"),
    "gha-adowa": ("Adowa performers", "Adowa Dance — traditional dance, music and song", "VnSQihGFUWY"),
    "gha-kpanlogo": ("Kpanlogo performers", "Kpanlogo Dance", "qfmlc6Tp870"),
    "jpn-city-pop": ("nocco", "nocco — Best Songs Selection", "4rgh4q7mW9U"),
    "lby-maluf": ("Hassan Araibi", "Tarraz Ar-Rayhaan — traditional Libyan Arabic music", "uUVqDVExol0"),
    "lka-kandyan-drumming": ("Kandyan drummers", "Traditional Kandyan Dance & Drumming", "4Ldq1oyHEz0"),
    "lso-famo": ("Famo musicians", "The Accordion Wars: Famo music and gang violence in Lesotho", "iYEDo3Tv00g"),
}


def main() -> None:
    data = json.loads(CATALOGUE.read_text())
    found = set()
    for entry in data["entries"]:
        promotion = PROMOTIONS.get(entry["id"])
        if not promotion:
            continue
        artist, title, video_id = promotion
        if artist not in entry["artists"]:
            if len(entry["artists"]) >= 3:
                raise SystemExit(f"representative limit reached: {entry['id']}")
            entry["artists"].append(artist)
        entry["youtube_examples"] = [{
            "artist": artist,
            "title": title,
            "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
            "reviewed_at": REVIEWED_AT,
        }]
        entry["research"]["sample"] = (
            "Reviewed direct YouTube example; attribution basis is recorded "
            "in Batch 4 search log."
        )
        found.add(entry["id"])
    missing = sorted(set(PROMOTIONS) - found)
    if missing:
        raise SystemExit(f"catalogue entries not found: {', '.join(missing)}")
    CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"promoted {len(found)} Batch 4 YouTube examples")


if __name__ == "__main__":
    main()
