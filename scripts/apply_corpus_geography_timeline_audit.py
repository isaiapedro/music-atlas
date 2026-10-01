"""Apply the reviewed 2026-09-28 cross-border and approximate-period corrections."""
import json
import re
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"


PERIODS = {
    "cpv-funana": (1900, None, "Early twentieth-century emergence; name established by the 1960s–1970s"),
    "afg-kabuli-ghazal": (1920, None, "Spread beyond Kabul from the 1920s; approximate prominence window"),
    "afg-naghma-ye-kashal": (1970, None, "Documented transmission by the 1970s; earlier onset unresolved"),
    "caf-zokela": (1980, 1999, "Prominent from the early 1980s through the documented early-1990s scene"),
    "mng-urtiin-duu": (1200, None, "Documented in literature by the thirteenth century; contemporary practice documented"),
    "tjk-shashmaqom": (1000, None, "Evolved over more than ten centuries; contemporary safeguarding documented"),
    "uzb-shashmaqom": (1000, None, "Evolved over more than ten centuries; contemporary safeguarding documented"),
    "cmr-mendzan-xylophone-traditions": (1940, 1979, "Documented transformation from the 1940s through the 1970s"),
    "cod-musique-moderne-zaireoise": (1940, 1999, "Documented guitar-based urban practice from the 1940s; later endpoint approximate"),
    "irn-tasnif": (1800, None, "Documented nineteenth-century popularity and later revival"),
    "btn-rigsar": (1970, None, "Developed around the late 1960s–1970s; later popularity documented"),
    "dza-chaabi": (1900, None, "Early twentieth-century emergence; approximate decade"),
    "ken-taarab": (1870, None, "Late nineteenth-century coastal development; continuing practice documented"),
    "tza-taarab": (1870, None, "Late nineteenth-century coastal development; continuing practice documented"),
}

# These are documentary or prominence anchors already stated in the reviewed
# catalogue/dossiers. They are deliberately rounded to decades.
DOCUMENTED_STARTS = {
    "nga-ogene": 1970, "sen-taasu": 1970, "mli-wassoulou": 1980,
    "bgd-bhatiyali": 1950, "bgd-bhawaiya": 1950, "bgd-rabindra-sangeet": 1900,
    "pak-mahiya": 1950, "pak-khattak-dance-music": 1950,
    "npl-panchai-baja": 2010, "npl-lok-dohori": 2000,
    "idn-angklung": 1930, "mar-ahwash": 1950, "mar-aissawa": 1960,
    "tur-mevlevi-ayin": 1270, "idn-keroncong": 1500,
    "cpv-morna": 1800, "cpv-batuque": 1800, "lao-lam-khap": 1970,
    "vnm-cheo": 1700, "sdn-zar-tambura": 1990, "phl-hudhud-chants": 1990,
    "tcd-ngambaye-vocal-music": 1900, "tha-lam-isan": 1990,
    "gnq-mvet-oyeng": 2010, "gnq-balele": 2010,
    "ind-bhangra": 1950, "aze-azerbaijani-mugham": 1900,
    "gha-highlife": 1800, "gha-kpanlogo": 1960, "gha-adowa": 1900,
    "mli-tuareg-guitar": 1970, "civ-zaouli": 1950,
    "npl-newar-dhimay": 1900, "lka-baila": 1500, "idn-saman": 1900,
    "vnm-vi-giam": 1900, "vnm-quan-ho": 1900, "vnm-ca-tru": 1900,
    "vnm-don-ca-tai-tu": 1900, "vnm-cai-luong": 1910,
    "eth-zema": 1900, "eth-azmari": 1900, "ken-isukuti": 1900,
    "uga-kidandali": 1960, "dza-ahellil": 1900, "dza-imzad": 1900,
    "mar-aita": 1900, "egy-semsemiah": 1900, "tur-asiklik": 1900,
    "aze-ashiq": 1900, "lby-maluf": 1900,
    "mrt-mauritanian-bardic-tradition": 1900, "chn-nanyin": 1900,
    "lka-rukada-natya": 1900, "ben-gelede-chants": 1900,
    "tgo-gelede-chants": 1900, "gmb-kankurang-music": 1900,
    "sen-kankurang-music": 1900, "gin-sosso-bala": 1900,
    "mli-imzad-music": 1900, "ner-imzad-music": 1900, "civ-gbofe": 1900,
    "moz-chopi-timbila": 1900, "zmb-mooba": 1900,
    "zwe-mbende-jerusarema": 1900, "pak-boreendo-music": 1900,
    "zaf-isicathamiya": 1900, "gnb-gumbe": 1970, "prk-arirang": 1900,
    "tkm-kushtdepdi": 1900, "tkm-dutar-music-and-singing": 1900,
    "tkm-gorogly-epic-art": 1900, "gab-mvet-oyeng": 1900,
    "lso-famo": 1920, "afg-rubab-playing": 1900,
    "geo-georgian-polyphonic-singing": 1900, "yem-sanaa-song": 1900,
    "brn-sung-pantun": 1900, "kor-arirang": 1900,
    "mac-cantonese-naamyam": 1900, "caf-aka-polyphonic-singing": 1900,
    "com-taarab": 1870, "sau-alardah-alnajdiyah": 1900,
    "mng-morin-khuur": 1900, "mng-khoomei": 1900, "aze-meyxana": 1900,
    "kaz-dombra-kuy": 1900, "swz-sibhaca": 1900, "cmr-mvet-oyeng": 1900,
    "lao-khaen-music": 1900, "rwa-intore": 1900, "vnm-nha-nhac": 1900,
    "ago-semba": 1950, "are-al-ayyala": 1900, "bfa-balafon-music": 1900,
    "bwa-dikopelo": 1900, "irq-iraqi-maqam": 1900, "kwt-fijiri": 1900,
    "psx-dabkeh-accompanying-folk-song-and-instrumental-music": 1900,
    "psx-ataba-mijana": 1900, "tur-kl-k": 1900,
    "egy-semsemiah-music": 1900, "jor-as-samer": 1900,
    "stp-tchiloli-performance-music": 1500, "arm-duduk-music": 1900,
    "cyp-byzantine-chant": 1900, "ken-isukuti-dance": 1900,
    "lka-nadagam-song": 1800, "tun-tw-yef-of-ghbonten": 1900,
    "hkg-cantonese-opera": 1900, "nam-aixan-ancestral-music": 1900,
    "cog-mvet-oyeng": 1900, "omn-al-bar-ah": 1900, "qat-arda": 1900,
    "qat-fijiri": 1900, "kgz-aitysh-aitys": 1900,
    "gab-gabonese-shelved-harp": 1620, "nam-ovambo-chihumba": 1990,
    "tcd-gourd-resonated-xylophone-lead": 1990, "bhr-fjiri": 1900,
}

PRE_1900_HINTS = re.compile(
    r"\b(ancient|centuries|century-old|traditional|ritual|ceremonial|devotional|"
    r"court tradition|classical tradition|folk tradition|oral tradition|epic tradition|"
    r"heritage tradition|monastic|indigenous)\b", re.I
)
PRESENT_HINTS = re.compile(
    r"\b(current|currently|continuing|continues|contemporary|ongoing|living|remain(?:s)? active|"
    r"still practi[cs]ed|today|present-day|intergenerational transmission)\b", re.I
)


def audit_timeline(entry):
    """Add broad, labelled estimates without turning them into exact origins."""
    research = entry.setdefault("research", {})
    text = " | ".join(str(value) for value in (
        entry.get("kind", ""), entry.get("start_label", ""), entry.get("note", ""),
        research.get("period", ""), research.get("continuity", ""),
    ))
    if entry.get("active_from") is None:
        start = DOCUMENTED_STARTS.get(entry["id"])
        if start is not None:
            entry["active_from"] = start
            entry["start_label"] = f"Documented or prominent by the {start // 10 * 10}s (approx.)"
        elif PRE_1900_HINTS.search(text):
            entry["active_from"] = 1900
            entry["start_label"] = "Established by 1900 (broad editorial estimate; earlier onset unresolved)"
        if entry.get("active_from") is not None:
            research["timeline_audit"] = (
                "Broad display anchor derived from reviewed descriptive or documentary wording. "
                "It is not an exact origin or a claim of uninterrupted continuity."
            )

    source_text = json.dumps(entry.get("sources", []), ensure_ascii=False)
    negative_end = re.search(r"\b(extinct|continuity unresolved|does not prove.*continuity|no post-)\b", text, re.I)
    if entry["id"] == "lka-nadagam-song":
        entry["active_to"] = 1950
        entry["research"]["timeline_audit"] = (
            "Broad nineteenth-century emergence and mid-twentieth-century endpoint estimate; "
            "the cited inventory describes the folk-opera form as extinct."
        )
    if entry.get("active_to") is not None:
        entry["timeline_end_status"] = "ended"
    elif PRESENT_HINTS.search(text) or ("ich.unesco.org" in source_text and not negative_end):
        entry["timeline_end_status"] = "present"
    else:
        entry["timeline_end_status"] = "unknown"

    for area in entry.get("associated_areas", []):
        area_text = f"{area.get('start_label', '')} | {area.get('note', '')}"
        area["timeline_end_status"] = (
            "ended" if area.get("active_to") is not None
            else "present" if PRESENT_HINTS.search(area_text)
            else "unknown"
        )


def write_json(path, value):
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=f".{path.name}.", delete=False) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    temporary.replace(path)


def main():
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    entries = {entry["id"]: entry for entry in data["entries"]}
    missing = set(PERIODS) - set(entries)
    assert not missing, f"missing audited records: {sorted(missing)}"

    for ident, (start, end, label) in PERIODS.items():
        entry = entries[ident]
        entry["active_from"] = start
        entry["active_to"] = end
        entry["start_label"] = label
        entry["research"]["timeline_audit"] = (
            "Approximate visibility or prominence endpoints derived from the cited source wording; "
            "they do not assert exact origin, extinction, or uninterrupted continuity."
        )

    urtiin = entries["mng-urtiin-duu"]
    china = next(area for area in urtiin["associated_areas"] if area["country"] == "CHN")
    china["active_from"] = 1200
    china["start_label"] = "Documented by the thirteenth century; contemporary Inner Mongolian practice documented"
    china["note"] = (
        "UNESCO identifies literary documentation from the thirteenth century and living regional styles "
        "in Inner Mongolia. The endpoints are approximate and do not claim uninterrupted continuity."
    )

    gelede = entries["ben-gelede-chants"]
    if not any(area["country"] == "NGA" for area in gelede["associated_areas"]):
        gelede["associated_areas"].append({
            "country": "NGA",
            "map_scope": "country",
            "regions": [],
            "relationship": "practice",
            "active_from": None,
            "active_to": None,
            "start_label": "Living Yoruba-Nago practice; historical onset unresolved",
            "note": "UNESCO documents the cross-border Gélédé heritage in Nigeria, Benin and Togo.",
            "sources": ["https://ich.unesco.org/en/RL/00002"],
            "reviewed_at": "2026-09-28",
        })

    for ident, merged_into in {
        "gmb-kankurang-ceremonial-song-and-drumming": "gmb-kankurang-music",
        "sen-kankurang-ceremonial-song-and-drumming": "sen-kankurang-music",
    }.items():
        duplicate = entries[ident]
        duplicate["status"] = "merged_duplicate"
        duplicate["research"]["merged_into"] = merged_into
        duplicate["research"]["risk"] = "Removed from the public build as a duplicate of the same UNESCO practice."

    for entry in data["entries"]:
        if entry["status"] == "published":
            audit_timeline(entry)

    write_json(CATALOGUE, data)


if __name__ == "__main__":
    main()
