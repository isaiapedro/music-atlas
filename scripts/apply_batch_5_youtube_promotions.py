"""Apply the reviewed Batch 5 YouTube video allowlist to the genre catalogue."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
REVIEWED_AT = "2026-09-28"

PROMOTIONS = {
    "pak-khattak-dance-music": ("Khattak dance performers", "Pashto Khattak Dance — Best Dhol Performance", "Lg_PDQ0-zRM"),
    "pak-mahiya": ("Arif Lohar", "Wagdi Ae Raavi (Mahiya)", "IwKEjk4r41E"),
    "sds-dinka-song-traditions": ("Dinka song practitioners", "Diet ke Jieeng ne Cueny Thudan", "-n-zW-VaF60"),
    "sen-taasu": ("Taasu women ritual poets", "Taasu (Tassou) Women Ritual Poets of Senegal", "uIZOqyBDYXQ"),
    "sle-bubu-music": ("Bubu musicians", "Bubu music in Sierra Leone", "js0UgXWnzC8"),
    "swz-sibhaca": ("Sibhaca dancers", "Sibhaca performance", "W1j13DB6Ovg"),
    "tls-tebe": ("Tebe practitioners", "Tebe traditional of Timor-Leste", "Zws_5LH69wM"),
    "tur-arabesk": ("İbrahim Tatlıses", "Arabesk — İbrahim Tatlıses", "sTMZEfP4CYc"),
    "twn-beiguan-music": ("Beiguan performers", "Traditional Beiguan Music Performance", "GgCIVLj8wWI"),
    "vnm-cai-luong": ("Cải lương performers", "The History of Cải Lương", "wej1Imjfisg"),
    "zaf-isicathamiya": ("Ladysmith Black Mambazo", "Ladysmith Black Mambazo", "wXbksUHTG20"),
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
            "in Batch 5 search log."
        )
        found.add(entry["id"])
    missing = sorted(set(PROMOTIONS) - found)
    if missing:
        raise SystemExit(f"catalogue entries not found: {', '.join(missing)}")
    CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"promoted {len(found)} Batch 5 YouTube examples")


if __name__ == "__main__":
    main()
