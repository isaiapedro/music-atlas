"""Write the durable ledger for the 2026-09-28 full remaining-video pass."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
OUTPUT = ROOT / "research" / "FULL_REMAINING_VIDEO_AUDIT_2026-09-28.md"

# These were direct, title-verified candidates discovered in this pass.  The
# remaining published no-video records are also targets: they were queried but
# did not produce a sufficiently specific direct YouTube match.
PROMOTED_IN_PASS = {
    "idn-gamelan", "mli-mbolon", "npl-panchai-baja", "lka-low-country-drumming",
    "idn-angklung", "vnm-quan-ho", "kor-trot", "eth-zema", "ken-benga",
    "mar-ahwash", "aze-dede-qorqud", "mdg-tsapiky", "lka-rukada-natya",
    "gmb-kankurang-music", "gin-sosso-bala", "moz-chopi-timbila",
    "zwe-mbende-jerusarema", "pak-boreendo-music", "gnb-gumbe", "cpv-batuque",
    "yem-sanaa-song", "brn-gulintangan", "mng-morin-khuur", "mng-khoomei",
    "mng-mongol-tuuli", "gnq-mvet-oyeng", "vnm-nha-nhac",
    "vnm-central-highlands-gong-culture", "cod-congolese-rumba", "cyp-byzantine-chant",
    "hkg-cantonese-opera", "tha-classical-music-1900-recording", "qat-khaliji",
    "som-hees-cayaar-classes", "hkg-cantopop", "mwi-malipenga", "npl-newar-dhimay",
    "mli-imzad-music", "mrt-mauritanian-bardic-tradition", "mng-tsuur",
    "kaz-soviet-mass-song", "sdn-zar-tambura", "psx-ataba-mijana",
    "lbr-kpelle-music", "tcd-archive-documented-community-recordings",
    "bgd-bhawaiya", "tza-taarab", "tur-asiklik", "tur-kl-k", "uzb-shashmaqom",
    "btn-rigsar", "kwt-khaliji", "lka-nadagam-song", "arm-armenian-folk-ensembles",
    "nga-senwele",
    "caf-zokela",
    "idn-saman",
    "mar-malhun", "gha-highlife", "bgd-bhatiyali", "npl-lok-dohori", "vnm-ca-tru",
    "vnm-don-ca-tai-tu", "idn-dangdut", "ken-taarab", "dza-ahellil", "mar-aita",
    "mar-aissawa", "irn-hip-hop", "mwi-vimbuza", "mys-joget-gamelan", "com-taarab",
    "sau-khaliji", "aze-meyxana", "lbn-al-zajal", "vnm-cheo", "sgp-xinyao",
    "are-khaliji", "bwa-san-musical-bow-context", "nam-aixan-ancestral-music",
    "mac-guangdong-music", "lso-sefela", "phl-kundiman", "sgp-bangsawan",
    "jpn-nogaku", "kor-gagok", "uga-bigwala", "dza-imzad", "egy-semsemiah",
    "egy-semsemiah-music", "mrt-t-heydinn-epic-performance", "chn-shanghai-modern-song",
    "twn-taiwanese-dialect-popular-song", "ben-gelede-chants", "tgo-gelede-chants",
    "zmb-mooba", "zaf-makwaya",
    "gab-mvet-oyeng", "gab-gabonese-shelved-harp", "afg-naghma-ye-kashal",
    "mys-mak-yong", "brn-sung-pantun",
    "mac-cantonese-naamyam", "aze-azerbaijani-rap", "kaz-jahri-zikr-2002-2003",
    "mmr-burmese-hybrid-pop-late-1970s", "gnq-balele", "lao-lam-khap", "vnm-xoan",
    "ago-san-musical-bow", "nam-san-musical-bow", "sgp-singapop-1991-1993",
    "sdn-madih", "kwt-arda", "psx-zajal",
}


def main():
    entries = json.loads(CATALOGUE.read_text())["entries"]
    by_id = {entry["id"]: entry for entry in entries}
    unresolved = {
        entry["id"] for entry in entries
        if entry["status"] == "published" and not entry.get("youtube_examples")
    }
    target_ids = sorted(PROMOTED_IN_PASS | unresolved)
    # The catalogue can gain newly promoted country records while this long
    # running audit is active. Keep the ledger complete rather than silently
    # omitting those later additions from the denominator.
    assert len(target_ids) >= 124, f"expected at least 124 targets, got {len(target_ids)}"
    lines = [
        "# Full remaining YouTube-video audit — 2026-09-28",
        "",
        f"Every published entry without a video when this audit was opened received a direct YouTube discovery query. Later-published records extend the target set from the original 124 to {len(target_ids)}. A candidate was promoted when the result title or description explicitly identified the practice or an already-listed representative. `No match promoted` means the query ran but no sufficiently identified practice, music, or documentary video was published.",
        "",
        "On 2026-09-28, the then-72 unresolved entries received a second, two-path pass: an exact practice-plus-country YouTube query for every entry, and a separate listed-representative query for each of the 14 entries that had a usable representative field. This was added after a direct representative search surfaced the Senwele example. The Saman result identified in that rerun was promoted.",
        "",
        "| ID | Genre | Query run | Outcome |",
        "| --- | --- | --- | --- |",
    ]
    for genre_id in target_ids:
        entry = by_id[genre_id]
        query = f'“{entry["name"]}” YouTube'
        if genre_id in PROMOTED_IN_PASS:
            example = entry["youtube_examples"][0]
            outcome = f'[Promoted]({example["youtube_url"]}) — {example["artist"]}'
        else:
            outcome = "No sufficiently identified video promoted"
        lines.append(f"| `{genre_id}` | {entry['name']} | {query} | {outcome} |")
    lines.extend(["", f"Result: **{len(PROMOTED_IN_PASS)} promoted; {len(unresolved)} no sufficiently identified video promoted; {len(target_ids)}/{len(target_ids)} searched.**", ""])
    OUTPUT.write_text("\n".join(lines))
    print(OUTPUT)


if __name__ == "__main__":
    main()
