"""Replace promoted placeholder citations with public bibliography and dossier locators.

Only records whose sole citation is the promotion placeholder are changed.
The exact acquired passage and claim remain in the private country dossier.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
DOSSIERS = ROOT / "research" / "countries"
PLACEHOLDER = "Local dossier source; see private evidence record."
BIBLIOGRAPHY = {
    "garland-african-handbook-2008": "Ruth M. Stone (ed.), The Garland Handbook of African Music, 2nd ed., Routledge, 2008",
    "folkways-jpn-semiclassical-folk-1974": "Smithsonian Folkways, Japan: Semiclassical and Folk Music, UNESCO Collection UNES08016, 1974, liner notes",
    "folkways-kor-folk-classical-1951": "Smithsonian Folkways, Folk and Classical Music of Korea, FW04424, 1951, liner notes",
    "folkways-kor-vocal-instrumental-1965": "Smithsonian Folkways, Korea: Vocal and Instrumental Music, UNESCO Collection UNES08010, 1965, liner notes",
    "unesco-masterpieces-2001-2005": "UNESCO, Masterpieces of the Oral and Intangible Heritage of Humanity: Proclamations 2001, 2003 and 2005, 2006",
    "bloomsbury-mena-genres-v10-2015": "Richard C. Jankowsky (vol. ed.), Bloomsbury Encyclopedia of Popular Music of the World, vol. X: Genres: Middle East and North Africa, Bloomsbury Academic, 2015",
    "garland-southeast-asia-v4-1998": "Terry E. Miller and Sean Williams (eds.), The Garland Encyclopedia of World Music, vol. 4: Southeast Asia, Garland Publishing, 1998",
    "turkic-soundscapes-2018": "Razia Sultanova and Megan Rancier (eds.), Turkic Soundscapes: From Shamanic Voices to Hip-Hop, Routledge, 2018",
}


def dossier_candidates():
    rows = {}
    for path in sorted(DOSSIERS.glob("*.json")):
        for candidate in json.loads(path.read_text(encoding="utf-8")).get("candidates", []):
            rows[candidate.get("publication_id") or candidate["id"]] = candidate
    return rows


def source_citations(candidate):
    citations = []
    for source in candidate.get("sources", []):
        identifier = source.get("acquired_document_id")
        if identifier not in BIBLIOGRAPHY:
            raise ValueError(f"Unknown bibliography ID: {identifier}")
        locator = source.get("page") or source.get("section")
        if not locator:
            raise ValueError(f"Missing exact locator: {candidate['id']} / {identifier}")
        citations.append({"citation": f"{BIBLIOGRAPHY[identifier]}, {locator}."})
    if not citations:
        raise ValueError(f"No dossier source: {candidate['id']}")
    return citations


def main():
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    dossiers = dossier_candidates()
    changed = 0
    for entry in data["entries"]:
        if entry.get("sources") != [{"citation": PLACEHOLDER}]:
            continue
        if entry["id"] not in dossiers:
            raise ValueError(f"Missing dossier: {entry['id']}")
        entry["sources"] = source_citations(dossiers[entry["id"]])
        changed += 1
    if changed:
        CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"replaced {changed} promotion placeholder citations")


if __name__ == "__main__":
    main()
