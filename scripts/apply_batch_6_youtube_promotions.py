"""Apply the reviewed Batch 6 YouTube video allowlist to the genre catalogue."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
REVIEWED_AT = "2026-09-28"

PROMOTIONS = {
    "civ-coupe-decale": ("Coupé-Décalé performers", "Rap Ivoire vs. Coupé-Décalé", "JUW15Lbl8vs"),
    "civ-zouglou": ("Zouglou performers", "Le zouglou, une musique qui résiste", "thsgFGvTWRo"),
    "cmr-mendzan-xylophone-traditions": ("Kiss Kiss Balafons", "Kiss Kiss Balafons at a village wedding", "9_IwBcstd0U"),
    "cod-musique-moderne-zaireoise": ("Musique zaïroise moderne performers", "Anthologie de la Musique Zaïroise Moderne, Vol. 1 excerpts", "ZWmPeoXBrcI"),
    "dza-chaabi": ("Malikat el-Chaabi", "Malikat el-Chaabi | Traditional Algerian Chaabi Music", "G4WhD3ONm20"),
    "eri-guayla": ("Vittorio Bossi", "Vittorio Bossi’s Traditional Guayla Song", "LA8zR5CgqfI"),
    "eth-azmari": ("Yoseph Gedefaw", "Azmari: An Ethiopian Musician", "j8Pvgc5TYH0"),
    "gha-hiplife": ("Reggie Rockstone", "30 Years of Hiplife: A Conversation with Reggie Rockstone", "hqOfqI5LJ3w"),
    "idn-keroncong": ("Niken Salindry", "Indonesia Pusaka (Keroncong)", "CjnVW_sH7Cc"),
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
            "in Batch 6 search log."
        )
        found.add(entry["id"])
    missing = sorted(set(PROMOTIONS) - found)
    if missing:
        raise SystemExit(f"catalogue entries not found: {', '.join(missing)}")
    CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"promoted {len(found)} Batch 6 YouTube examples")


if __name__ == "__main__":
    main()
