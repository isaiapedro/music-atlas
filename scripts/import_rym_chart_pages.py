"""Privately index user-saved RYM chart HTML as album recommendations.

All RYM-derived ratings, counts, page URLs, and raw chart attributes stay in
.local/rym. This importer does not publish static app data or promote genre
identity/geography claims. MusicBrainz resolution remains a separate review.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import statistics
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

try:
    from lxml import html
except ImportError as exc:  # pragma: no cover - depends on local tooling
    raise SystemExit("Install/use the local lxml-enabled Python to parse saved chart HTML") from exc

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / ".local/rym/raw"
DB_PATH = ROOT / ".local/rym/chart_catalogue.sqlite3"
SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS chart_page (
  page_id TEXT PRIMARY KEY, filename TEXT NOT NULL, chart_label TEXT NOT NULL,
  sha256 TEXT NOT NULL, imported_at TEXT NOT NULL, row_count INTEGER NOT NULL,
  exact_app_genre_ids_json TEXT NOT NULL, disposition TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS album_candidate (
  candidate_id TEXT PRIMARY KEY, page_id TEXT NOT NULL REFERENCES chart_page(page_id) ON DELETE CASCADE,
  chart_label TEXT NOT NULL, chart_rank INTEGER NOT NULL, title TEXT NOT NULL,
  artist_credit TEXT NOT NULL, rym_release_url TEXT NOT NULL, displayed_year TEXT NOT NULL,
  provisional_year INTEGER, average_rating REAL, rating_count INTEGER,
  review_count INTEGER, primary_genres_json TEXT NOT NULL, secondary_genres_json TEXT NOT NULL,
  primary_target_match INTEGER NOT NULL, median_rating_count REAL,
  threshold_pass INTEGER NOT NULL, selected_within_page_decade INTEGER NOT NULL,
  selection_note TEXT NOT NULL, source_sha256 TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS album_chart_idx ON album_candidate(page_id, provisional_year, chart_rank);
CREATE TABLE IF NOT EXISTS chart_tag (
  page_id TEXT NOT NULL REFERENCES chart_page(page_id) ON DELETE CASCADE,
  tag_label TEXT NOT NULL, primary_count INTEGER NOT NULL, secondary_count INTEGER NOT NULL,
  PRIMARY KEY(page_id, tag_label)
);
CREATE TABLE IF NOT EXISTS musicbrainz_resolution (
  candidate_id TEXT NOT NULL REFERENCES album_candidate(candidate_id) ON DELETE CASCADE,
  release_group_mbid TEXT NOT NULL, mb_title TEXT NOT NULL, mb_artist_credit TEXT NOT NULL,
  mb_first_year INTEGER, title_credit_match TEXT NOT NULL, year_comparison TEXT NOT NULL,
  PRIMARY KEY(candidate_id, release_group_mbid)
);
CREATE TABLE IF NOT EXISTS genre_assessment (
  page_id TEXT PRIMARY KEY REFERENCES chart_page(page_id) ON DELETE CASCADE,
  chart_label TEXT NOT NULL, atlas_genre_ids_json TEXT NOT NULL,
  classification TEXT NOT NULL, assessment_note TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS undated_hold_candidate (
  candidate_id TEXT PRIMARY KEY REFERENCES album_candidate(candidate_id) ON DELETE CASCADE,
  chart_label TEXT NOT NULL, average_rating REAL NOT NULL, rating_count INTEGER NOT NULL,
  page_median_rating_count REAL NOT NULL, hold_reason TEXT NOT NULL
);
"""

ASSESSMENTS = {
    "Afrobeats": ("distinct_from_similarly_named_genre", "Keep Afrobeats distinct from Afrobeat unless identity evidence supports a merge."),
    "Ayyalah": ("alias_or_spelling_review", "User context identifies Ayyalah as a replacement/discovery label; check spelling and the Atlas entry before equating."),
    "Azerbaijani Music": ("national_umbrella", "User says this was a stand-in for Dede Qorqud epic music; broader country music, not equivalent. Needs a better sourced definition/listing."),
    "Central African Music": ("regional_umbrella", "User says this was a stand-in for Cameroon Mendzəŋ; broader region label, not equivalent."),
    "Gamelan angklung": ("broader_related_tradition", "User says Indonesian angklung was not found; this is a broader/mixed Gamelan angklung term requiring definition, not an automatic equivalent."),
    "Klasik": ("broad_style_or_ambiguous_tag", "User says Afghan rubab playing appears under Klasik and Pashto Folk Music; these are discovery associations, not a precise equivalent."),
    "Pashto Folk Music": ("broader_related_tradition", "User says Afghan rubab playing appears under Klasik and Pashto Folk Music; treat as a broad repertoire relation, not the instrument/practice itself."),
    "Arabic Folk Music": ("broad_related_category", "User says Semsemiah and Zār are represented here; retain as a broad discovery category, not an exact equivalence."),
    "Kazakh Music": ("national_umbrella", "User notes this country-level umbrella does not identify a specific genre; do not create a genre layer from this label alone."),
    "Kyrgyz Traditional Music": ("national_umbrella", "User notes this country-level umbrella does not identify a specific genre; do not create a genre layer from this label alone."),
    "Cantonese Opera": ("related_not_equivalent", "User could not find Naamyam and found Cantonese Opera; keep as related discovery only, not an equivalence."),
    "Malay Gamelan": ("related_not_equivalent", "User says Joget gamelan is represented as Malay Gamelan; preserve as a broader/related discovery label, not an automatic merge."),
    "Azmari": ("shortened_name_candidate", "Shortened RYM label for the Atlas entry Azmari performance; same-identity candidate, pending category/definition check."),
    "Ayyalah": ("transliteration_candidate", "Possible transliteration/short-name relation to Al-Ayyala; retain as a candidate until page/category identity is reviewed."),
    "Armenian Folk Music": ("broader_related_tradition", "Broader RYM category related to Armenian folk ensemble practice; not a country-specific exact match."),
    "Dinka Music": ("broader_related_tradition", "Broad RYM category related to Dinka song traditions; keep the app's specific form distinct."),
    "Ghazal": ("broader_related_tradition", "Broad poetic/vocal genre; related to Kabuli ghazal but does not preserve its geographical qualifier."),
    "Pop Ghazal": ("broader_related_tradition", "Pop-inflected ghazal; related to pak-ghazal but does not confirm the classical tradition identity. Keep under revision until genre scope is resolved."),
    "Phleng phuea chiwit": ("broader_related_tradition", "Thai genre not currently in the Atlas catalogue. Possibly related to tha-luk-thung but identity unresolved. Keep under revision."),
    "Mande Music": ("regional_umbrella", "Broad Mande/Mandé cultural-area umbrella; does not map to a single Atlas genre. Keep under revision."),
    "Ngoma": ("broad_style_or_ambiguous_tag", "Broad East/Central African drum-and-dance umbrella; not equivalent to any single Atlas entry. Keep under revision."),
    "Shona Music": ("broader_related_tradition", "Broader Shona-music umbrella related to zwe-shona-mbira; Shona Mbira Music already matched exactly. Retain as a discovery relation."),
    "Soviet Estrada": ("broader_related_tradition", "Soviet-era popular-music umbrella possibly related to uzb-estrada and tjk-tajik-popular-music; national scope unresolved. Keep under revision."),
    "Uzbek Music": ("national_umbrella", "Country-level umbrella; does not identify a single Atlas genre. Keep under revision."),
    "Indigenous Taiwanese Music": ("broader_related_tradition", "Aboriginal/indigenous Taiwanese music; distinct from Campus Folk Songs (already matched). No current Atlas entry. Keep under revision."),
    "Songhai Music": ("broader_related_tradition", "Broad Songhai/Zarma-Songhai cultural category; related to ner-zarma-songhai-music but broader in scope. Review before equating."),
    "Tajik Music": ("broader_related_tradition", "National-level Tajik music umbrella; possibly related to tjk-tajik-popular-music but broader. Review before equating."),
    "Guangdong yinyue": ("translated_name_candidate", "Literal/shortened Guangdong-music naming candidate for Guangdong music in Macao; confirm the specific tradition and local scope."),
    "Hokkien Pop": ("related_narrower_category", "A pop-specific category related to Hokkien music; do not replace the broader app identity unless the entry itself is specifically Hokkien pop."),
}
TAG_ASSESSMENTS = {
    "Hip Hop": ("global_genre_family", [], "Treat as a broad, non-national genre family; an RYM tag does not establish a country-specific Atlas identity."),
    "Conscious Hip Hop": ("global_subgenre_discovery", [], "Broad/global subgenre label; use only for musical discovery, not a nationality assignment."),
    "Experimental Hip Hop": ("global_subgenre_discovery", [], "Broad/global subgenre label; use only for musical discovery, not a nationality assignment."),
    "Hardcore Hip Hop": ("global_subgenre_discovery", [], "Broad/global subgenre label; use only for musical discovery, not a nationality assignment."),
    "Instrumental Hip Hop": ("global_subgenre_discovery", [], "Broad/global subgenre label; use only for musical discovery, not a nationality assignment."),
    "Political Hip Hop": ("global_subgenre_discovery", [], "Broad/global subgenre label; use only for musical discovery, not a nationality assignment."),
    "Hip Hop Soul": ("global_subgenre_discovery", [], "Broad/global subgenre label; use only for musical discovery, not a nationality assignment."),
    "Polyphonic Chant": ("broad_vocal_form", [], "A broad vocal-form tag, not a national genre identity; the local musical tradition must be resolved independently."),
    "Nguni Folk Music": ("user_reported_related_category", ["ago-san-musical-bow"], "User reports this as a RYM representation related to Angolan San musical-bow practice; it was not present in the 67 saved chart pages, so treat as unverified and non-equivalent."),
    "Klasik": ("broad_style_or_ambiguous_tag", ["afg-rubab-playing"], "User reports this among RYM representations of Afghan rubab practice; broad discovery relation, not an exact genre/instrument equivalence."),
    "Pashto Folk Music": ("broader_related_tradition", ["afg-rubab-playing"], "User reports this among RYM representations of Afghan rubab practice; broad repertoire relation, not an exact equivalence."),
    "Arabic Folk Music": ("broad_related_category", ["egy-semsemiah", "egy-zar"], "User reports this as a broad RYM category for Semsemiah and Zār; not an exact equivalence."),
    "Azerbaijani Music": ("national_umbrella", ["aze-dede-qorqud"], "User reports this as a stand-in for Dede Qorqud; country umbrella, not an exact genre match."),
    "Central African Music": ("regional_umbrella", ["cmr-mendzan-xylophone-traditions"], "User reports this as a stand-in for Cameroon Mendzəŋ; broader region category, not an exact match."),
    "Gamelan angklung": ("broader_related_tradition", ["idn-angklung"], "User reports this as a broader/mixed category related to Indonesian angklung; not an exact equivalence."),
    "Cantonese Opera": ("related_not_equivalent", ["mac-cantonese-naamyam"], "User reports this as a discovery relation for Naamyam; not an exact equivalence."),
    "Malay Gamelan": ("related_not_equivalent", ["mys-joget-gamelan"], "User reports this as a discovery relation for Joget gamelan; not an automatic equivalence."),
}

ALIASES = {
    "Azmari": ["eth-azmari"],
    "Ayyalah": ["are-al-ayyala"],
    "Armenian Folk Music": ["arm-armenian-folk-ensembles"],
    "Dinka Music": ["sds-dinka-song-traditions"],
    "Ghazal": ["afg-kabuli-ghazal"],
    "Guangdong yinyue": ["mac-guangdong-music"],
    "Hokkien Pop": ["twn-taiwanese-dialect-popular-song"],
    "Azerbaijani Music": ["aze-dede-qorqud"],
    "Central African Music": ["cmr-mendzan-xylophone-traditions"],
    "Gamelan angklung": ["idn-angklung"],
    "Arabic Folk Music": ["egy-semsemiah", "egy-zar"],
    "Klasik": ["afg-rubab-playing"],
    "Pashto Folk Music": ["afg-rubab-playing"],
    "Cantonese Opera": ["mac-cantonese-naamyam"],
    "Malay Gamelan": ["mys-joget-gamelan"],
    # New genre batch — confirmed crosswalk entries
    "Andalusian Classical Music": ["mar-andalusian-nubah", "dza-andalusian-nubah", "lby-andalusian-nubah", "tun-andalusian-nubah"],
    "Andalusian Folk Music": ["mar-andalusian-nubah", "dza-andalusian-nubah", "lby-andalusian-nubah", "tun-andalusian-nubah"],
    "Beni": ["ken-beni", "tza-beni"],
    "Ewe Music": ["tgo-ewe-traditional-music"],
    "Griot Music": ["sen-griot-jeli-kora", "gmb-jali-griot-kora"],
    "Hausa Music": ["ner-hausa-griot-tradition"],
    "Jewish Liturgical Music": ["uga-abayudaya-music"],
    "Kirtan": ["bgd-pala-kirtan"],
    "Koche bazari": ["irn-kucheh-bazari"],
    "Mahori": ["khm-mohori"],
    "Muzika mizrahit": ["isr-musiqa-mizrahit"],
    "Muziki wa dansi": ["ken-dansi", "tza-dansi"],
    "Nubian Music": ["egy-nubian-music"],
    "OPM": ["phl-opm"],
    "Samri": ["sau-samri"],
    "Sanjo": ["kor-kayageum-sanjo"],
    "Tsugaru shamisen": ["jpn-shamisen-tradition"],
}


def norm(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


def musicbrainz_match_key(title: str, credit: str):
    """Return a conservative title/credit key, or ``None`` when it is unsafe.

    ``norm`` intentionally folds accented Latin text, but it cannot transliterate
    every writing system.  Treating a non-Latin title or credit as the empty
    string made unrelated releases appear to be exact matches.  Those entries
    remain in the private RYM review queue until they can be resolved with an
    identifier or a script-aware matcher.
    """
    normalized_title, normalized_credit = norm(title), norm(credit)
    if not normalized_title or not normalized_credit:
        return None
    return normalized_title, normalized_credit


def text(node) -> str:
    return " ".join(node.text_content().split()) if node is not None else ""


def nodes_by_class(node, class_name: str):
    return node.xpath(
        './/*[contains(concat(" ", normalize-space(@class), " "), $token)]',
        token=f" {class_name} ",
    )


def first_text(node, class_name: str) -> str:
    found = nodes_by_class(node, class_name)
    return text(found[0]) if found else ""


def parse_year(value: str):
    match = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", value)
    return int(match.group(1)) if match else None


def chart_artist_credit(artist_links) -> tuple[str, str]:
    """Return the visible credit, treating omitted chart credits as compilations.

    Saved RYM chart cards sometimes omit the artist anchor for compilation
    releases. The Atlas workflow treats every absent credit as Various Artists;
    the later MusicBrainz identity check remains mandatory.
    """
    names = "; ".join(dict.fromkeys(text(link) for link in artist_links if text(link)))
    if names:
        return names, "displayed_artist_credit"
    return "Various Artists", "inferred_various_artists"


def number(value: str):
    value = value.strip().replace(",", "")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([kKmM]?)", value)
    if not match:
        return None
    amount = float(match.group(1))
    return int(amount * {"": 1, "k": 1000, "m": 1_000_000}[match.group(2).casefold()])


def classes(node, class_name):
    return node.xpath(
        './/*[contains(concat(" ", normalize-space(@class), " "), $token)]',
        token=f" {class_name} ",
    )


def app_index():
    data = json.loads((ROOT / "web/data/genres.json").read_text(encoding="utf-8"))["genres"]
    index = {}
    for genre in data:
        index.setdefault(display_key(genre["name"]), []).append(genre["id"])
    return index


def display_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    normalized = re.sub(r"\b(music|dance|song|songs|chant|chants|tradition|traditions|style|genre|the)\b", " ", normalized)
    return " ".join(dict.fromkeys(re.findall(r"[a-z0-9]+", normalized)))


def musicbrainz_index(path: Path):
    if not path.exists():
        return {}
    db = sqlite3.connect(path)
    index = {}
    try:
        for rgid, title, credit_id, mbid, year in db.execute(
                "SELECT id,title,credit_id,mbid,first_year FROM release_group"):
            parts = db.execute(
                "SELECT credited_name,join_phrase FROM artist_credit_artist "
                "WHERE credit_id=? ORDER BY position", (credit_id,)
            ).fetchall()
            credit = "".join(name + join for name, join in parts)
            key = musicbrainz_match_key(title, credit)
            if key:
                index.setdefault(key, []).append((mbid, title, credit, year))
    finally:
        db.close()
    return index


def parse_page(path: Path, index):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    root = html.fromstring(raw)
    label = path.name.removeprefix("Best ").removesuffix(" albums of all time - Rate Your Music.html")
    page_id = "rym-chart-" + re.sub(r"[^a-z0-9]+", "-", norm(label)).strip("-")
    exact_ids = index.get(display_key(label), [])
    app_ids = exact_ids or ALIASES.get(label, [])
    if exact_ids:
        disposition = "exact_display_name_candidate; review shared identity and areas"
    elif app_ids:
        disposition = "alias_or_relationship_candidate; inspect the editorial classification"
    else:
        disposition = "unmatched_or_alias_candidate; no genre promotion from chart label alone"
    cards = root.xpath(
        '//div[contains(concat(" ", normalize-space(@class), " "), " page_charts_section_charts_item ") '
        'and contains(concat(" ", normalize-space(@class), " "), " object_release ")]'
    )
    parsed = []
    primary_counts = {}
    secondary_counts = {}
    for rank, card in enumerate(cards, 1):
        release = card.xpath('.//a[contains(concat(" ", normalize-space(@class), " "), " release ")]')
        artist_links = card.xpath('.//a[contains(concat(" ", normalize-space(@class), " "), " artist ")]')
        primary = [text(n) for n in classes(card, "page_charts_section_charts_item_genres_primary")
                   for n in n.xpath('.//a[contains(concat(" ", normalize-space(@class), " "), " genre ")]')]
        secondary = [text(n) for n in classes(card, "page_charts_section_charts_item_genres_secondary")
                     for n in n.xpath('.//a[contains(concat(" ", normalize-space(@class), " "), " genre ")]')]
        for value in set(primary):
            primary_counts[value] = primary_counts.get(value, 0) + 1
        for value in set(secondary):
            secondary_counts[value] = secondary_counts.get(value, 0) + 1
        rating_text = first_text(card, "page_charts_section_charts_item_details_average_num")
        rating_match = re.search(r"\d+(?:\.\d+)?", rating_text)
        rating_nodes = classes(card, "page_charts_section_charts_item_details_ratings")
        review_nodes = classes(card, "page_charts_section_charts_item_details_reviews")
        count_text = text(classes(rating_nodes[0], "abbr")[0]) if rating_nodes and classes(rating_nodes[0], "abbr") else ""
        review_text = text(classes(review_nodes[0], "abbr")[0]) if review_nodes and classes(review_nodes[0], "abbr") else ""
        displayed_year = first_text(card, "page_charts_section_charts_item_date")
        release_url = release[0].get("href", "") if release else ""
        artist_credit, artist_credit_source = chart_artist_credit(artist_links)
        row = {
            "rank": rank,
            "title": text(release[0]) if release else "",
            "url": release_url,
            "artist": artist_credit,
            "artist_credit_source": artist_credit_source,
            "displayed_year": displayed_year,
            "year": parse_year(displayed_year),
            "rating": float(rating_match.group()) if rating_match else None,
            "rating_count": number(count_text),
            "review_count": number(review_text),
            "primary": primary,
            "secondary": secondary,
        }
        row["primary_match"] = norm(label) in {norm(tag) for tag in primary}
        parsed.append(row)
    # Rating/review thresholds rank the normal recommendation pass. A page with
    # fewer than nine selected items is then filled from the chart itself,
    # regardless of score/participation, so sparse genre pages retain every
    # available recommendation up to nine. The later MB identity gate still
    # decides whether a row can become a public record.
    by_decade = {}
    for row in parsed:
        if row["year"] and row["rating_count"] and row["primary_match"]:
            decade = row["year"] // 10 * 10
            by_decade.setdefault(decade, []).append(row)
    selected_ids = set()
    medians = {}
    for decade, pool in by_decade.items():
        median = statistics.median(row["rating_count"] for row in pool)
        medians[decade] = median
        qualified = [row for row in pool if row["rating"] is not None and row["rating"] > 3.2
                     and row["rating_count"] >= median]
        qualified.sort(key=lambda row: (-row["rating"], -row["rating_count"], row["rank"]))
        selected_ids.update(id(row) for row in qualified[:9])
    page_counts = [row["rating_count"] for row in parsed if row["primary_match"] and row["rating_count"]]
    page_median = statistics.median(page_counts) if page_counts else None
    fallback_ids = set()
    if len(selected_ids) < 9:
        for row in sorted(parsed, key=lambda item: item["rank"]):
            if id(row) in selected_ids:
                continue
            fallback_ids.add(id(row))
            if len(selected_ids) + len(fallback_ids) >= 9:
                break
    selected_ids.update(fallback_ids)
    return page_id, label, digest, app_ids, disposition, parsed, primary_counts, secondary_counts, medians, selected_ids, fallback_ids, page_median


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=RAW)
    parser.add_argument("--database", type=Path, default=DB_PATH)
    parser.add_argument("--musicbrainz-database", type=Path,
                        default=ROOT / ".local/musicbrainz/catalog.sqlite3")
    args = parser.parse_args()
    pages = sorted(args.input_dir.glob("Best * albums of all time - Rate Your Music.html"))
    if not pages:
        raise SystemExit(f"No saved RYM chart pages found under {args.input_dir}")
    args.database.parent.mkdir(parents=True, exist_ok=True)
    index = app_index()
    mb_index = musicbrainz_index(args.musicbrainz_database)
    db = sqlite3.connect(args.database)
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(SCHEMA)
    imported_items = 0
    with db:
        for path in pages:
            page_id, label, digest, app_ids, disposition, rows, primary, secondary, medians, selected, fallback, page_median = parse_page(path, index)
            db.execute("DELETE FROM chart_page WHERE page_id=?", (page_id,))
            db.execute("INSERT INTO chart_page VALUES(?,?,?,?,?,?,?,?)", (
                page_id, path.name, label, digest, datetime.now(timezone.utc).isoformat(), len(rows),
                json.dumps(app_ids), disposition,
            ))
            classification, assessment_note = ASSESSMENTS.get(
                label,
                ("exact_name_candidate" if app_ids else "unmatched_needs_review",
                 "Exact display-name candidate only; RYM chart identity does not establish Atlas geography, period, or equivalence." if app_ids else
                 "No exact app display-name match. Treat the page as a discovery lead; do not create or delete an Atlas genre without independent review."),
            )
            db.execute("INSERT INTO genre_assessment VALUES(?,?,?,?,?)", (
                page_id, label, json.dumps(app_ids), classification, assessment_note,
            ))
            for tag in sorted(set(primary) | set(secondary)):
                db.execute("INSERT INTO chart_tag VALUES(?,?,?,?)", (
                    page_id, tag, primary.get(tag, 0), secondary.get(tag, 0),
                ))
            for row in rows:
                decade = row["year"] // 10 * 10 if row["year"] else None
                median = medians.get(decade)
                pass_threshold = bool(row["primary_match"] and row["rating"] is not None
                                      and row["rating"] > 3.2 and row["rating_count"] is not None
                                      and median is not None and row["rating_count"] >= median)
                chosen = id(row) in selected
                coverage_fallback = id(row) in fallback
                notes = []
                if not row["primary_match"]:
                    notes.append("target absent from primary genres")
                if row["year"] is None:
                    notes.append("chart capture does not expose a release year; use MusicBrainz only after an unambiguous identity match")
                if row["artist_credit_source"] == "inferred_various_artists":
                    notes.append("artist credit absent in saved chart card; treated as Various Artists")
                if row["rating"] is None or row["rating_count"] is None:
                    notes.append("rating/count unavailable")
                if pass_threshold and not chosen:
                    notes.append("passed score and P50 but outside top nine in provisional page decade")
                if coverage_fallback:
                    notes.append("minimum-nine chart-page fallback; selected by chart membership/rank, not rating or review threshold")
                notes.append("provisional only; resolve album identity and year independently before app ingestion")
                candidate_id = hashlib.sha256(f"{page_id}|{row['rank']}|{row['url']}|{row['title']}".encode()).hexdigest()
                db.execute("INSERT INTO album_candidate VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                    candidate_id, page_id, label, row["rank"], row["title"], row["artist"], row["url"],
                    row["displayed_year"], row["year"], row["rating"], row["rating_count"], row["review_count"],
                    json.dumps(row["primary"], ensure_ascii=False), json.dumps(row["secondary"], ensure_ascii=False),
                    int(row["primary_match"]), median, int(pass_threshold), int(chosen), "; ".join(notes), digest,
                ))
                if (row["year"] is None and row["primary_match"] and row["rating"] is not None
                        and row["rating"] > 3.2 and row["rating_count"] is not None
                        and page_median is not None and row["rating_count"] >= page_median):
                    db.execute("INSERT INTO undated_hold_candidate VALUES(?,?,?,?,?,?)", (
                        candidate_id, label, row["rating"], row["rating_count"], page_median,
                        "Undated chart item exceeds 3.2 and reaches the page-level median participation threshold; "
                        "review identity and assign a decade from independent discographic evidence.",
                    ))
                match_key = musicbrainz_match_key(row["title"], row["artist"])
                for mbid, mb_title, mb_credit, mb_year in mb_index.get(match_key, []) if match_key else []:
                    db.execute("INSERT INTO musicbrainz_resolution VALUES(?,?,?,?,?,?,?)", (
                        candidate_id, mbid, mb_title, mb_credit, mb_year,
                        "exact_normalized_title_and_artist_credit",
                        "same_year" if row["year"] and mb_year == row["year"] else
                        "year_differs" if row["year"] and mb_year else
                        "year_unresolved_in_one_or_both_sources",
                    ))
            imported_items += len(rows)
    crosswalk_path = ROOT / "research/rym_chart_page_crosswalk.csv"
    tag_crosswalk_path = ROOT / "research/rym_tag_discovery_crosswalk.csv"
    album_review_path = ROOT / ".local/rym/album_candidates.csv"
    with crosswalk_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("rym_chart_label", "atlas_genre_id_candidates", "classification", "assessment_note", "chart_items"))
        writer.writerows(db.execute(
            "SELECT a.chart_label,a.exact_app_genre_ids_json,g.classification,g.assessment_note,p.row_count "
            "FROM genre_assessment g JOIN chart_page p USING(page_id) "
            "JOIN (SELECT page_id,chart_label,exact_app_genre_ids_json FROM chart_page) a USING(page_id) "
            "ORDER BY a.chart_label"
        ))
    tag_totals = {}
    for label, primary_count, secondary_count in db.execute(
            "SELECT tag_label,SUM(primary_count),SUM(secondary_count) FROM chart_tag GROUP BY tag_label"):
        if label in TAG_ASSESSMENTS:
            classification, ids, note = TAG_ASSESSMENTS[label]
        else:
            ids = index.get(display_key(label), []) or ALIASES.get(label, [])
            classification = "exact_name_candidate" if index.get(display_key(label)) else (
                "alias_or_related_candidate" if ids else "unmatched_secondary_or_primary_discovery")
            note = ("Name match only; verify musical identity and geography before merging." if ids else
                    "Unmatched RYM chart tag; discovery lead only. Secondary tags are never album-selection evidence or proof of Atlas identity.")
        tag_totals[label] = (classification, ids, note, primary_count or 0, secondary_count or 0)
    tag_totals.setdefault("Nguni Folk Music", TAG_ASSESSMENTS["Nguni Folk Music"] + (0, 0))
    with tag_crosswalk_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("rym_tag", "atlas_genre_id_candidates", "relationship_classification",
                         "primary_genre_album_occurrences", "secondary_tag_album_occurrences", "assessment_note"))
        for label, (classification, ids, note, primary_count, secondary_count) in sorted(tag_totals.items()):
            writer.writerow((label, json.dumps(ids, ensure_ascii=False), classification,
                             primary_count, secondary_count, note))
    with album_review_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("candidate_id", "chart_label", "chart_rank", "album_title", "artist_credit",
                         "rym_displayed_year", "provisional_year", "average_rating_private",
                         "rating_count_private", "review_count_private", "primary_genres",
                         "secondary_genres_discovery_only", "primary_target_match", "p50_threshold_pass",
                         "top_nine_provisional", "undated_hold", "musicbrainz_release_group_mbids",
                         "musicbrainz_years", "review_note"))
        writer.writerows(db.execute(
            "SELECT a.candidate_id,a.chart_label,a.chart_rank,a.title,a.artist_credit,a.displayed_year,a.provisional_year,"
            "a.average_rating,a.rating_count,a.review_count,a.primary_genres_json,a.secondary_genres_json,"
            "a.primary_target_match,a.threshold_pass,a.selected_within_page_decade,"
            "EXISTS(SELECT 1 FROM undated_hold_candidate h WHERE h.candidate_id=a.candidate_id),"
            "COALESCE((SELECT group_concat(release_group_mbid,';') FROM musicbrainz_resolution m WHERE m.candidate_id=a.candidate_id),''),"
            "COALESCE((SELECT group_concat(COALESCE(mb_first_year,'?'),';') FROM musicbrainz_resolution m WHERE m.candidate_id=a.candidate_id),''),"
            "a.selection_note FROM album_candidate a ORDER BY a.chart_label,a.provisional_year,a.chart_rank"
        ))
    print(json.dumps({
        "database": str(args.database), "pages_indexed": len(pages), "album_rows_indexed": imported_items,
        "private_album_review_csv": str(album_review_path),
        "page_assessment_csv": str(crosswalk_path),
        "tag_discovery_crosswalk_csv": str(tag_crosswalk_path),
        "genre_pages_with_atlas_identity_candidates": sum(bool(parse_page(path, index)[3]) for path in pages),
        "exact_title_artist_musicbrainz_matches": db.execute(
            "SELECT COUNT(DISTINCT candidate_id) FROM musicbrainz_resolution"
        ).fetchone()[0],
        "selected_candidates_with_exact_musicbrainz_match": db.execute(
            "SELECT COUNT(DISTINCT a.candidate_id) FROM album_candidate a "
            "JOIN musicbrainz_resolution m USING(candidate_id) WHERE a.selected_within_page_decade=1"
        ).fetchone()[0],
        "undated_high_score_holds": db.execute("SELECT COUNT(*) FROM undated_hold_candidate").fetchone()[0],
        "album_threshold": "Rating pass: primary genre, average >3.2 and page-decade P50; sparse pages are then filled to nine chart items by rank regardless of ratings/reviews",
        "caveat": "all selections remain private provisional recommendations pending MusicBrainz identity/date resolution",
    }, ensure_ascii=False, indent=2))
    db.close()


if __name__ == "__main__":
    main()
