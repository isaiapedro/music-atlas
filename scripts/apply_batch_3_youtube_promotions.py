"""Apply the reviewed Batch 3 YouTube video allowlist to the genre catalogue."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
REVIEWED_AT = "2026-09-28"

PROMOTIONS = {
    "ner-imzad-music": ("Tuareg imzad practitioners", "Imzad music (UNESCO element film)", "J_0EdwuC9og"),
    "nga-highlife": ("Chief Oliver De Coque", "Chief Oliver De Coque — Identity", "hodxm2Om0bE"),
    "omn-al-bar-ah": ("Al-Bar'ah practitioners", "Al-Bar'ah, Oman (UNESCO element film)", "87h_TNLHRGY"),
    "pak-qawwali": ("Nusrat Fateh Ali Khan", "All Time Best Qawwalies — Nusrat Fateh Ali Khan", "FIzjqBtb_xo"),
    "phl-hudhud-chants": ("Ifugao Hudhud chanters", "Hudhud chants of the Ifugao (UNESCO element film)", "qDImhwTKMOk"),
    "prk-arirang": ("Eun Hee-ji", "Arirang in the North Korean singing style", "lQVUrfdpobA"),
    "psx-dabkeh-accompanying-folk-song-and-instrumental-music": ("Palestinian Dabkeh performers", "Palestinian Dabkeh performed in London", "BZpCQX9ablA"),
    "rwa-intore": ("Intore dancers", "Intore dance (UNESCO element film)", "fD_rJi8lbBk"),
    "sau-alardah-alnajdiyah": ("Alardah Alnajdiyah performers", "Alardah Alnajdiyah (UNESCO element film)", "0dinIKjrgW0"),
    "sen-kankurang-music": ("Manding Kankurang practitioners", "The Kankurang, Manding Initiatory Rite (UNESCO element film)", "3gNtkPUuxl0"),
    "stp-tchiloli-performance-music": ("Tchiloli performers", "Tchiloli, théâtre vivant de Sao Tomé-et-Principe", "vAIjn4kxJCI"),
    "syr-al-qudoud-al-halabiya": ("Al-Qudoud al-Halabiya performers", "Al-Qudoud al-Halabiya (UNESCO element film)", "a5UjbNtY3Nc"),
    "tha-nora": ("Nora performers", "Nora, dance drama in southern Thailand (UNESCO element film)", "YOZVmLS9N0o"),
    "tjk-falak": ("Rahmatullo Hoshimov", "Rahmatullo Hoshimov — Falak", "ndlgoHnkL5A"),
    "tjk-shashmaqom": ("Shashmaqom musicians", "Shashmaqom music (UNESCO element film)", "ZagFXO6uVXE"),
    "tkm-dutar-music-and-singing": ("Turkmen dutar musicians", "Dutar music and singing (UNESCO element film)", "LFSJ2n7zPeM"),
    "tkm-gorogly-epic-art": ("Gorogly epic performers", "Epic art of Gorogly (UNESCO element film)", "LDtW7evOGT8"),
    "tkm-kushtdepdi": ("Kushtdepdi performers", "Kushtdepdi (UNESCO element film)", "en3bW5EVJGs"),
}

# A reviewed example must name the performer shown. Nigerian highlife already
# had three representatives, so replace the unlinked third slot with the
# directly evidenced Oliver De Coque rather than exceeding the app-wide limit.
REPLACEMENTS = {"nga-highlife": "Stephen Osita Osadebe"}


def main() -> None:
    data = json.loads(CATALOGUE.read_text())
    found = set()
    for entry in data["entries"]:
        promotion = PROMOTIONS.get(entry["id"])
        if not promotion:
            continue
        artist, title, video_id = promotion
        if artist not in entry["artists"]:
            if len(entry["artists"]) < 3:
                entry["artists"].append(artist)
            elif entry["id"] in REPLACEMENTS:
                previous = REPLACEMENTS[entry["id"]]
                entry["artists"].remove(previous)
                entry["artists"].append(artist)
            else:
                raise SystemExit(f"representative limit reached: {entry['id']}")
        entry["youtube_examples"] = [{
            "artist": artist,
            "title": title,
            "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
            "reviewed_at": REVIEWED_AT,
        }]
        entry["research"]["sample"] = (
            "Reviewed direct YouTube example; attribution basis is recorded "
            "in Batch 3 search log."
        )
        found.add(entry["id"])
    missing = sorted(set(PROMOTIONS) - found)
    if missing:
        raise SystemExit(f"catalogue entries not found: {', '.join(missing)}")
    CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"promoted {len(found)} Batch 3 YouTube examples")


if __name__ == "__main__":
    main()
