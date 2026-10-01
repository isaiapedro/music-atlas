"""Apply the reviewed Batch 2 YouTube video allowlist to the genre catalogue."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
REVIEWED_AT = "2026-09-28"

PROMOTIONS = {
    "ind-lavani": ("Sulochana Chavan", "Lavani, folk dance of Maharashtra", "GgglIQeIAyw"),
    "irn-khorasan-bakhshi": ("Khorasan bakhshi musicians", "The music of the Bakhshis of Khorasan (UNESCO element film)", "TSRNKUL8MnU"),
    "irn-taziye": ("Ta'zīye practitioners", "The ritual dramatic art of Ta'zīye (UNESCO element film)", "PtMIjHteW9c"),
    "irq-iraqi-maqam": ("Iraqi Maqam musicians", "The Iraqi Maqam (UNESCO element film)", "NOrqQKL99eo"),
    "jpn-gagaku": ("Sukeyasu Shiba and the Reigakusha Ensemble", "Gagaku (UNESCO element film)", "5OA8HFUNfIk"),
    "jpn-kumiodori": ("Kumiodori performers", "Kumiodori: The Wind of Okinawa Alive on Stage", "Y-bdA4MxFFs"),
    "kaz-dombra-kuy": ("Dombra kuy musicians", "Kazakh traditional art of dombra kuy (UNESCO element film)", "f4AAkHMNBhw"),
    "ken-isukuti-dance": ("Isukha and Idakho Isukuti practitioners", "Isukuti dance (UNESCO element film)", "Zw3WSI8j8Bs"),
    "kgz-aitysh-aitys": ("Aitysh/Aitys akyns", "Aitysh/Aitys, art of improvisation (UNESCO element film)", "hKBG6JmJK0k"),
    "kgz-akyn-epic-performance": ("Sagynbay", "The Art of Akyns, Kyrgyz Epic Tellers (UNESCO element film)", "jiYQi6VQ6bc"),
    "khm-chapei-dang-veng": ("Chapei Dang Veng practitioners", "Chapei Dang Veng, Cambodia (UNESCO element film)", "Gs-HK7my51M"),
    "kor-arirang": ("Arirang singers", "Arirang, lyrical folk song in the Republic of Korea (UNESCO element film)", "Yrz49xxOC24"),
    "kor-nongak": ("Nongak community performers", "Nongak, community band music, dance and rituals (UNESCO element film)", "Kc37atMKHQs"),
    "lao-khaen-music": ("Lao khaen musicians", "Khaen music of the Lao people (UNESCO element film)", "XstshoSh6eU"),
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
            "in Batch 2 search log."
        )
        found.add(entry["id"])
    missing = sorted(set(PROMOTIONS) - found)
    if missing:
        raise SystemExit(f"catalogue entries not found: {', '.join(missing)}")
    CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"promoted {len(found)} Batch 2 YouTube examples")


if __name__ == "__main__":
    main()
