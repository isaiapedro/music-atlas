"""Build a reproducible research queue for every mapped area, without publishing leads."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
ACQUIRED = ROOT / ".local" / "acquired_sources"
WORKSPACE = ROOT.parents[2]
ARTS_MUSIC_RAW = WORKSPACE / "knowledge" / "arts" / "raw" / "music"
DECADES = list(range(1900, 2030, 10))
CURRENT_YEAR = 2026  # Snapshot date, not a runtime assertion.
SPECIAL_AREAS = {"CYN", "HKG", "IOA", "KAS", "MAC", "PSX", "SAH", "SOL", "TWN"}

# Stable, non-overlapping country ownership for parallel research. These are
# editorial work lanes, not claims about a place's cultural or political identity.
REGION_LANES = {
    "africa_north": "DZA EGY LBY MAR MRT SAH SDN TUN",
    "africa_west": "BEN BFA CIV CPV GHA GIN GMB GNB LBR MLI NER NGA SEN SLE TGO",
    "africa_central": "CAF CMR COD COG GAB GNQ STP TCD",
    "africa_east_horn": "BDI DJI ERI ETH KEN RWA SDS SOL SOM TZA UGA",
    "africa_south_islands": "AGO BWA COM LSO MDG MOZ MWI NAM SWZ ZAF ZMB ZWE",
    "asia_central_north": "KAZ KGZ MNG TJK TKM UZB",
    "asia_west_caucasus": "ARM AZE CYP CYN GEO TUR",
    "asia_west_middle_east": "ARE BHR IRN IRQ ISR JOR KWT LBN OMN PSX QAT SAU SYR YEM",
    "asia_east": "CHN HKG JPN KOR MAC PRK TWN",
    "asia_south": "AFG BGD BTN IND IOA KAS LKA NPL PAK",
    "asia_southeast": "BRN IDN KHM LAO MMR MYS PHL SGP THA TLS VNM",
}
AGENT_BY_LANE = {
    "africa_north": "Agent 1",
    "africa_west": "Agent 2",
    "africa_central": "Agent 3",
    "africa_east_horn": "Agent 4",
    "africa_south_islands": "Agent 5",
    "asia_central_north": "Agent 6",
    "asia_west_caucasus": "Agent 7",
    "asia_west_middle_east": "Agent 8",
    "asia_east": "Agent 9",
    "asia_south": "Agent 10",
    "asia_southeast": "Agent 11",
}
INTEGRATOR = "Agent 12"
assert set(AGENT_BY_LANE) == set(REGION_LANES)
assert len(set(AGENT_BY_LANE.values())) == len(REGION_LANES)
LANE_BY_CODE = {code: lane for lane, codes in REGION_LANES.items() for code in codes.split()}
assert sum(len(codes.split()) for codes in REGION_LANES.values()) == len(LANE_BY_CODE)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def acquired_sources(mapped_codes):
    """Attach registered private documents as reading assignments, not evidence."""
    index = ACQUIRED / "index.json"
    if not index.exists():
        return defaultdict(list)
    data = read(index)
    assert data.get("version") == 1 and isinstance(data.get("documents"), list)
    result = defaultdict(list)
    seen = set()
    for item in data["documents"]:
        source_id = item["id"]
        assert source_id not in seen, f"duplicate acquired source: {source_id}"
        seen.add(source_id)
        assert ("file" in item) != ("source_path" in item), f"exactly one source path required: {source_id}"
        if "file" in item:
            relative = Path(item["file"])
            base = ACQUIRED
        else:
            relative = Path(item["source_path"])
            assert relative.parts[:4] == ("knowledge", "arts", "raw", "music"), f"source outside Arts music custody: {relative}"
            base = WORKSPACE
        assert not relative.is_absolute() and ".." not in relative.parts, f"unsafe acquired file path: {relative}"
        path = (base / relative).resolve()
        assert path.is_relative_to((ARTS_MUSIC_RAW if "source_path" in item else ACQUIRED).resolve()) and path.is_file(), f"missing acquired source: {path}"
        codes = item["countries"]
        assert codes and set(codes) <= mapped_codes, f"unknown acquired-source country: {source_id}"
        assert item.get("title") and item.get("citation") and item.get("language"), f"incomplete acquired source: {source_id}"
        knowledge_note = item.get("knowledge_note")
        if knowledge_note:
            note = Path(knowledge_note)
            assert note.parts[:4] == ("knowledge", "arts", "wiki", "papers") and ".." not in note.parts and (WORKSPACE / note).is_file(), f"missing Arts source note: {knowledge_note}"
        for code in codes:
            result[code].append({"id": source_id, "title": item["title"], "citation": item["citation"],
                                 "file": str(path), "language": item["language"],
                                 "knowledge_note": knowledge_note,
                                 "relevant_pages": item.get("relevant_pages", "review table of contents"),
                                 "review_status": "unreviewed"})
    return result


def candidate_sources(dossier, unesco):
    """Prefer distinct source families; preserve URLs for a reviewer to inspect."""
    sources, domains = [], set()
    for candidate in dossier.get("candidates", []):
        matching_heritage = next((item for item in unesco
                                  if candidate["name"].casefold() in item["title"].casefold()
                                  or item["title"].casefold() in candidate["name"].casefold()), None)
        if matching_heritage and "ich.unesco.org" not in domains:
            sources.append({"url": matching_heritage["source_url"], "title": matching_heritage["title"],
                            "kind": "unesco_record", "lead": candidate["name"]})
            domains.add("ich.unesco.org")
        for source in candidate.get("sources", []):
            url = source.get("url", "")
            domain = urlparse(url).hostname
            if domain == "ich.unesco.org" and ("/RL/" in url or "/USL/" in url):
                continue  # Older dossier slugs need verification; use the canonical record above.
            if domain and domain not in domains:
                sources.append({"url": url, "title": source.get("title") or candidate["name"],
                                "kind": "dossier_source", "lead": candidate["name"]})
                domains.add(domain)
            if len(sources) == 3:
                return sources
    for lead in unesco:
        if lead.get("music_match") != "primary_concept":
            continue
        url = lead.get("source_url", "")
        if url and url not in {item["url"] for item in sources}:
            sources.append({"url": url, "title": lead["title"], "kind": "unreviewed_unesco_lead"})
        if len(sources) == 3:
            break
    return sources


def active(genre, area, decade):
    start = max(genre.get("active_from") or 2020, area.get("active_from") or 2020)
    end = min(genre.get("active_to") or CURRENT_YEAR, area.get("active_to") or CURRENT_YEAR)
    return start <= min(decade + 9, CURRENT_YEAR) and decade <= end


def decade_ranges(years):
    if not years:
        return "none"
    groups = []
    for year in years:
        if groups and year == groups[-1][-1] + 10:
            groups[-1].append(year)
        else:
            groups.append([year])
    return ", ".join(f"{group[0]}s–{group[-1]}s" if len(group) > 1 else f"{group[0]}s"
                     for group in groups)


def build():
    inventory = read(RESEARCH / "country_inventory.json")["countries"]
    assert {row["code"] for row in inventory} == set(LANE_BY_CODE), "Update regional lanes for the mapped-area inventory"
    documents = acquired_sources(set(LANE_BY_CODE))
    genres = [row for row in read(RESEARCH / "genre_catalogue.json")["entries"] if row["status"] == "published"]
    saved_wikis = read(RESEARCH / "wiki_articles.json")["genres"]
    unesco = defaultdict(list)
    for row in read(RESEARCH / "unesco_candidates.json")["candidates"]:
        unesco[row["country"]].append(row)
    wikidata = defaultdict(list)
    for row in read(RESEARCH / "wikidata_candidates.json")["candidates"]:
        wikidata[row["country"]].append(row)
    mapped = defaultdict(list)
    for genre in genres:
        mapped[genre["country"]].append((genre, genre))
        for area in genre.get("associated_areas", []):
            mapped[area["country"]].append((genre, area))
    result = []
    for row in inventory:
        code, name = row["code"], row["name"]
        path = RESEARCH / "countries" / f"{code}.json"
        dossier = read(path) if path.exists() else {}
        mapped_genres = mapped[code]
        covered = [year for year in DECADES if any(active(genre, area, year) for genre, area in mapped_genres)]
        missing = [year for year in DECADES if year not in covered]
        published_ids = {genre["id"] for genre, _ in mapped_genres}
        leads = [{"name": candidate["name"], "status": candidate["publication_status"]}
                 for candidate in dossier.get("candidates", [])
                 if candidate.get("publication_status") != "published" and candidate.get("publication_id", candidate["id"]) not in published_ids]
        leads += [{"name": item["title"], "status": "unreviewed_unesco"}
                  for item in unesco[code] if item.get("music_match") == "primary_concept"]
        leads += [{"name": item["title"], "status": "unreviewed_wikidata"} for item in wikidata[code][:2]]
        seen, distinct = set(), []
        for lead in leads:
            key = lead["name"].casefold()
            if key not in seen:
                distinct.append(lead)
                seen.add(key)
        access = candidate_sources(dossier, unesco[code])
        actions = ["Write a sourced 1900–present music-history chronology, including continuity and ruptures.",
                   "Audit ritual, oral, court/classical, popular and contemporary roles against local communities.",
                   "For each missing decade, find documented practice in that decade; reuse a continuing genre only with continuity evidence.",
                   "Verify one genre-specific Wikipedia page or focused section and relevant credited artists for every published layer."]
        if code in SPECIAL_AREAS:
            actions.insert(0, "Resolve the mapped area's political/geographic scope before assigning national music claims.")
        if not dossier:
            actions.insert(0, "Create a country dossier and locate a national archive, broadcaster, library or university collection.")
        result.append({
            "code": code, "name": name, "continent": row["continent"],
            "research_lane": LANE_BY_CODE[code], "assigned_agent": AGENT_BY_LANE[LANE_BY_CODE[code]],
            "map_scope_review": code in SPECIAL_AREAS,
            "acquired_documents": documents[code],
            "inventory_status": row["status"], "has_dossier": bool(dossier),
            "languages_already_searched": dossier.get("languages_searched", []),
            "live_genres": [{"id": genre["id"], "name": genre["name"],
                             "association": "catalogue_home" if genre is area else area["relationship"],
                             "wikipedia_status": "saved" if saved_wikis.get(genre["id"]) else
                             genre.get("research", {}).get("wikipedia", {}).get("status", "unreviewed"),
                             "artists": genre.get("artists", [])}
                            for genre, area in mapped_genres],
            "genre_wikipedia_gaps": [genre["id"] for genre, _ in mapped_genres if not saved_wikis.get(genre["id"])],
            "genre_artist_gaps": [genre["id"] for genre, _ in mapped_genres if not genre.get("artists")],
            "currently_visible_decades": covered, "decades_without_live_genre": missing,
            "decades_requiring_historical_audit": DECADES,
            "candidate_leads_to_verify": distinct[:8], "first_access_urls": access,
            "additional_access_queries": [f"{name} music history 1900 1950 2000 ethnomusicology",
                                          f"{name} national music archive radio recordings discography",
                                          f"{name} traditional music living communities field recordings"],
            "next_actions": actions,
            "source_need": "Need local-language histories, discographies or fieldwork, especially for early decades."
                           if len(covered) < 7 else "Need period-by-period continuity checks and minority/community coverage.",
            "private_intake_request": (f"{name}: a cited local-language music history, pre-1950 discography, "
                                       "or archive inventory with pages and access rights."
                                       if not access else
                                       f"{name}: sources documenting the {missing[0]}s or the next unreviewed decade, "
                                       "including page numbers, credited performers and access rights."
                                       if missing else
                                       f"{name}: sources testing continuity and minority-community coverage "
                                       "across the full 1900s–2020s span, with page numbers and access rights.")
        })
    assert len(result) == 107 and len({row["code"] for row in result}) == 107
    return {"version": 1, "snapshot_date": "2026-09-28", "target_decades": DECADES,
            "integration_owner": INTEGRATOR,
            "coverage_definition": "Evidence-anchored published genre association; undated viewer layers do not fill historical research cells",
            "countries": result}


def render_markdown(data):
    rows = data["countries"]
    visible = sum(len(row["currently_visible_decades"]) for row in rows)
    no_access = sum(not row["first_access_urls"] for row in rows)
    lines = ["# Country and decade music research plan", "",
             "This is a research queue, not a completed history or a claim that every decade had a distinct genre. "
             "The target is at least one **source-supported living or historical practice** for each 1900s–2020s "
             "country-decade cell, plus a representative set of major traditions and relevant artists. "
             "An empty cell means evidence is unreviewed or unavailable, never that music was absent.", "",
             f"Snapshot: 2026-09-28. The current atlas shows a genre in {visible} of {len(rows) * len(DECADES)} "
             "country-decade cells. None of the national history audits is complete. Current visibility can rest on "
             "a genre's broad editorial lifespan and is **not** proof of decade-by-decade continuity.", "",
             "The queue also names the saved Wikipedia status and credited artists of each live layer. "
             "An exact genre article may not exist; a focused section or clearly attributed local text is the honest fallback. "
             "For collective traditions, document an ensemble or bearer community when individual artist credit would be misleading.", "",
             "## Parallel regional work lanes", "",
             "Each mapped area has exactly one `research_lane` and one `assigned_agent` in the JSON queue. Agent numbers are stable work assignments, not currently running processes. "
             "These lanes divide editing responsibility; they do not define musical borders. North Asian Russia is outside the current map, while Mongolia belongs to `asia_central_north`. "
             "Western Asia is split between the Caucasus/Anatolia and the rest of the Middle East so existing Middle East material can be reused without hiding the Caucasus gap.", "",
             "| Agent | Lane | Areas | Count | Acquired source IDs |", "| --- | --- | --- | ---: | --- |"]
    for lane, codes in REGION_LANES.items():
        lane_rows = [row for row in rows if row["code"] in codes.split()]
        area_names = [f"{row['name']} ({row['code']})" for row in lane_rows]
        source_ids = sorted({doc["id"] for row in lane_rows for doc in row["acquired_documents"]})
        lines.append(f"| {AGENT_BY_LANE[lane]} | `{lane}` | {', '.join(area_names)} | {len(area_names)} | {', '.join(source_ids) or 'none'} |")
    lines += ["",
             f"**{INTEGRATOR} — catalog integrator:** owns shared `research/genre_catalogue.json`, Wikipedia article matching/snapshots, generated site data, duplicate resolution, cross-border association review, and publication checks. Research agents own only their assigned country dossiers. Run agents in waves according to available capacity; preserve the same assignment when a wave resumes.", "",
             "### Parallel editing contract", "",
             "Private acquired documents are registered in `.local/acquired_sources/index.json` and assigned by mapped country code. "
             "The generator lists them in each country's `acquired_documents`; it does not read or interpret their contents. "
             "Agents must read the relevant file and cited pages, record claim-level findings in their country dossier, and distinguish a document's claims from their own inferences.", "",
             "For every assigned country: open the Arts Knowledge source note to locate relevant chapters or entries, read those passages in the exact raw file, then record document ID, page/section, claim, place, date, artist, and uncertainty in `research/countries/<CODE>.json`. The wiki note is a navigation aid; it does not replace the source passage. A missing or unreadable passage remains a gap, not a verified claim.", "",
             "1. Each agent owns only `research/countries/<CODE>.json` files in its lane. Record source URLs, page or section pointers, access language, place/period claims, performers, uncertainty, and open decade gaps there. Never force one genre into every decade without continuity evidence.",
             "2. Agents may nominate cross-border genres in their dossiers, but must send the affected country code and exact supporting claim to that lane's owner. The receiving owner verifies local practice, location, and dates. Keep one canonical genre identity; treat other countries as separately sourced associations.",
             f"3. Agents do not concurrently edit `research/genre_catalogue.json`, `research/wiki_articles.json`, generated static data, or this plan. {INTEGRATOR} reviews dossiers and source ledgers, resolves duplicate names and contested geography, promotes entries, saves exact Wikipedia matches, then runs the builders and validators. The public source is a bibliographic citation with an exact locator, never a private raw path.",
             "4. Handoff per country: reviewed candidates, a source-backed period chronology, mapped region names or justified country scope, artist and article status, remaining decade gaps, and an explicit coverage judgment. The integrator marks the country complete only after the breadth audit in `GENRE_RESEARCH_PLAN.md`.", "",
             "## Research sequence for every country", "",
             "1. Establish the mapped area's scope, major communities and local search languages. "
             "Write a short chronology of colonial, independence, migration, broadcast, recording and digital eras where relevant; do not impose those events on countries where they do not fit.",
             "2. Review the existing dossier and the first access links below. Search national archives, libraries, broadcasters, university repositories, community institutions and local-language scholarship. "
             "Read every assigned acquired document or record why it could not be read. Use UNESCO and Wikidata rows as discovery leads only.",
             "3. Build a source ledger for each candidate: name/aliases, musical characteristics, practice or influence area, first documentation, later transmission, named performers, and exact page or archive item. "
             "Separate a recording's release date from a genre's origin and an inscription date from continued practice.",
             "4. Audit the thirteen decades individually. A genre may cover several decades when a source supports transmission through them. "
             "When evidence is thin, keep the cell open and seek fieldwork or specialist history; never invent a filler genre.",
             "5. For each published genre, map a matching standalone Wikipedia page or focused section and save its revision in `research/wiki_articles.json`. "
             "If no precise article exists, retain the reviewed no-match reason and a source-backed local note. "
             "Verify artists against recordings, scholarly accounts or cultural institutions; use a named ensemble or community bearer where individual attribution is inappropriate. Attach YouTube playback only for exact reviewed videos from an official artist, verified artist, label, or other rights-holder channel.",
             "6. Publish the reviewed country dossier and genre areas, regenerate static data, validate, inspect the map at each decade, and update the audit. "
             "Recheck boundary changes before mapping a historical locality to a modern region.", "",
             "## Access routes", "",
             "- [UNESCO heritage files](https://ich.unesco.org/en/lists) supply nominations and living-practice leads; they are not a complete genre ranking.",
             "- [Smithsonian Folkways](https://folkways.si.edu/faq) provides free album liner notes that can supply performer, place and recording context.",
             "- [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API) helps resolve artist and recording identifiers; verify genre and geography in independent sources.",
             "- Local archives, university repositories, national broadcasters and community institutions provide the missing country-specific histories. "
             "Record access terms and citation pages in the dossier; keep full copyrighted books out of public site assets.",
             f"- {no_access} area plans do not yet have a candidate-specific direct source URL. Their saved search queries and private intake request are the first access task, not evidence of an absent musical history.", "",
             "## Country queue", "",
             "The linked JSON has the exact missing-decade list, source URLs, verified or candidate leads, and next actions for **every mapped area**. "
             "`Lead` below means a topic to investigate, not a confirmed main genre. An inspect-source link starts the country's source review and may document a different candidate than the first named lead. "
             "The map includes several territories or disputed areas; those rows require a scope review before national claims.", ""]
    for continent in ("Africa", "Asia"):
        lines += [f"### {continent}", "", "| Area | Live layers | Decades without live genre | First lead and access |", "| --- | ---: | --- | --- |"]
        for row in rows:
            if row["continent"] != continent:
                continue
            lead = (row["candidate_leads_to_verify"][0]["name"] if row["candidate_leads_to_verify"]
                    else f"expand {row['live_genres'][0]['name']} history" if row["live_genres"]
                    else "archive survey needed")
            lead = lead.replace("|", "\\|")
            if row["first_access_urls"]:
                source = row["first_access_urls"][0]
                access = f"{lead}; [inspect source]({source['url']})"
            else:
                access = lead
            star = " *" if row["map_scope_review"] else ""
            lines.append(f"| {row['name']} ({row['code']}){star} | {len(row['live_genres'])} | "
                         f"{decade_ranges(row['decades_without_live_genre'])} | {access} |")
        lines.append("")
    lines += ["* Scope review required.", "", "## Source material that would accelerate the audit", "",
              "If you already have lawful access, a **private** research copy or bibliographic pages from these sources would help. "
              "Do not place full copyrighted books in `web/`; record only short paraphrases and citations in dossiers.", "",
              "1. *The Garland Encyclopedia of World Music*: Africa (vol. 1), Southeast Asia (vol. 4), South Asia (vol. 5), Middle East/Central Asia (vol. 6), East Asia (vol. 7). "
              "[Publisher series](https://www.routledge.com/Garland-Encyclopedia-of-World-Music/book-series/TFSE00091). These provide country and community histories and bibliographies.",
              "2. *Bloomsbury Encyclopedia of Popular Music of the World*, vol. 6 (Africa/Middle East locations) and vol. 12 (Sub-Saharan African genres). "
              "[Vol. 6](https://www.bloomsbury.com/us/bloomsbury-encyclopedia-of-popular-music-of-the-world-volume-6-9781501324468/), "
              "[vol. 12](https://www.bloomsbury.com/us/bloomsbury-encyclopedia-of-popular-music-of-the-world-volume-12-9781501342028/). These help with twentieth-century genre chronology and named practitioners.",
              "3. For countries with no dossier or thin early-decade evidence, country-specific academic articles, discographies, radio catalogues and field recordings are more valuable than another broad encyclopedia. "
              "Prioritize a scan or citation for the relevant chapter/decade, including title, author, edition, page numbers, and access rights.", "",
              "Store privately supplied files in a user-approved research intake location; only source metadata and paraphrased findings enter the public catalog.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = build()
    json_path = RESEARCH / "country_decade_plan.json"
    md_path = ROOT / "COUNTRY_DECADE_RESEARCH_PLAN.md"
    json_text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    md_text = render_markdown(data) + "\n"
    if args.check:
        assert json_path.read_text() == json_text
        assert md_path.read_text() == md_text
    else:
        json_path.write_text(json_text, encoding="utf-8")
        md_path.write_text(md_text, encoding="utf-8")
    print(f"{len(data['countries'])} area plans; "
          f"{sum(len(row['currently_visible_decades']) for row in data['countries'])}/1391 evidence-anchored decade cells")


if __name__ == "__main__":
    main()
