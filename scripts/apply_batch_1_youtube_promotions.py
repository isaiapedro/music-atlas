"""Apply the reviewed Batch 1 YouTube video allowlist to the genre catalogue."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
REVIEWED_AT = "2026-09-28"

PROMOTIONS = {
    "afg-rubab-playing": ("Ustad Amir Mohammad and Ustad Attaie", "Ustad Amir Mohammad with Ustad Attaie on Afghan rubab", "K2JnXX7MKLU"),
    "ago-semba": ("Bonga, Paulo Flores and Yuri da Cunha", "Bonga, Paulo Flores & Yuri da Cunha live: semba concert", "17y2aOrNk2o"),
    "are-al-ayyala": ("Al-Ayyala performers", "Al-Ayyala (Embassy Festival performance)", "jFvGSKchbE8"),
    "arm-duduk-music": ("Armenian duduk musicians", "Duduk and its music (UNESCO element film)", "X8CWEiK6PkI"),
    "bfa-balafon-music": ("Lars Pistorius", "Farafina Bolomakoté: traditional balafon music from Burkina Faso", "uzuujQI5290"),
    "bhr-fjiri": ("Ghalali traditional music and dance group", "Fijiri", "rx_2Ye00-kA"),
    "btn-drametse-ngacham": ("Drametse Ngacham practitioners", "Mask dance of the drums from Drametse (UNESCO element film)", "k4qFI51_JRw"),
    "bwa-dikopelo": ("Bakgatla ba Kgafela Dikopelo practitioners", "Dikopelo folk music of Bakgatla ba Kgafela (UNESCO element film)", "nYWQFf_n3xU"),
    "caf-aka-polyphonic-singing": ("Aka polyphonic singers", "Polyphonic singing of the Aka Pygmies (UNESCO element film)", "ApZVPIP1uhg"),
    "chn-nanyin": ("Nanyin practitioners", "Nanyin (UNESCO element film)", "x0EXIrADaIU"),
    "civ-gbofe": ("Afounkaha Tagbana Gbọfẹ̀ practitioners", "The Gbofe of Afounkaha (UNESCO element film)", "IFoho4oD7Ic"),
    "civ-zaouli": ("Manfla Zaouli performers", "Zaouli de Manfla", "jZ572yLH9sc"),
    "cmr-mvet-oyeng": ("Ekang Mvet Oyeng practitioners", "Mvet Oyeng (UNESCO element film)", "ryu92M0LKso"),
    "cog-mvet-oyeng": ("Ekang Mvet Oyeng practitioners", "Mvet Oyeng (UNESCO element film)", "ryu92M0LKso"),
    "cpv-morna": ("Morna practitioners", "Morna, musical practice of Cabo Verde (UNESCO element film)", "2e0wCkWeoVs"),
}


def main() -> None:
    data = json.loads(CATALOGUE.read_text())
    found = set()
    for entry in data["entries"]:
        promotion = PROMOTIONS.get(entry["id"])
        if not promotion:
            continue
        artist, title, video_id = promotion
        # Morna already has the allowed three named representatives.  The
        # institutional element film remains the example; its representative
        # label is an existing source-backed morna artist rather than adding a
        # fourth generic group label.
        if entry["id"] == "cpv-morna":
            artist = "Cesária Évora"
        if artist not in entry["artists"]:
            entry["artists"] = (entry["artists"] + [artist])[:3]
        entry["youtube_examples"] = [{
            "artist": artist,
            "title": title,
            "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
            "reviewed_at": REVIEWED_AT,
        }]
        entry["research"]["sample"] = (
            "Reviewed direct YouTube example; attribution basis is recorded "
            "in Batch 1 search log."
        )
        found.add(entry["id"])
    missing = sorted(set(PROMOTIONS) - found)
    if missing:
        raise SystemExit(f"catalogue entries not found: {', '.join(missing)}")
    CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"promoted {len(found)} Batch 1 YouTube examples")


if __name__ == "__main__":
    main()
