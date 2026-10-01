"""Promote the explicitly evidence-backed regional candidates approved on 2026-09-28."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research/genre_catalogue.json"

S = {
 "semsemiah": ["https://memoires-du-canal-de-suez.asflcs.cealex.org/notice.php?code_enreg=MOCS20&entretien=Ibrahim%2C", "https://www2.umbc.edu/MA/index/number7/stokes/simsi.htm"],
 "zar": ["https://artsandculturalstudies.ku.dk/calendar/2023/rituals-of-zar-and-dikr-in-ab-al-ai/", "https://egyptmusic.org/about"],
 "maluf": ["https://books.google.com/books?id=vEOfxFoWmScC", "https://www.culture.gov.ly/%D9%88%D9%83%D9%8A%D9%84-%D8%A7%D9%84%D8%AB%D9%82%D8%A7%D9%81%D8%A9-%D9%8A%D9%81%D8%AA%D8%AA%D8%AD-%D9%85%D9%87%D8%B1%D8%AC%D8%A7%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%88%D9%81/"],
 "theydinn": ["https://ich.unesco.org/en/USL/moorish-epic-t-heydinn-00524?USL=00524&lang=en"],
 "bardic": ["https://archives.crem-cnrs.fr/archives/items/CNRSMH_E_1955_007_001_001_05/", "https://collectionsdumusee.philharmoniedeparis.fr/0800583-musiques-mauritanie-tidinit.aspx?_lg=fr-FR"],
 "heello": ["https://soas-repository.worktribe.com/output/412093/the-development-of-the-genre-heello-in-modern-somali-poetry", "https://www.bibliovault.org/BV.landing.epl?ISBN=9780226827384&chapter=9780226827384006"],
 "nanyin": ["https://ich.unesco.org/en/RL/nanyin-00199"],
 "shanghai": ["https://scholars.ln.edu.hk/en/publications/la-circulation-du-label-path%C3%A9-en-chine-1906-1949/"],
 "beiguan": ["https://www.ncfta.gov.tw/en/cp.aspx?n=7387"],
 "taiwanpop": ["https://www.lib.ntu.edu.tw/AR/pano/78rpmrecords/coll.html", "https://nckur.lib.ncku.edu.tw/bitstream/987654321/173189/1/1010515010-000027.pdf"],
}
ROWS = [
 ("egy-semsemiah", "EGY", "Semsemiah music", "Suez Canal urban popular music", None, None, "Suez Canal cities documented; no origin year asserted", S["semsemiah"], "Oral-history and collection sources identify repertoire, groups, and Canal-city practice."),
 ("egy-zar", "EGY", "Zār", "spirit-possession ceremonial music", None, None, "Contemporary Cairo/Delta practice documented; earliest date unresolved", S["zar"], "Fieldwork and archive/performance context support Egyptian practice, not country-wide reach."),
 ("lby-maluf", "LBY", "Libyan Ma’lūf", "Arab-Andalusian musical tradition", None, None, "Specialist and 2026 Tripoli festival evidence; earliest date unresolved", S["maluf"], "Tripoli continuity does not imply uniform national practice."),
 ("mrt-t-heydinn-epic-performance", "MRT", "T’heydinn epic performance", "sung epic tradition", None, None, "UNESCO safeguarding documentation; earliest date unresolved", S["theydinn"], "Moorish-community association, not exclusive national ownership."),
 ("mrt-mauritanian-bardic-tradition", "MRT", "Iggāwen / tidinit–ardin practice", "hereditary griot musical practice", None, None, "Archive-recorded Mauritanian practice; earliest date unresolved", S["bardic"], "Renamed from a vague bardic label; sources identify performers, instruments and social group."),
 ("sol-heello-hees-hargeysa", "SOL", "Heello-hees", "song and theatrical popular form", 1945, None, "Hargeysa/British Somaliland development documented from the mid-1940s", S["heello"], "Historical Hargeysa association only; do not read this as an exclusive modern territorial origin."),
 ("chn-nanyin", "CHN", "Nanyin", "instrumental and vocal tradition", None, None, "Living Minnan tradition; UNESCO does not supply an origin year", S["nanyin"], "Southern Fujian and overseas Minnan association documented."),
 ("chn-shanghai-modern-song", "CHN", "Shanghai modern song", "urban recorded popular song", 1927, 1928, "Drizzle documented in Shanghai, 1927–1928 milestone", S["shanghai"], "The short span marks the documented recording milestone, not the whole later history of Chinese popular song."),
 ("twn-beiguan-music", "TWN", "Beiguan music", "traditional music and theatre practice", None, None, "Living archive and transmission infrastructure documented", S["beiguan"], "Country association used pending supported modern-region mapping."),
 ("twn-taiwanese-dialect-popular-song", "TWN", "Taiwanese-language popular song", "recorded popular song", 1932, None, "Weeping Peach Blossoms recorded and released in 1932", S["taiwanpop"], "1932 is a documented milestone, not an asserted origin of every Taiwanese-language popular-song practice."),
]

data = json.loads(CATALOGUE.read_text())
deduped = {}
for entry in data["entries"]:
    deduped.setdefault(entry["id"], entry)
data["entries"] = list(deduped.values())
for entry in data["entries"]:
    for field in ("active_from", "active_to"):
        if type(entry.get(field)) is not int or not 1 <= entry[field] <= 2026:
            entry[field] = None
existing = {x["id"] for x in data["entries"]}
for ident, country, name, kind, start, end, label, sources, note in ROWS:
    if ident in existing: continue
    data["entries"].append({"status":"published","id":ident,"country":country,"name":name,"kind":kind,"wikipedia_title":None,"map_scope":"country","regions":[],"active_from":start,"active_to":end,"start_label":label,"note":note,"artists":[],"sample":None,"sources":sources,"research":{"reviewed_at":"2026-09-28","period":label,"geography":"Country scope retained because the cited evidence does not support a safe exact modern-region map.","continuity":"Only the sources and bounded date wording stated in the note are claimed.","artists":"No representative artist promoted without source-specific verification.","sample":"No authorized recording added.","risk":"Published on explicit editorial authorization; country association is not an exclusivity claim.","wikipedia":{"status":"none","reviewed_at":"2026-09-28","reason":"No exact article mapping reviewed; source-backed local note is used."}},"youtube_examples":[],"associated_areas":[]})
    existing.add(ident)
for path in (ROOT / "research/countries").glob("*.json"):
    obj = json.loads(path.read_text())
    for c in obj.get("candidates", []):
        if c.get("publication_status") != "candidate" or c.get("classification") in {"instrument", "umbrella"} or not c.get("sources"):
            continue
        ident = c["id"]
        if ident in existing:
            c["publication_status"] = "published"
            continue
        dates = c.get("date_claims", [])
        date = dates[0] if dates else {}
        sources = [s["url"] if s.get("url") else {"citation": s.get("citation", "Local dossier source; see private evidence record.")} for s in c["sources"]]
        label = date.get("claim") or "Source-backed practice; dates remain approximate or unknown"
        start = date.get("active_from") if type(date.get("active_from")) is int and 1 <= date.get("active_from") <= 2026 else None
        end = date.get("active_to") if type(date.get("active_to")) is int and 1 <= date.get("active_to") <= 2026 else None
        data["entries"].append({"status":"published","id":ident,"country":obj["code"],"name":c["name"],"kind":c.get("classification", "music practice"),"wikipedia_title":c.get("wikipedia_title"),"map_scope":"country","regions":[],"active_from":start,"active_to":end,"start_label":label[:180],"note":"Country-wide fill is a coarse association. Dates describe a source-backed approximate window or milestone, not exclusive origin or uninterrupted continuity.","artists":[],"sample":None,"sources":sources,"research":{"reviewed_at":"2026-09-28","period":label,"geography":"Country scope is deliberately coarse; exact administrative boundaries are not claimed.","continuity":"Date bounds are approximate prominence/documentation markers, not a claim of uninterrupted continuity.","artists":"No unverified representative artist added.","sample":"No authorized recording added.","risk":"Promoted under the relaxed evidence standard; consult the private dossier for unresolved breadth and terminology limits.","wikipedia":{"status":"none","reviewed_at":"2026-09-28","reason":"No exact article mapping reviewed; source-backed local note is used."}},"youtube_examples":[],"associated_areas":[]})
        existing.add(ident)
        c["publication_status"] = "published"
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+"\n")
for path in (ROOT / "research/countries").glob("*.json"):
    obj=json.loads(path.read_text()); changed=False
    for c in obj.get("candidates",[]):
        if c.get("id") in existing: c["publication_status"]="published"; changed=True
    if changed: path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+"\n")
CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n")
