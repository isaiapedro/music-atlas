# 1950s–present genre research roadmap

Snapshot: 2026-09-30. This roadmap expands the atlas from its stronger early-century coverage into postwar, late-20th-century, and contemporary musical genres and scenes. It is a research and ingestion plan, not a claim that every country produced a distinct genre in every decade.

## 2026-09-30 research-gap revision

The current public catalogue contains 250 entries in 100 mapped countries, but that is not a complete modern-history inventory: 75 country dossiers remain `unreviewed` and 32 are `starter_only`. The country-decade plan shows 32 mapped areas without a 1950s–present visible cell, 55 without a 2000s cell, and 57 without a 2020s cell. Visibility is a discovery proxy—not a claim-level completion measure.

The next bottleneck is therefore **source ingestion**, not another broad genre-name search. [`research/modern_source_ingestion_queue.csv`](research/modern_source_ingestion_queue.csv) specifies, by country, the missing period bands, current source custody, and the minimum material needed: postwar chronology, 2000s–present scene evidence, community/regional context, and representative evidence. [`research/MODERN_SOURCE_INGESTION_GAP_REVISION.md`](research/MODERN_SOURCE_INGESTION_GAP_REVISION.md) defines the intake order. Complete record ingestion only for already verified record-bearing entries; use the completed source packets—not tags or RYM pages alone—to discover new modern candidates and then revisit historical, instrument, and umbrella classifications.

## Baseline and success measures

The reproducible country-decade plan currently shows visible genre coverage in 47 countries for the 1950s, 52 for the 1960s, 57 for the 1970s, 64 for the 1980s, 64 for the 1990s, 52 for the 2000s, 52 for the 2010s, and 50 for the 2020s. Thirty-two mapped areas have no visible cell from 1950 onward. Of 250 published records, 77 have a documented start in or after 1950 and 15 in or after 2000. These are navigation/discovery counts, not evidence-anchored completion claims; the higher visibility counts do not replace the modern-emergence audit.

Track two different measures so an old tradition surviving into 2020 is not mistaken for a modern genre:

1. **Decade presence:** a source establishes that a genre or scene was active, recorded, performed, broadcast, circulated, revived, or prominent in that country during the decade.
2. **Period emergence:** a source places the genre's formation, naming, first scene, breakthrough, or recognizable stylistic consolidation in the period. This may be an approximate decade and must not be presented as an exact invention date.

The first completion milestone is not a genre quota. It is:

- every mapped country has a logged search for 1950–1979, 1980–1999, 2000–2009, 2010–2019, and 2020–present;
- every usable claim is recorded at claim level in its country dossier, including negative or inconclusive searches;
- every 1950s–2020s country-decade cell is either evidence-anchored or explicitly marked `searched_no_evidence`, `source_inaccessible`, or `classification_unresolved`;
- every published post-1950 candidate has independently checked identity, place, and time evidence;
- cross-border genres share one editorial content family while retaining separately supported country geography and timeline associations.

## Priority waves

### Wave 1 — Countries with no anchored 1950s–2020s cell

Start with: BDI, BEN, BFA, CYN, CYP, GEO, GIN, GMB, IOA, IRQ, ISR, JOR, KAS, KGZ, LBY, MAC, MDG, MOZ, MRT, NER, OMN, PSX, RWA, SAH, SLE, SWZ, TGO, TKM, TUN, YEM, ZMB, and ZWE.

For each area, seek one postwar chronology source and one contemporary-scene source before searching individual genre names. This avoids filling the queue with internationally visible artists while overlooking local scenes, minority communities, or locally named categories.

### Wave 2 — Countries with only one or two anchored cells

Next cover BWA, LBR, TLS, CAF, COG, DZA, GAB, GNQ, KHM, LSO, THA, and ZAF. Prefer evidence that bridges different periods rather than extending one old genre across all missing decades.

### Wave 3 — Modern-emergence audit for every country

Search all 107 mapped areas for genres or recognizable scenes formed, named, or nationally prominent after 2000. Prioritize locally used terms, hybrid and electronic styles, dance scenes, hip-hop and popular-music variants, religious and ceremonial revivals, minority-language scenes, and genres shaped by migration or digital circulation. Do not require that a source call the subject a “genre”; a documented scene or named style is eligible when its musical identity, place, and period are clear.

### Wave 4 — Balance and cross-border review

Audit the results for urban/rural, majority/minority, religious/secular, commercial/community, gender, language, island/mainland, and diaspora/home-scene balance. Join records only when they are the same musical identity, not merely cognate names. Add each country to a shared genre only after evidence independently establishes practice or a scene there.

## Source acquisition and ingestion

Use the Registry preflight before external discovery. Search local Arts Knowledge notes and registered raw sources first. Add lawful acquired material to `knowledge/arts/raw/music/` with a source note under `knowledge/arts/wiki/`, or to the project's private `.local/acquired_sources/` intake when it is not suitable for shared Knowledge custody. Register the exact file, citation, language, countries, and useful pages in `.local/acquired_sources/index.json`. Never copy raw books, scans, or rights-restricted media into `web/`.

Acquire sources in this order:

1. **National chronologies:** national libraries and archives, university presses, music encyclopedias, ethnomusicology handbooks, theses, dissertations, and peer-reviewed histories. These establish periodization and local terminology.
2. **Contemporaneous scene evidence:** broadcaster archives, record-label catalogues, discographies, newspaper and magazine archives, festival programmes, cultural-policy documents, oral-history collections, and archived venue material. These help date emergence, prominence, circulation, and decline.
3. **Community and regional sources:** practitioner associations, community archives, language-specific cultural institutions, regional museums, and specialist scholarship. These establish bearer communities and subnational or cross-border geography.
4. **Contemporary verification:** official artist or label biographies, reputable interviews, institutional festival profiles, chart archives, and rights-holder catalogues. These can support representatives and recent activity but should not alone establish a national origin claim.
5. **Discovery-only systems:** UNESCO, Wikidata, MusicBrainz, Wikipedia, streaming catalogues, and search results generate leads. Promote nothing from an identifier, tag, title match, inscription year, upload date, or search snippet alone.

For PDFs and scans, record page-level excerpts as short paraphrased claims. For audiovisual archives, record the catalogue identifier, recording date, place, credited performer, collector or publisher, and the specific inference it supports. An upload or release date is not automatically the genre's start date.

## Search protocol

For each country and period, run a repeatable search matrix in English, official languages, major local languages, and common transliterations:

- `[country/city/region] music history 1950s|1960s|1970s|1980s|1990s`;
- local equivalents of `popular music`, `dance music`, `youth music`, `urban music`, `new music`, `electronic music`, `underground`, `scene`, `radio`, `record label`, and `festival`;
- `[genre/local name] emerged|developed|scene|history|decline|revival`;
- site-specific searches across national libraries, broadcasters, universities, journals, archives, labels, and cultural institutions;
- neighbouring-country and migration-corridor searches for styles whose documented region crosses state borders.

Log the query, language, date, source family, result URL, access outcome, and useful or negative result in `research/countries/<CODE>.json`. Search decade-first before artist-first. An artist is evidence for a genre only when a source explicitly connects the artist to that musical identity.

## Candidate record and claim matrix

Every candidate should carry enough structured evidence for an integrator to answer:

- **Identity:** preferred local name, script, transliterations, aliases, and whether it is a genre, scene, tradition, dance-music practice, revival, or umbrella.
- **Formation:** approximate emergence decade and what the source actually dates—formation, naming, first recording, first broadcast, breakthrough, or stylistic consolidation.
- **Activity:** separately supported decades of activity or prominence. Gaps do not imply inactivity, and a revival does not imply uninterrupted continuity.
- **Geography:** country relationship, cities or broad direction, communities, migration routes, and independently evidenced cross-border associations.
- **Musical description:** sound, instrumentation, language, performance setting, social function, and related styles, paraphrased from suitable sources.
- **Prominence change:** approximate peak, decline, suppression, displacement, revival, or last documented activity. Use `timeline_end_status: present` only with evidence of living practice; otherwise use `unknown` or a clearly labelled approximate end of prominence.
- **Representatives and media:** up to three source-backed representatives and only manually reviewed rights-holder or institutional video examples.
- **Source precision:** URL or acquired document ID, title, publisher/archive, author, publication date, language, exact page/section/catalogue item, access date, and a `supports` statement for each claim.

Record conflicting dates and genre boundaries instead of averaging them. A broad decade estimate is acceptable when its evidence and uncertainty are explicit.

## Review and catalog integration

Regional researchers edit only their assigned dossiers. The catalog integrator processes candidates in batches of no more than 20:

1. Normalize names and compare aliases against the full corpus to prevent same-country duplicates.
2. Decide whether a candidate is a new identity, a local variant, a revival, a scene, or an additional country association for an existing cross-border family.
3. Verify at least one direct source for musical identity, one for country/region association, and one for the displayed period. One source may satisfy several requirements when it states them directly.
4. Set approximate `active_from`, `active_to`, and `timeline_end_status` from the supported claim—not from publication, inscription, or upload dates.
5. Add a saved Wikipedia article or focused section only when it is actually about the same form; otherwise retain a source-backed local description and reviewed no-match status.
6. Reuse the cross-country family's description, image, representatives, and videos. Keep only geography and timeline evidence on the national association.
7. Build static data, run the full validators and tests, inspect the map and detail panel, then publish the batch.

Do not block an otherwise supported genre because it lacks an image, Wikipedia page, named artist, exact boundary, exact year, or embeddable video.

## Delivery sequence

### Stage A — Queue and schema alignment

- Extend the generated country-decade queue to report both decade presence and emergence-decade coverage.
- Add explicit late-period search outcomes to dossiers without treating “no result” as musical absence.
- Produce country, decade, research-lane, and source-access batch views.

Exit condition: all 107 countries have machine-readable assignments for the five audit periods and every current post-1950 candidate appears in exactly one integration queue.

### Stage B — High-gap source bundles

- Ingest or register one national/regional history source and one post-2000 scene source for every Wave 1 country where obtainable.
- Index exact chapters, pages, archive series, or catalogue collections before extracting candidates.
- Bundle sources that cover several small or poorly indexed countries, especially regional encyclopedias, broadcaster collections, and cross-border cultural studies.

Exit condition: every Wave 1 country has either two usable source families or a documented acquisition blocker.

### Stage C — 1950s–1990s research

- Work by two-decade passes: 1950–1969, 1970–1989, then 1990–1999.
- Capture genres that emerged in the period as well as older forms with documented revivals, recordings, or changed social roles.
- Record radio, recording-industry, independence-era, migration, conflict, censorship, and urbanization context only where sources connect it to the music.

Exit condition: every country has a reviewed outcome for the three passes, and all publishable candidates have claim-level identity/place/time evidence.

### Stage D — 2000s–present research

- Search 2000–2009, 2010–2019, and 2020–present separately.
- Use contemporary institutional and scene documentation to counter the publication lag in encyclopedias.
- Preserve distinctions between local formation, diaspora formation, later adoption, commercial breakthrough, and internet visibility.

Exit condition: every country has a reviewed modern search outcome; published modern genres have an emergence basis stronger than a release date or platform tag.

### Stage E — Integration and quality audit

- Promote reviewed batches, rebuild the site, and regenerate the country-decade plan after each batch.
- Re-audit duplicate names, cross-country families, start/end decades, region labels, descriptions, images, representatives, and videos.
- Report separately: covered cells, searched-but-empty cells, source-access gaps, post-1950 emergence records, post-2000 emergence records, and countries still lacking a modern candidate.

Exit condition: no silent empty cells, no unsupported decade stretching, no same-country duplicate identities, and no cross-country family with conflicting editorial content.

## Main risks and mitigations

- **Recent-scene publication lag:** use contemporary archives, broadcasters, labels, festivals, and scholarly theses; label provisional classifications.
- **Search-engine and streaming bias:** search in local languages and through institutions before platform catalogues; do not equate availability with importance.
- **Genre versus scene ambiguity:** preserve the source's category and allow a documented scene/style record rather than forcing a genre label.
- **Political boundary bias:** search cultural regions and migration corridors, then require separate evidence for every country association.
- **False start dates:** distinguish formation, naming, recording, breakthrough, and revival; display approximate decades with the correct claim.
- **False continuity:** add only supported decade cells and leave documentary gaps visible.
- **Source scarcity or access:** bundle regional reference works, record inaccessible collections explicitly, and request the smallest high-yield document set rather than many isolated files.
- **Fast-changing media links:** treat article text and source citations as durable content; images and videos remain optional reviewed enhancements.

## Routine reporting

After every research wave, regenerate `research/country_decade_plan.json` and its readable plan, then report:

- countries searched and countries blocked;
- newly anchored cells by decade;
- newly reviewed emergence records for 1950–1999 and 2000–present;
- candidates found, rejected, merged, held, and published, with reasons;
- cross-border associations added or withheld;
- source bundles ingested and the remaining minimum acquisition requests;
- description, article, representative, image, and video gaps as optional enrichment metrics.

Coverage improves when the historical evidence improves—not merely when a broad lifespan makes another decade visible in the interface.
