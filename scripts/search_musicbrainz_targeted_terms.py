"""Search user-supplied genre variants in local MusicBrainz dump tables."""
from __future__ import annotations

import csv
import difflib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TERMS = ROOT / "research/musicbrainz_targeted_search_terms.json"
PROMOTIONS = ROOT / "research/musicbrainz_promoted_relationships.json"
TABLES = ROOT / ".local/musicbrainz/dumps/mbdump.tar.bz2.tables"
DERIVED = ROOT / ".local/musicbrainz/dumps/mbdump-derived.tar.bz2.tables"
OUT = ROOT / ".local/musicbrainz/targeted_term_results.json"
CSV_OUT = ROOT / ".local/musicbrainz/targeted_term_results.csv"


def norm(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def score(query, value):
    left, right = norm(query), norm(value)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if left in right or right in left:
        return 0.92 * min(len(left), len(right)) / max(len(left), len(right)) + 0.08
    return difflib.SequenceMatcher(None, left, right).ratio()


def grams(value):
    value = norm(value).replace(" ", "_")
    return {value[i:i+3] for i in range(max(1, len(value)-2))}


def plausible(query, value, fraction=.35):
    left, right = grams(query), grams(value)
    return bool(left and right and len(left & right) >= max(1, round(len(left) * fraction)))


def read_tsv(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            yield [None if value == r"\N" else value for value in line.rstrip("\n").split("\t")]


def main():
    config = json.loads(TERMS.read_text(encoding="utf-8"))
    promotions = json.loads(PROMOTIONS.read_text(encoding="utf-8"))
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"searches":[]}
    previous_recordings = defaultdict(list)
    for search in previous.get("searches",[]):
        for match in search.get("matches",[]):
            if match["entity_type"]=="recording":
                match.setdefault("musicbrainz_id",match.get("mbid",""))
                previous_recordings[search["atlas_id"]].append(match)
    catalogue = {e["id"]: e for e in json.loads((ROOT/"research/genre_catalogue.json").read_text(encoding="utf-8"))["entries"]}
    tag_rows = [{"id":int(r[0]),"name":r[1],"ref_count":int(r[2] or 0)} for r in read_tsv(DERIVED/"tag")]
    tag_grams=defaultdict(set)
    for index,tag in enumerate(tag_rows):
        for gram in grams(tag["name"]): tag_grams[gram].add(index)
    results = {"generated_at":date.today().isoformat(),"status":"pending_validation","searches":[]}
    by_atlas = {}
    for entry in config["entries"]:
        for atlas_id in entry["atlas_ids"]:
            genre = catalogue[atlas_id]
            row = {"atlas_id":atlas_id,"country":genre["country"],"atlas_name":genre["name"],
                   "terms":entry["terms"],"requested_entity_search":entry.get("entity_search",[]),"matches":[]}
            for term in entry["terms"]:
                candidates=[]
                overlaps=Counter(index for gram in grams(term) for index in tag_grams[gram])
                minimum=max(1,round(len(grams(term))*.35))
                for index,count in overlaps.items():
                    if count < minimum: continue
                    tag=tag_rows[index]
                    similarity=score(term,tag["name"])
                    if similarity >= .72:
                        candidates.append((similarity,tag["ref_count"],tag))
                for similarity,_,tag in sorted(candidates,reverse=True,key=lambda x:(x[0],x[1]))[:5]:
                    row["matches"].append({"entity_type":"tag","query":term,"name":tag["name"],
                        "musicbrainz_id":str(tag["id"]),"similarity":round(similarity,4),
                        "ref_count":tag["ref_count"],"decision":"pending","review_note":""})
            by_atlas[atlas_id]=row; results["searches"].append(row)
    artist_entries=[e for e in config["entries"] if "artist" in e.get("entity_search",[])]
    artist_hits=defaultdict(list)
    for r in read_tsv(TABLES/"artist"):
        artist_name=r[2]
        fields=(r[2],r[3],r[13] or "")
        searchable=" ".join(fields).casefold()
        if not any(key in searchable for key in ("turan","tұran","тұран","yalla","ялла","farrukh","zakirov","zokirov","закиров")):
            continue
        for entry in artist_entries:
            possible=[]
            for term in entry["terms"]:
                for field in fields:
                    if term.casefold() == field.casefold() or (norm(term) and norm(term) == norm(field)):
                        possible.append((1.0,term))
                    elif norm(term) and set(norm(term).split()) == set(norm(field).split()):
                        possible.append((.99,term))
                    elif term.casefold() in field.casefold():
                        possible.append((.94,term))
                    elif plausible(term,field):
                        possible.append((score(term,field),term))
            if not possible: continue
            best=max(possible)
            if best[0] >= .78:
                for atlas_id in entry["atlas_ids"]:
                    artist_hits[atlas_id].append((best[0],artist_name,r[1],best[1],r[13] or ""))
    for atlas_id,hits in artist_hits.items():
        for similarity,name,mbid,query,comment in sorted(hits,reverse=True)[:20]:
            by_atlas[atlas_id]["matches"].append({"entity_type":"artist","query":query,"name":name,
                "musicbrainz_id":mbid,"similarity":round(similarity,4),"comment":comment,
                "decision":"pending","review_note":""})
    recording_entries=[e for e in config["entries"] if "recording" in e.get("entity_search",[])]
    recording_hits=defaultdict(list)
    if recording_entries and not any(previous_recordings.values()):
        for r in read_tsv(TABLES/"recording"):
            recording_name=r[2]
            if "arirang" not in norm(recording_name) and "아리랑" not in recording_name:
                continue
            for entry in recording_entries:
                possible=[term for term in entry["terms"] if plausible(term,recording_name,.5)]
                if not possible: continue
                best=max((score(term,recording_name),term) for term in possible)
                if best[0] >= .88:
                    for atlas_id in entry["atlas_ids"]:
                        recording_hits[atlas_id].append((best[0],recording_name,r[1],best[1],r[5] or ""))
        for atlas_id,hits in recording_hits.items():
            for similarity,name,mbid,query,comment in sorted(hits,reverse=True)[:50]:
                by_atlas[atlas_id]["matches"].append({"entity_type":"recording","query":query,"name":name,
                    "musicbrainz_id":mbid,"similarity":round(similarity,4),"comment":comment,
                    "decision":"pending","review_note":""})
    else:
        for atlas_id,matches in previous_recordings.items():
            by_atlas[atlas_id]["matches"].extend(matches)
    for cache in sorted((ROOT/".local/musicbrainz").glob("arirang_works_*.json")):
        payload=json.loads(cache.read_text(encoding="utf-8"))
        query=cache.stem.removeprefix("arirang_works_").replace("_"," ")
        for work in payload.get("works",[]):
            title=work.get("title","")
            for entry in (e for e in config["entries"] if "work" in e.get("entity_search",[])):
                similarity=max(score(term,title) for term in entry["terms"])
                if similarity < .65: continue
                for atlas_id in entry["atlas_ids"]:
                    if any(m["entity_type"]=="work" and m["musicbrainz_id"]==work["id"] for m in by_atlas[atlas_id]["matches"]): continue
                    by_atlas[atlas_id]["matches"].append({"entity_type":"work","query":query,"name":title,
                        "musicbrainz_id":work["id"],"similarity":round(similarity,4),
                        "comment":work.get("disambiguation","") or "","decision":"pending","review_note":""})
    for search in results["searches"]:
        for match in search["matches"]:
            identifier=match.pop("musicbrainz_id","")
            match["tag_id"]=identifier if match["entity_type"]=="tag" else ""
            match["mbid"]="" if match["entity_type"]=="tag" else identifier
            match["relationship"]="related"
            for rule in promotions["rules"]:
                if search["atlas_id"] not in rule["atlas_ids"] or match["entity_type"] != rule["entity_type"]:
                    continue
                name_match=not rule.get("result_names") or match["name"].casefold() in {name.casefold() for name in rule["result_names"]}
                id_match=not rule.get("mbids") or match["mbid"] in rule["mbids"]
                if name_match and id_match:
                    match["decision"]=rule["decision"]; match["relationship"]=rule["relationship"]; match["review_note"]=rule["note"]
            if search["atlas_id"] in {"prk-arirang","kor-arirang"}:
                lower=match["name"].casefold()
                if match["entity_type"]=="recording":
                    match["decision"]="retain_candidate"
                    match["relationship"]="regional_variant" if lower.startswith(("jindo arirang","jeongseon arirang")) else "example_recording"
                    match["review_note"]="Verify performer, repertoire, language, and work relationship."
                elif match["entity_type"]=="work":
                    match["relationship"]="related"
                    if match.get("comment")=="Soul Edge" or lower.startswith("horangi arirang"):
                        match["decision"]="reject_identity"; match["review_note"]="Title alone does not establish traditional repertoire; comment identifies Soul Edge."
                    elif lower.startswith("echoes of arirang"):
                        match["decision"]="investigate_inspiration"; match["review_note"]="Possibly inspired by the tradition; not equivalent identity."
                    elif "schindler" in match.get("comment","").casefold():
                        match["decision"]="retain_arrangement"; match["review_note"]="Arrangement/example, not identity of the whole tradition."
                    else:
                        match["decision"]="inspect_work"; match["review_note"]="Inspect composer, traditional attribution, language, aliases, and recording relationships."
    results["summary"]={"atlas_records":len(results["searches"]),
        "records_with_matches":sum(bool(r["matches"]) for r in results["searches"]),
        "matches_by_type":dict(sorted((kind,sum(m["entity_type"]==kind for r in results["searches"] for m in r["matches"])) for kind in ("tag","artist","recording","work")))}
    OUT.write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with CSV_OUT.open("w",encoding="utf-8",newline="") as stream:
        fields=("country","atlas_id","atlas_name","entity_type","relationship","query","result_name","tag_id","mbid","similarity","ref_count","comment","decision","review_note")
        writer=csv.DictWriter(stream,fieldnames=fields); writer.writeheader()
        for search in results["searches"]:
            for match in search["matches"]:
                writer.writerow({"country":search["country"],"atlas_id":search["atlas_id"],"atlas_name":search["atlas_name"],
                    "entity_type":match["entity_type"],"query":match["query"],"result_name":match["name"],
                    "relationship":match["relationship"],"tag_id":match["tag_id"],"mbid":match["mbid"],"similarity":match["similarity"],
                    "ref_count":match.get("ref_count",""),"comment":match.get("comment",""),"decision":match["decision"],"review_note":match["review_note"]})
    print(json.dumps(results["summary"],indent=2)); print(OUT); print(CSV_OUT)


if __name__ == "__main__": main()
