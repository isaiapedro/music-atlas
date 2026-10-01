"""Apply the reviewed Batch 7 YouTube video allowlist to the genre catalogue."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
REVIEWED_AT = "2026-09-28"

PROMOTIONS = {
    "kaz-turan-ensemble": ("TURAN", "TURAN / ER TURAN", "P1PH0Ob946I"),
    "ken-gengetone": ("MATATA", "MATATA — GENGETONE LOVE", "LrmmF9QTb4w"),
    "khm-pinn-peat": ("Pinn Peat performers", "Pinn Peat music — folk art of the Khmer people", "vykCXh27Tt8"),
    "kwt-fijiri": ("Ghalali traditional music and dance group", "Fijiri song by the Ghalali traditional music and dance group", "rx_2Ye00-kA"),
    "kwt-sawt": ("Kuwaiti Sawt performers", "Kuwaiti Sawt Music", "4eTxrdcd7GE"),
    "lbn-ataba-mijana": ("Ataba–Mijana performers", "Best of Ataba–Mijana", "eNBgy2KWdcM"),
    "mmr-hsainwain": ("Htet Arkar Myanmar Orchestra", "Introduction Performance of Htet Arkar Myanmar Orchestra (Hsaing Waing)", "tk4q6dxMPN0"),
}

UNPUBLISHED_ROSTER_CONFLICTS = {"irn-persian-pop", "irn-tasnif"}


def main() -> None:
    data = json.loads(CATALOGUE.read_text())
    found = set()
    for entry in data["entries"]:
        if entry["id"] in UNPUBLISHED_ROSTER_CONFLICTS:
            entry["youtube_examples"] = []
            entry["research"]["sample"] = "No reviewed YouTube example."
            continue
        promotion = PROMOTIONS.get(entry["id"])
        if not promotion:
            continue
        artist, title, video_id = promotion
        if artist not in entry["artists"]:
            if len(entry["artists"]) < 3:
                entry["artists"].append(artist)
        entry["youtube_examples"] = [{
            "artist": artist,
            "title": title,
            "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
            "reviewed_at": REVIEWED_AT,
        }]
        entry["research"]["sample"] = (
            "Reviewed direct YouTube example; attribution basis is recorded "
            "in Batch 7 search log."
        )
        found.add(entry["id"])
    missing = sorted(set(PROMOTIONS) - found)
    if missing:
        raise SystemExit(f"catalogue entries not found: {', '.join(missing)}")
    CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"promoted {len(found)} Batch 7 YouTube examples")


if __name__ == "__main__":
    main()
