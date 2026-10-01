"""Build a private, reviewable MusicBrainz genre catalogue from official dumps.

The pipeline deliberately treats MusicBrainz tags as discovery signals, not as
editorial proof that an artist or recording represents an Atlas genre.
"""
from __future__ import annotations

import argparse
import bz2
import csv
import json
import re
import sqlite3
import tarfile
import tempfile
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DERIVED = ROOT / ".local/musicbrainz/dumps/mbdump-derived.tar.bz2"
DEFAULT_CORE = ROOT / ".local/musicbrainz/dumps/mbdump.tar.bz2"
DEFAULT_DB = ROOT / ".local/musicbrainz/catalog.sqlite3"
DEFAULT_OUT = ROOT / ".local/musicbrainz/catalog.json"
DEFAULT_RYM_CANDIDATES = ROOT / ".local/musicbrainz/rym_album_candidates.csv"
MAPPINGS = ROOT / "research/musicbrainz_genre_mappings.json"


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def rows(archive: Path, member_name: str):
    """Stream a MusicBrainz COPY-format table from a compressed tarball."""
    cached = archive.parent / f"{archive.name}.tables" / member_name
    derived_cached = DEFAULT_DERIVED.parent / f"{DEFAULT_DERIVED.name}.tables" / member_name
    if not cached.exists() and archive == DEFAULT_CORE and derived_cached.exists():
        cached = derived_cached
    if cached.exists():
        with cached.open("r", encoding="utf-8") as stream:
            for raw in stream:
                yield [None if cell == r"\N" else cell for cell in raw.rstrip("\n").split("\t")]
        return
    wanted = f"mbdump/{member_name}"
    with tarfile.open(archive, "r:bz2") as tf:
        member = tf.getmember(wanted)
        stream = tf.extractfile(member)
        assert stream is not None
        for raw in stream:
            yield [None if cell == r"\N" else cell for cell in raw.decode("utf-8").rstrip("\n").split("\t")]


def ensure_tables(archive: Path, names):
    """Extract a fixed allow-list in one bzip2 pass; existing tables are resumable."""
    destination = archive.parent / f"{archive.name}.tables"
    destination.mkdir(parents=True, exist_ok=True)
    missing = set(names) - {p.name for p in destination.iterdir() if p.is_file()}
    if not missing:
        return
    print(f"extracting {len(missing)} tables from {archive.name} in one pass", flush=True)
    with tarfile.open(archive, "r|bz2") as tf:
        for member in tf:
            name = member.name.removeprefix("mbdump/")
            if name not in missing or not member.isfile():
                continue
            source = tf.extractfile(member)
            assert source is not None
            target = destination / name
            with tempfile.NamedTemporaryFile("wb", dir=destination, delete=False) as output:
                while block := source.read(1024 * 1024):
                    output.write(block)
                temporary = Path(output.name)
            temporary.replace(target)
            missing.remove(name)
            print(f"  extracted {name}", flush=True)
            if not missing:
                break
    if missing:
        raise SystemExit("dump is missing required tables: " + ", ".join(sorted(missing)))


def atlas_genres():
    payload = json.loads((ROOT / "research/genre_catalogue.json").read_text(encoding="utf-8"))
    return [entry for entry in payload["entries"] if entry["status"] == "published"]


def connect(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    return db


def init(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS atlas_genre(
      id TEXT PRIMARY KEY, name TEXT NOT NULL, country TEXT NOT NULL,
      active_from INTEGER, active_to INTEGER, tag_id INTEGER, tag_name TEXT,
      popularity INTEGER NOT NULL DEFAULT 0, selected INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS tag_entity(
      genre_id TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id INTEGER NOT NULL,
      score INTEGER NOT NULL, PRIMARY KEY(genre_id, entity_type, entity_id));
    CREATE TABLE IF NOT EXISTS artist(
      id INTEGER PRIMARY KEY, mbid TEXT, name TEXT, sort_name TEXT, type_id INTEGER,
      area_id INTEGER, begin_area_id INTEGER, end_area_id INTEGER, begin_year INTEGER,
      end_year INTEGER, comment TEXT, gender_id INTEGER);
    CREATE TABLE IF NOT EXISTS artist_alias(artist_id INTEGER, name TEXT, locale TEXT,
      sort_name TEXT, primary_locale INTEGER, PRIMARY KEY(artist_id,name,locale));
    CREATE TABLE IF NOT EXISTS artist_identifier(artist_id INTEGER, kind TEXT, value TEXT,
      PRIMARY KEY(artist_id,kind,value));
    CREATE TABLE IF NOT EXISTS genre_artist(
      genre_id TEXT, artist_id INTEGER, score INTEGER, basis TEXT,
      PRIMARY KEY(genre_id,artist_id,basis));
    CREATE TABLE IF NOT EXISTS artist_credit_artist(
      credit_id INTEGER, position INTEGER, artist_id INTEGER, credited_name TEXT, join_phrase TEXT,
      PRIMARY KEY(credit_id,position));
    CREATE TABLE IF NOT EXISTS recording(
      id INTEGER PRIMARY KEY, mbid TEXT, title TEXT, credit_id INTEGER, duration_ms INTEGER,
      comment TEXT, video INTEGER, year INTEGER, month INTEGER, day INTEGER);
    CREATE TABLE IF NOT EXISTS genre_recording(
      genre_id TEXT, recording_id INTEGER, score INTEGER, basis TEXT,
      PRIMARY KEY(genre_id,recording_id,basis));
    CREATE TABLE IF NOT EXISTS release_group(
      id INTEGER PRIMARY KEY, mbid TEXT, title TEXT, credit_id INTEGER, type_id INTEGER,
      comment TEXT, first_year INTEGER);
    CREATE TABLE IF NOT EXISTS release(
      id INTEGER PRIMARY KEY, mbid TEXT, title TEXT, credit_id INTEGER, release_group_id INTEGER,
      status_id INTEGER, language_id INTEGER, barcode TEXT, comment TEXT);
    CREATE TABLE IF NOT EXISTS label(
      id INTEGER PRIMARY KEY, mbid TEXT, name TEXT, type_id INTEGER, area_id INTEGER,
      label_code INTEGER, begin_year INTEGER, end_year INTEGER, comment TEXT);
    CREATE TABLE IF NOT EXISTS release_label(
      release_id INTEGER, label_id INTEGER, catalog_number TEXT, PRIMARY KEY(release_id,label_id,catalog_number));
    CREATE TABLE IF NOT EXISTS recording_release(
      recording_id INTEGER, release_id INTEGER, track_number TEXT, track_title TEXT,
      PRIMARY KEY(recording_id,release_id,track_number));
    CREATE TABLE IF NOT EXISTS instrument(
      id INTEGER PRIMARY KEY, mbid TEXT, name TEXT, type_id INTEGER, comment TEXT, description TEXT);
    CREATE TABLE IF NOT EXISTS artist_instrument(
      artist_id INTEGER, instrument_id INTEGER, link_id INTEGER, PRIMARY KEY(artist_id,instrument_id,link_id));
    CREATE TABLE IF NOT EXISTS event(
      id INTEGER PRIMARY KEY, mbid TEXT, name TEXT, begin_year INTEGER, end_year INTEGER,
      type_id INTEGER, cancelled INTEGER, setlist TEXT, comment TEXT);
    CREATE TABLE IF NOT EXISTS artist_event(
      artist_id INTEGER, event_id INTEGER, link_id INTEGER, PRIMARY KEY(artist_id,event_id,link_id));
    CREATE TABLE IF NOT EXISTS place(
      id INTEGER PRIMARY KEY, mbid TEXT, name TEXT, type_id INTEGER, address TEXT,
      area_id INTEGER, coordinates TEXT, comment TEXT);
    CREATE TABLE IF NOT EXISTS artist_place(
      artist_id INTEGER, place_id INTEGER, link_id INTEGER, PRIMARY KEY(artist_id,place_id,link_id));
    CREATE TABLE IF NOT EXISTS area(id INTEGER PRIMARY KEY, mbid TEXT, name TEXT, type_id INTEGER, comment TEXT);
    CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS artist_credit_artist_credit_idx ON artist_credit_artist(credit_id);
    CREATE INDEX IF NOT EXISTS artist_credit_artist_artist_idx ON artist_credit_artist(artist_id);
    CREATE INDEX IF NOT EXISTS recording_credit_idx ON recording(credit_id);
    CREATE INDEX IF NOT EXISTS genre_artist_genre_idx ON genre_artist(genre_id,artist_id);
    CREATE INDEX IF NOT EXISTS genre_recording_genre_idx ON genre_recording(genre_id,recording_id);
    CREATE INDEX IF NOT EXISTS recording_release_recording_idx ON recording_release(recording_id);
    """)


def index_derived(args):
    derived_tables = ["tag"] + [f"{kind}_tag" for kind in ("artist", "recording", "release_group", "release", "label", "event", "instrument", "place")]
    ensure_tables(args.derived, derived_tables)
    genres = atlas_genres()
    mapping_payload = json.loads(MAPPINGS.read_text(encoding="utf-8")) if MAPPINGS.exists() else {"mappings": []}
    curated = {atlas_id: mapping for mapping in mapping_payload["mappings"] for atlas_id in mapping["atlas_ids"]}
    candidates = defaultdict(list)
    for genre in genres:
        candidates[norm(genre["name"])].append(genre)
        title = genre.get("wikipedia_title")
        if title and norm(title) != norm(genre["name"]):
            candidates[norm(title)].append(genre)
        mapping = curated.get(genre["id"])
        if mapping and mapping.get("dump_tag"):
            candidates[norm(mapping["dump_tag"])].append(genre)
    tags = {}
    for row in rows(args.derived, "tag"):
        if norm(row[1]) in candidates:
            tags[int(row[0])] = row[1]
    matched = {}
    for tag_id, tag_name in tags.items():
        for genre in candidates[norm(tag_name)]:
            matched.setdefault(genre["id"], (tag_id, tag_name))
    db = connect(args.db)
    init(db)
    db.execute("DELETE FROM atlas_genre")
    db.execute("DELETE FROM tag_entity")
    for genre in genres:
        tag = matched.get(genre["id"])
        db.execute("INSERT INTO atlas_genre(id,name,country,active_from,active_to,tag_id,tag_name) VALUES(?,?,?,?,?,?,?)",
                   (genre["id"], genre["name"], genre["country"], genre.get("active_from"), genre.get("active_to"),
                    tag[0] if tag else None, tag[1] if tag else None))
    tag_to_genre = defaultdict(list)
    for genre_id, (tag_id, _) in matched.items():
        tag_to_genre[tag_id].append(genre_id)
    for entity_type in ("artist", "recording", "release_group", "release", "label", "event", "instrument", "place"):
        member = f"{entity_type}_tag"
        batch = []
        for row in rows(args.derived, member):
            tag_id, count = int(row[1]), int(row[2])
            if count <= 0 or tag_id not in tag_to_genre:
                continue
            for genre_id in tag_to_genre[tag_id]:
                batch.append((genre_id, entity_type, int(row[0]), count))
            if len(batch) >= 10000:
                db.executemany("INSERT OR REPLACE INTO tag_entity VALUES(?,?,?,?)", batch); batch.clear()
        db.executemany("INSERT OR REPLACE INTO tag_entity VALUES(?,?,?,?)", batch)
        db.commit()
    db.execute("UPDATE atlas_genre SET popularity=COALESCE((SELECT SUM(score) FROM tag_entity WHERE genre_id=atlas_genre.id),0)")
    db.execute("UPDATE atlas_genre SET selected=0")
    db.execute("UPDATE atlas_genre SET selected=1 WHERE id IN (SELECT id FROM atlas_genre WHERE tag_id IS NOT NULL ORDER BY popularity DESC,name LIMIT ?)", (args.top_genres,))
    db.execute("INSERT OR REPLACE INTO metadata VALUES('derived_snapshot',?)", (args.snapshot,))
    db.commit()
    stats = db.execute("SELECT COUNT(*),SUM(selected) FROM atlas_genre WHERE tag_id IS NOT NULL").fetchone()
    print(f"matched {stats[0]} Atlas genres; selected top {stats[1]} for the compact catalogue")


def selected_sets(db):
    genres = {r[0] for r in db.execute("SELECT id FROM atlas_genre WHERE selected=1")}
    by_type = defaultdict(set)
    for genre, kind, entity in db.execute("SELECT genre_id,entity_type,entity_id FROM tag_entity WHERE genre_id IN (SELECT id FROM atlas_genre WHERE selected=1)"):
        by_type[kind].add(entity)
    return genres, by_type


def import_core(args):
    core_tables = ("recording release_group release artist_credit_name artist artist_ipi artist_isni artist_alias "
                   "l_artist_instrument l_artist_event l_artist_place instrument event place area track medium "
                   "release_label label").split()
    ensure_tables(args.core, core_tables)
    ensure_tables(DEFAULT_DERIVED, ("release_group_meta",))
    db = connect(args.db); init(db)
    genres, targets = selected_sets(db)
    if not genres:
        raise SystemExit("no selected genres; run index-derived first")
    direct_artists = targets["artist"]
    # Artist-credit membership is the bridge from tagged works to their performers.
    wanted_credits = set()
    entity_credits = {"recording": {}, "release_group": {}, "release": {}}
    recording_seed = targets["recording"]
    release_group_seed = targets["release_group"]
    release_seed = targets["release"]
    for row in rows(args.core, "recording"):
        if int(row[0]) in recording_seed:
            wanted_credits.add(int(row[3])); entity_credits["recording"][int(row[0])] = int(row[3])
    for member, seed, credit_pos in (("release_group", release_group_seed, 3), ("release", release_seed, 3)):
        for row in rows(args.core, member):
            if int(row[0]) in seed:
                wanted_credits.add(int(row[credit_pos])); entity_credits[member][int(row[0])] = int(row[credit_pos])
    credit_rows = []
    associated_artists = set(direct_artists)
    for row in rows(args.core, "artist_credit_name"):
        if int(row[0]) in wanted_credits:
            credit_rows.append((int(row[0]), int(row[1]), int(row[2]), row[3], row[4] or "")); associated_artists.add(int(row[2]))
    db.executemany("INSERT OR REPLACE INTO artist_credit_artist VALUES(?,?,?,?,?)", credit_rows)
    db.commit()
    # Attribute artists discovered through a tagged work to that genre, preserving basis.
    for genre, kind, entity, score in db.execute("SELECT genre_id,entity_type,entity_id,score FROM tag_entity WHERE genre_id IN (SELECT id FROM atlas_genre WHERE selected=1)"):
        if kind == "artist":
            db.execute("INSERT OR REPLACE INTO genre_artist VALUES(?,?,?,?)", (genre, entity, score, "artist tag"))
        elif kind in entity_credits and entity in entity_credits[kind]:
            credit = entity_credits[kind][entity]
            for artist in (r[2] for r in credit_rows if r[0] == credit):
                db.execute("INSERT OR REPLACE INTO genre_artist VALUES(?,?,?,?)", (genre,artist,score,f"{kind} tag credit"))
    artist_batch = []
    for r in rows(args.core, "artist"):
        if int(r[0]) in associated_artists:
            artist_batch.append((int(r[0]),r[1],r[2],r[3],r[10] and int(r[10]),r[11] and int(r[11]),r[17] and int(r[17]),r[18] and int(r[18]),r[4] and int(r[4]),r[7] and int(r[7]),r[13],r[12] and int(r[12])))
    db.executemany("INSERT OR REPLACE INTO artist VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", artist_batch)
    for member, kind in (("artist_ipi","ipi"),("artist_isni","isni")):
        db.executemany("INSERT OR IGNORE INTO artist_identifier VALUES(?,?,?)",
                       ((int(r[0]),kind,r[1]) for r in rows(args.core, member) if int(r[0]) in associated_artists))
    alias_batch = []
    for r in rows(args.core, "artist_alias"):
        if int(r[1]) in associated_artists:
            alias_batch.append((int(r[1]),r[2],r[3] or "",r[7],1 if r[14] == "t" else 0))
    db.executemany("INSERT OR IGNORE INTO artist_alias VALUES(?,?,?,?,?)", alias_batch)
    db.commit()
    # All recordings credited to any selected artist are the artist-based search result.
    artist_credits = set()
    all_credit_rows = []
    for r in rows(args.core, "artist_credit_name"):
        if int(r[2]) in associated_artists:
            artist_credits.add(int(r[0])); all_credit_rows.append((int(r[0]),int(r[1]),int(r[2]),r[3],r[4] or ""))
    db.executemany("INSERT OR REPLACE INTO artist_credit_artist VALUES(?,?,?,?,?)", all_credit_rows)
    recording_batch=[]
    for r in rows(args.core, "recording"):
        if int(r[0]) in recording_seed or int(r[3]) in artist_credits:
            recording_batch.append((int(r[0]),r[1],r[2],int(r[3]),r[4] and int(r[4]),r[5],1 if r[8]=="t" else 0,None,None,None))
    db.executemany("INSERT OR REPLACE INTO recording VALUES(?,?,?,?,?,?,?,?,?,?)", recording_batch)
    db.commit()
    recording_ids={r[0] for r in recording_batch}
    # Genre attribution is explicit: direct recording tag, or an artist tag association.
    for genre, entity, score in db.execute("SELECT genre_id,entity_id,score FROM tag_entity WHERE entity_type='recording' AND genre_id IN (SELECT id FROM atlas_genre WHERE selected=1)"):
        db.execute("INSERT OR REPLACE INTO genre_recording VALUES(?,?,?,?)",(genre,entity,score,"recording tag"))
    for genre, artist, score in db.execute("SELECT genre_id,artist_id,score FROM genre_artist"):
        db.execute("""INSERT OR IGNORE INTO genre_recording
          SELECT ?,r.id,?,'genre-tagged artist credit' FROM recording r JOIN artist_credit_artist a ON a.credit_id=r.credit_id WHERE a.artist_id=?""",(genre,score,artist))
    db.commit()
    # Related entities are bounded to selected artists and selected recordings/releases.
    for member, table, target_type in (("l_artist_instrument","artist_instrument","instrument"),("l_artist_event","artist_event","event"),("l_artist_place","artist_place","place")):
        values=[]
        for r in rows(args.core,member):
            if int(r[2]) in associated_artists:
                values.append((int(r[2]),int(r[3]),int(r[1]))); targets[target_type].add(int(r[3]))
        db.executemany(f"INSERT OR REPLACE INTO {table} VALUES(?,?,?)",values)
    for r in rows(args.core,"instrument"):
        if int(r[0]) in targets["instrument"]:
            db.execute("INSERT OR REPLACE INTO instrument VALUES(?,?,?,?,?,?)",(int(r[0]),r[1],r[2],r[3] and int(r[3]),r[6],r[7]))
    for r in rows(args.core,"event"):
        if int(r[0]) in targets["event"]:
            db.execute("INSERT OR REPLACE INTO event VALUES(?,?,?,?,?,?,?,?,?)",(int(r[0]),r[1],r[2],r[3] and int(r[3]),r[6] and int(r[6]),r[10] and int(r[10]),1 if r[11]=="t" else 0,r[12],r[13]))
    area_ids=set()
    for r in rows(args.core,"place"):
        if int(r[0]) in targets["place"]:
            db.execute("INSERT OR REPLACE INTO place VALUES(?,?,?,?,?,?,?,?)",(int(r[0]),r[1],r[2],r[3] and int(r[3]),r[4],r[5] and int(r[5]),r[6],r[7]));
            if r[5]: area_ids.add(int(r[5]))
    area_ids.update(r[4] for r in artist_batch if r[4]); area_ids.update(r[5] for r in artist_batch if r[5]); area_ids.update(r[6] for r in artist_batch if r[6])
    for r in rows(args.core,"area"):
        if int(r[0]) in area_ids:
            db.execute("INSERT OR REPLACE INTO area VALUES(?,?,?,?,?)",(int(r[0]),r[1],r[2],r[3] and int(r[3]),r[13]))
    # Resolve releases containing selected recordings, then their release groups and labels.
    medium_ids=set(); recording_medium=[]
    for r in rows(args.core,"track"):
        if int(r[2]) in recording_ids:
            medium_ids.add(int(r[3])); recording_medium.append((int(r[2]),int(r[3]),r[5],r[6]))
    release_ids=set(release_seed)
    medium_release={}
    for r in rows(args.core,"medium"):
        if int(r[0]) in medium_ids:
            release_ids.add(int(r[1])); medium_release[int(r[0])]=int(r[1])
    db.executemany("INSERT OR REPLACE INTO recording_release VALUES(?,?,?,?)",
                   ((recording,medium_release[medium],number,title) for recording,medium,number,title in recording_medium if medium in medium_release))
    release_group_ids=set(release_group_seed)
    for r in rows(args.core,"release"):
        if int(r[0]) in release_ids:
            release_group_ids.add(int(r[4])); db.execute("INSERT OR REPLACE INTO release VALUES(?,?,?,?,?,?,?,?,?)",(int(r[0]),r[1],r[2],int(r[3]),int(r[4]),r[5] and int(r[5]),r[7] and int(r[7]),r[9],r[10]))
    first_year={int(r[0]):(r[2] and int(r[2])) for r in rows(args.core,"release_group_meta") if int(r[0]) in release_group_ids}
    for r in rows(args.core,"release_group"):
        if int(r[0]) in release_group_ids:
            db.execute("INSERT OR REPLACE INTO release_group VALUES(?,?,?,?,?,?,?)",(int(r[0]),r[1],r[2],int(r[3]),r[4] and int(r[4]),r[5],first_year.get(int(r[0]))))
    db.execute("""UPDATE recording SET year=(SELECT MIN(rg.first_year)
      FROM recording_release rr JOIN release rel ON rel.id=rr.release_id
      JOIN release_group rg ON rg.id=rel.release_group_id
      WHERE rr.recording_id=recording.id AND rg.first_year IS NOT NULL)""")
    label_ids=set(targets["label"])
    for r in rows(args.core,"release_label"):
        if int(r[1]) in release_ids and r[2]:
            label_ids.add(int(r[2])); db.execute("INSERT OR REPLACE INTO release_label VALUES(?,?,?)",(int(r[1]),int(r[2]),r[3] or ""))
    for r in rows(args.core,"label"):
        if int(r[0]) in label_ids:
            db.execute("INSERT OR REPLACE INTO label VALUES(?,?,?,?,?,?,?,?,?)",(int(r[0]),r[1],r[2],r[10] and int(r[10]),r[11] and int(r[11]),r[9] and int(r[9]),r[3] and int(r[3]),r[6] and int(r[6]),r[12]))
    db.execute("INSERT OR REPLACE INTO metadata VALUES('core_snapshot',?)",(args.snapshot,)); db.commit()
    print(f"imported {len(associated_artists)} associated artists and {len(recording_batch)} artist-linked recordings")


def refresh_dates(args):
    db=connect(args.db); init(db)
    wanted={r[0] for r in db.execute("SELECT id FROM release_group")}
    db.executemany("UPDATE release_group SET first_year=? WHERE id=?",
                   ((int(r[2]),int(r[0])) for r in rows(DEFAULT_DERIVED,"release_group_meta") if int(r[0]) in wanted and r[2]))
    db.execute("""UPDATE recording SET year=(SELECT MIN(rg.first_year)
      FROM recording_release rr JOIN release rel ON rel.id=rr.release_id
      JOIN release_group rg ON rg.id=rel.release_group_id
      WHERE rr.recording_id=recording.id AND rg.first_year IS NOT NULL)""")
    db.commit()
    dated=db.execute("SELECT COUNT(*) FROM recording WHERE year IS NOT NULL").fetchone()[0]
    print(f"refreshed release-derived years for {dated} recordings")


def export(args):
    db=connect(args.db)
    payload={"generated_at":date.today().isoformat(),"provider":"MusicBrainz","snapshot":dict(db.execute("SELECT key,value FROM metadata")),
             "notice":"MusicBrainz tags are discovery signals pending editorial review.","genres":[]}
    for gid,name,country,start,end,pop in db.execute("SELECT id,name,country,active_from,active_to,popularity FROM atlas_genre WHERE selected=1 ORDER BY popularity DESC,name"):
        genre={"atlas_id":gid,"name":name,"country":country,"active_from":start,"active_to":end,"tag_score":pop,"artists":[],"recordings_by_decade":{}}
        artist_ids=[]
        for a in db.execute("""SELECT DISTINCT a.id,a.mbid,a.name,a.sort_name,a.begin_year,a.end_year,a.comment
          FROM artist a JOIN genre_artist ga ON ga.artist_id=a.id WHERE ga.genre_id=? ORDER BY a.name""",(gid,)):
            artist_ids.append(a[0]); genre["artists"].append({"mbid":a[1],"name":a[2],"sort_name":a[3],"begin_year":a[4],"end_year":a[5],"comment":a[6],
              "aliases":[x[0] for x in db.execute("SELECT name FROM artist_alias WHERE artist_id=? ORDER BY primary_locale DESC,name",(a[0],))],
              "identifiers":{kind:[v[0] for v in db.execute("SELECT value FROM artist_identifier WHERE artist_id=? AND kind=? ORDER BY value",(a[0],kind))]
                             for kind in ("ipi","isni")},
              "instruments":[x[0] for x in db.execute("SELECT i.name FROM instrument i JOIN artist_instrument ai ON ai.instrument_id=i.id WHERE ai.artist_id=? ORDER BY i.name",(a[0],))],
              "events":[{"name":x[0],"year":x[1]} for x in db.execute("SELECT e.name,e.begin_year FROM event e JOIN artist_event ae ON ae.event_id=e.id WHERE ae.artist_id=? ORDER BY e.begin_year,e.name",(a[0],))],
              "places":[x[0] for x in db.execute("SELECT p.name FROM place p JOIN artist_place ap ON ap.place_id=p.id WHERE ap.artist_id=? ORDER BY p.name",(a[0],))]})
        first=(start//10)*10 if start else 1900; last=((end or date.today().year)//10)*10
        for decade in range(max(1900,first),last+1,10) if args.per_decade > 0 else ():
            rec=[]
            for r in db.execute("""SELECT r.mbid,r.title,r.year,r.duration_ms,MAX(gr.score),r.credit_id
              FROM recording r JOIN genre_recording gr ON gr.recording_id=r.id
              WHERE gr.genre_id=? AND r.year>=? AND r.year<? GROUP BY r.id ORDER BY MAX(gr.score) DESC,r.title LIMIT ?""",(gid,decade,decade+10,args.per_decade)):
                rec.append({"mbid":r[0],"title":r[1],"year":r[2],"duration_ms":r[3],"score":r[4],
                            "artist_credit":"".join(x[0]+x[1] for x in db.execute("SELECT credited_name,join_phrase FROM artist_credit_artist WHERE credit_id=? ORDER BY position",(r[5],))),
                            "releases":[{"title":x[0],"mbid":x[1],"track_number":x[2],"labels":[{"name":y[0],"catalog_number":y[1]} for y in db.execute("SELECT l.name,rl.catalog_number FROM release_label rl JOIN label l ON l.id=rl.label_id WHERE rl.release_id=? ORDER BY l.name",(x[3],))]} for x in db.execute("SELECT rel.title,rel.mbid,rr.track_number,rel.id FROM recording_release rr JOIN release rel ON rel.id=rr.release_id WHERE rr.recording_id=? ORDER BY rel.title",(db.execute("SELECT id FROM recording WHERE mbid=?",(r[0],)).fetchone()[0],))]})
            genre["recordings_by_decade"][str(decade)]=rec
        payload["genres"].append(genre)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("w",encoding="utf-8",dir=args.out.parent,delete=False) as f:
        json.dump(payload,f,ensure_ascii=False,indent=2); f.write("\n"); tmp=Path(f.name)
    tmp.replace(args.out)
    print(f"wrote {len(payload['genres'])} genres to {args.out}")


def export_rym_candidates(args):
    """Write the complete album-level pool; make no MusicBrainz-only shortlist."""
    db=connect(args.db)
    credit={}
    for credit_id,name,join_phrase in db.execute(
        "SELECT credit_id,credited_name,join_phrase FROM artist_credit_artist ORDER BY credit_id,position"
    ):
        credit[credit_id]=credit.get(credit_id,"")+name+(join_phrase or "")
    query="""SELECT gr.genre_id,ag.name,ag.country,rg.mbid,rg.title,rg.first_year,rg.credit_id,
                    MAX(gr.score),COUNT(DISTINCT r.id),COUNT(DISTINCT rel.id)
             FROM genre_recording gr
             JOIN atlas_genre ag ON ag.id=gr.genre_id AND ag.selected=1
             JOIN recording r ON r.id=gr.recording_id
             JOIN recording_release rr ON rr.recording_id=r.id
             JOIN release rel ON rel.id=rr.release_id
             JOIN release_group rg ON rg.id=rel.release_group_id
             GROUP BY gr.genre_id,rg.id
             ORDER BY gr.genre_id,rg.first_year,rg.title"""
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("w",encoding="utf-8",newline="",dir=args.out.parent,delete=False) as stream:
        writer=csv.writer(stream)
        writer.writerow(("atlas_genre_id","atlas_genre_name","country","release_group_mbid","title",
                         "first_year","decade","artist_credit","musicbrainz_association_score",
                         "recording_count","release_count","review_status"))
        count=0
        for gid,gname,country,mbid,title,year,credit_id,score,recordings,releases in db.execute(query):
            writer.writerow((gid,gname,country,mbid,title,year or "",(year//10)*10 if year else "",
                             credit.get(credit_id,""),score,recordings,releases,"pending_rym"))
            count+=1
        tmp=Path(stream.name)
    tmp.replace(args.out)
    print(f"wrote {count} uncapped album candidates to {args.out}")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db",type=Path,default=DEFAULT_DB)
    sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser("index-derived"); p.add_argument("--derived",type=Path,default=DEFAULT_DERIVED); p.add_argument("--top-genres",type=int,default=12); p.add_argument("--snapshot",default="20260926-002121"); p.set_defaults(func=index_derived)
    p=sub.add_parser("import-core"); p.add_argument("--core",type=Path,default=DEFAULT_CORE); p.add_argument("--snapshot",default="20260926-002121"); p.set_defaults(func=import_core)
    p=sub.add_parser("export"); p.add_argument("--out",type=Path,default=DEFAULT_OUT); p.add_argument("--per-decade",type=int,default=0,
      help="Legacy MusicBrainz-only recording preview; 0 (default) disables preselection"); p.set_defaults(func=export)
    p=sub.add_parser("export-rym-candidates"); p.add_argument("--out",type=Path,default=DEFAULT_RYM_CANDIDATES); p.set_defaults(func=export_rym_candidates)
    p=sub.add_parser("refresh-dates"); p.set_defaults(func=refresh_dates)
    args=parser.parse_args(); args.func(args)


if __name__=="__main__": main()
