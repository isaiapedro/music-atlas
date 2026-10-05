# Music Atlas

## Genre description, image, and video review

The permanent source is `research/genre_catalogue.json`; `research/wiki_articles.json` stores fetched Wikipedia reading. `web/data/genres.json` contains only records that pass static validation. Newly promoted records are tracked in separate private description, image, and video review queues; publication status alone does not mean all three assets are present. Follow the [genre enrichment pipeline](GENRE_RESEARCH_PLAN.md#enrichment-pipeline-for-newly-promoted-genres) for the exact commands and review requirements. Wikipedia is attributed reading; source-backed local notes establish the genre description. Images need verified depiction and licence, and YouTube examples need exact performance and uploader review.

## Private MusicBrainz catalogue build

The official MusicBrainz full-export snapshots can be reduced into a local,
reviewable catalogue without operating a complete MusicBrainz server. Raw dumps,
extracted tables, SQLite working data, and generated candidate catalogues stay in
the ignored `.local/musicbrainz/` directory.

```sh
python3 scripts/build_musicbrainz_catalog.py index-derived --top-genres 1000
python3 scripts/build_musicbrainz_catalog.py import-core
python3 scripts/build_musicbrainz_catalog.py export
python3 scripts/build_musicbrainz_catalog.py export-rym-candidates
python3 scripts/research_musicbrainz_genre_variants.py
python3 scripts/search_musicbrainz_targeted_terms.py
```

The first stage matches published Atlas names (and their reviewed Wikipedia
titles) to exact normalized MusicBrainz tags, ranks them by positive tag counts,
and selects every match when the requested ceiling exceeds the match count. The second follows those tags to all
associated artists and searches the dump for their recordings, identifiers,
aliases, instruments, events, places, releases, release groups, and labels. The
The uncapped album-candidate export groups recordings through MusicBrainz release groups and does
not select winners. Missing years remain blank for later review; the builder does not invent dates.
Only the separate RYM workflow may select up to nine albums per decade after rating and engagement
analysis. For a saved genre-chart page that yields fewer than nine selected recommendations, it
also retains the remaining chart items in rank order up to nine, irrespective of rating and review
counts. Public records use the saved chart's title, artist credit, and year; MusicBrainz is optional
identity enrichment and is never a publication gate.

## On-demand record artwork

`/api/record-art?record=<record-id>` never exposes provider credentials. It uses promoted exact
Discogs release IDs in `web/data/discogs_record_paths.json`, then discovers a high-confidence exact
edition live when a visitor opens a genre shelf and `DISCOGS_TOKEN` is configured. Successful and
unsuccessful match outcomes are persisted locally without artwork URLs, API payloads, or credentials.
It keeps the response in memory for no more than six hours and returns Discogs attribution and a
direct release link. If Discogs has no usable image, or has not been configured, it falls back to the
Cover Art Archive using the record's optional MusicBrainz release-group identity.
The current private catalogue selects all 91 exact tag-backed Atlas records rather than a
popularity-limited subset.

## Private genre recording research import

`python3 scripts/import_genre_recording_catalogue.py <source.json>` imports a reviewed research
JSON into `.local/musicbrainz/genre_recording_research.sqlite3`, separate from the MusicBrainz
snapshot database. It retains every source row and citation, routes `record_found` items to
`album_extension_candidates`, and stores `performance_found` items separately as supplemental
non-album recordings. Supplemental performances are fallback-only while a genre has fewer than
nine official `record_found` candidates; because the input has no verified release years, this is
a total-count proxy and does not claim decade coverage. Candidate rows remain private and are not
automatically publishable: MusicBrainz IDs and `automatic_import_ready` are preserved as supplied.
Repeated import of the same source hash refreshes the batch idempotently.

MusicBrainz tags are community discovery metadata, not evidence for the Atlas's
historical or geographic claims. Candidate associations require editorial review
before publication. MusicBrainz core data is CC0; the derived/tag dump is offered
under CC BY-NC-SA 3.0, so generated tag-derived catalogues retain that provenance.
The variant-name research command creates private JSON, Markdown, and editable
CSV review queues for genres that lack an exact tag-name match. It retains
Wikidata multilingual labels and aliases, MusicBrainz genre MBIDs when present,
and fuzzy tag suggestions, but never changes an association automatically.

The targeted-term command searches the reviewed multilingual and entity-specific terms in
`research/musicbrainz_targeted_search_terms.json`. Editorial promotions live separately in
`research/musicbrainz_promoted_relationships.json`. Its private CSV and JSON outputs separate
numeric community-tag `tag_id` values from UUID `mbid` values and preserve whether a result is an
`equivalent_tag`, `instrument`, `artist`, `example_recording`, `regional_variant`, `broader`, or
`related` lead. An exact result for an expanded query therefore remains qualified unless it has an
explicit promotion rule.

## Private RYM candidate workflow

Unofficial Rate Your Music data is an optional ranking signal, not an identity or historical
source. Save a Parse `get_charts` or compatible release response under the ignored `.local/`
directory, then reconcile it against the artists already associated with one MusicBrainz genre:

```sh
python3 scripts/build_rym_candidates.py .local/rym/raw/arabesk.json --genre-id tur-arabesk
```

The private RYM result selects at most nine MusicBrainz-matched releases per decade using a Bayesian
rating plus logarithmically normalized rating and written-review counts. High-scoring releases
without a reliable year enter `undated_hold`; the command never guesses their decade. Unmatched
artists and other excluded candidates remain visible in `not_selected`. Raw responses, ratings,
review counts, provider URLs, and generated queues remain private because RYM access is unofficial
and its community metrics change over time. The command consumes saved responses and does not make
paid or authenticated requests itself.

A live Parse chart smoke test is a separate, one-request command. The current `get_charts`
endpoint supports year, location, chart type, and media type filters; it has no genre filter.
Use it to check connectivity and response parsing, not to claim genre-specific coverage. Put the
credential only in an environment variable and acknowledge the potentially billable request:

```sh
PARSE_API_KEY=<secret> python3 scripts/fetch_parse_rym.py get_charts \
  --param page=1 --param year=1970s --param chart_type=top --param media_type=album \
  --allow-live-request --output .local/rym/raw/chart-connectivity-pilot.json
```

The fetcher allows one request per invocation, never writes the key to a URL or output file, and
keeps the response under ignored `.local/` storage. Review provider pricing and the returned filters
before requesting subsequent pages. For an artist-level pilot, use `search` with an artist name and
`search_type=a`, then call `get_artist_details` with the returned RYM artist URL. The artist endpoint
returns a discography with release years, ratings, and rating counts. This requires two individually
acknowledged requests and should be tested on one already-associated MusicBrainz artist before a bulk run.

To test RYM genre-name coverage across all published Atlas genres, fetch the taxonomy once and
compare it locally:

```sh
.venv/bin/python scripts/fetch_parse_rym.py get_genres --allow-live-request \
  --output .local/rym/raw/genres.json
.venv/bin/python scripts/compare_rym_genres.py .local/rym/raw/genres.json
```

The Parse listing currently prices `get_genres` at 2 credits per successful request. Exact
normalized names are separated from fuzzy suggestions, which remain pending review.

## Private ListenBrainz artist discovery

`python3 scripts/fetch_listenbrainz_genre_artists.py` ranks strongly MusicBrainz-associated artists
using ListenBrainz total listens and listener counts. By default, MusicBrainz candidates need a
direct artist genre-tag score of at least 2; high global listening counts cannot promote weak
recording/release-credit associations. The threshold can be changed with
`--min-artist-tag-score`. It also adds the representatives already
listed in the published Atlas catalogue for genres without a matched MusicBrainz genre tag.
Unique exact artist-name matches in the local MusicBrainz dump receive ListenBrainz metrics;
ambiguous names, unmatched names, and generic community/performer descriptions remain visible
as name-only manual-search candidates. The private JSON and CSV outputs are written under
`.local/listenbrainz/`; the ranked CSV includes up to 20 candidates per published genre record
by default (`--per-genre` accepts 1–20) and includes only artists with a MusicBrainz ID and
ListenBrainz metrics. `genres_without_listenbrainz_artists.csv` lists every genre with no
ListenBrainz-scored artist and whether its app-defined representatives occur in other genre
candidate lists.
ListenBrainz counts are global listening activity, not genre-specific popularity, nationality, or
proof of genre membership. The ranked export only includes repeated direct artist-tag evidence or
unique exact Atlas-representative matches where no MusicBrainz genre tag is available. MusicBrainz
association basis and match status are kept separate for review. A companion
`genre_artist_popularity_by_tag_score.csv` contains direct artist-tag associations in three review
bands: score 1, score 2, and score 3+.

To open the private analysis notebook in the project-local environment:

```sh
source .venv/bin/activate
python -m pip install -r requirements-notebook.txt
jupyter lab .local/musicbrainz/musicbrainz_genre_match_review.ipynb
```

The [country-by-country decade research plan](COUNTRY_DECADE_RESEARCH_PLAN.md) tracks source access, candidate genres and open 1900s–2020s decade cells for every mapped area. Its [machine-readable queue](research/country_decade_plan.json) separates visible layers from historical verification.

An interactive geographic starting point for exploring music across Africa and Asia. Visitors can select a country, see its first-level regions, move through a year timeline, and explore starter genre layers. [ROADMAP.md](ROADMAP.md) tracks the remaining historical content and 3D experience work.

Drag the map to move it, double-click to zoom at a location, or use the on-map zoom and fullscreen buttons. Country detail view keeps the dark atlas backdrop; surrounding countries are not navigation targets. Close the details to select another country from the overview.

Select a country to reveal capital circles, regional boundaries, and decade points floating above the music maps, starting at the current decade. Click or drag across the points to move through periods. Hover over a capital or region to see its name. Click a region to read its saved Wikipedia introduction in the description panel; the country's introduction appears by default. Country and region descriptions show saved Wikidata population and area when captured. Article attribution and source links stay at the bottom of the panel. Decade selection changes layers with reviewed time bounds. A tradition with no supported start remains discoverable at every decade as an explicitly undated layer; its dashed full-width lifespan is a UI affordance, not evidence of presence or continuity in every decade. Saved encyclopedia text and geographic figures are not filtered by period. A missing article has an explicit empty state.

Country view stacks colored genre slices above the geographic base map. A single genre may appear in more than one country when a separately reviewed local area documents practice or a later scene; each country shows only its supported regions and dates. A slice may use exact documented regions, the country outline for a national association, or a clearly labelled uniform directional slice (for example, “Approx. south”). Directional slices are deliberately broad locators, not administrative boundaries. Layers are separated vertically without resizing their geometry and follow pan and zoom. Hovering a slice raises it above its resting position; hovering the bottom geographic map isolates that map. Leaving restores the stack or the selected genre. The Geography selector offers the same interaction by keyboard or touch. Shaded surfaces and illuminated edges give a relief appearance; these effects are decorative, not elevation or musical-intensity data. Each genre has a distinct color within its country. Hover or focus a color selector to bring an overlapping association forward; click a selector or territory to open its saved Wikipedia introduction when available, or a source-backed local note otherwise. The reading panel shows place and period labels, up to three source-backed representatives (individual artists, ensembles, or documented bearer groups), and on-demand YouTube cards when reviewed genre videos exist. Source references stay at the bottom. Period endpoints are approximate evidence-informed visibility or prominence windows, not continuous popularity claims. Open ends are explicitly labelled either `present` or `last prominence unresolved`; the site no longer treats every missing final year as continuing popularity. [GENRE_RESEARCH_PLAN.md](GENRE_RESEARCH_PLAN.md) describes the evidence needed to expand coverage country by country. Validate edits with `python3 scripts/validate_genres.py`.

## Run

```sh
docker compose up --build -d --wait
```

Open `http://127.0.0.1:5186`. For local development without Docker:

```sh
python3 server.py
```

For access from a phone on a trusted LAN, determine this computer's private IPv4 address and bind to that exact address:

```sh
ATLAS_BIND_HOST=192.168.1.16 docker compose up --build -d --wait
```

Open `http://192.168.1.16:5186` on the phone, replacing the example address. LAN mode has no login; everyone on that reachable network can view the public map. Firewall rules and Wi-Fi client isolation can prevent access. Return to loopback with `docker compose down` followed by the default start command.

The connection definition is:

| Setting | Value |
| --- | --- |
| Protocol | HTTP, same-origin static web server |
| Host port | `5186` (reserved to Music Atlas in `registry/PORTS.md`) |
| Default bind | `127.0.0.1:5186` |
| LAN bind | Exact private IPv4 supplied through `ATLAS_BIND_HOST`; never `0.0.0.0` |
| Main route | `/` |
| Health route | `/health` |

There is no separate API address, TLS termination, authentication, or router-port-forwarding requirement. Keep LAN access on a trusted private network.

## Map data

Bundled country boundaries come from [Natural Earth 1:50m Admin 0](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_50m_admin_0_countries.geojson); province boundaries come from [Natural Earth 1:10m Admin 1](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_10m_admin_1_states_provinces.geojson). Capital points come from [Natural Earth 1:50m Populated Places](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_50m_populated_places.geojson). Natural Earth data is public domain. `scripts/prepare_map.py` and `scripts/prepare_capitals.py` reduce the source files to browser assets. The browser displays them using the [Equal Earth projection](https://shadedrelief.com/ee_proj/EEp_Math_and_Implementation_details_%202019-04-16.pdf), centered at 75°E. Some countries have incomplete or absent first-level region coverage or capital points. Borders are illustrative and reflect Natural Earth's cartographic conventions.

Country view includes WUP 2025 city centres plus country-scoped Natural Earth 10m attributes for
LandScan urban areas, rivers and lake centerlines, lakes/reservoirs, and named elevation points.
They are bundled as offline GeoJSON and reveal their name/type/value on hover or keyboard focus.
`scripts/prepare_geography.py` rebuilds these layers from the corresponding Natural Earth
shapefiles. Country zoom supports close inspection of these features while the continental
overview retains its bounded zoom range.

UN World Urbanization Prospects 2025 city populations drive the country-relative luminosity
visualization and displayed city markers. WUP covers cities with at least 50,000
inhabitants in 2025, so smaller
or unmatched places remain omitted from region markers. The qualified values live in
`web/data/place_population_overrides.json`. Country descriptions use WUP 2025 population totals;
region descriptions omit population because WUP does not provide a matching global admin-1
series. Country and region area remain visible when available. Rebuild the WUP city matches from its
official bulk gzip with `python3 scripts/import_wup_city_populations.py <downloaded-file.csv.gz>`.
Refresh country totals with `python3 scripts/import_wup_country_populations.py <level1-file.csv.gz>`.

Populated-place values from Natural Earth `POP_MAX` are modeled LandScan urban estimates, not
uniformly dated census counts. They remain useful as a comparable input to the country-relative
concentration layer, but the UI identifies them as modeled estimates. A separate
`place_population_overrides.json` supplies source-qualified year and scope metadata where an
official census value has been reviewed; those legacy records are not used by the current
WUP-exclusive region-city display.

The browser reads saved [English Wikipedia](https://en.wikipedia.org/) introductions and [Wikidata](https://www.wikidata.org/) geographic figures from generated `web/data/articles.json`; durable originals live in `research/wiki_articles.json`. It does not call either site while visitors browse. Population may be older than the selected year; area is converted to km² only for recognized units. Missing or unsupported figures are omitted. Captured Wikipedia text has source and [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) attribution. Artist examples use YouTube's privacy-enhanced embed only after the visitor presses a card. A direct video link remains available. Playback may be unavailable if the uploader changes the video or its embed permissions. The project does not copy or host recordings. There are no accounts, first-party analytics, database, or personal records.

Genre images are optional. The site displays only a reviewed external image URL with creator, licence, depiction statement, and a link to its source file page; it never treats an image as evidence of a genre's origin, territorial extent, or continuity. The private Wikimedia Commons discovery queue is generated on demand with `python3 scripts/find_genre_images.py`; candidates need per-file rights and depiction review before publication. No image is shown when no suitable reusable asset is found.

## Persistent research and article data

`research/country_inventory.json` records the review status of all 107 mapped areas. `research/INDEX.md` and `research/mvp_country_locks.json` list MVP-reviewed countries whose published media and listening-room selections must not be bulk-overwritten; Afghanistan is locked as of 2026-10-03. `research/genre_catalogue.json` is the durable source for reviewed genre layers, and `research/wiki_articles.json` permanently stores fetched encyclopedia introductions. The research queue currently has 86 area dossiers, 89 unpublished manually checked candidates, 359 automated UNESCO leads, and 65 automated Wikidata leads. Twenty-one mapped areas still lack a defensible dossier; their evidence or boundary gaps are recorded in the inventory. None of these discovery counts is a claim of comprehensive national coverage. Add dossiers following [research/README.md](research/README.md), with claim-level sources, period and community coverage, and known gaps. A candidate becomes a public map layer after its musical identity, time, and place claims are checked; an exact region, Wikipedia page, or authorized recording is optional. These files persist across browser and development sessions. `python3 scripts/research_progress.py` reports current counts and the remaining research queue.

The [country and decade plan](COUNTRY_DECADE_RESEARCH_PLAN.md) assigns Agents 1–11 to disjoint regional country dossiers and Agent 12 to shared catalog integration. Seven Arts Knowledge reference works are assigned to 96 country queues. Agents use each Knowledge note to locate relevant raw passages, record page-specific claims in the private dossier, and pass reviewed findings to the integrator. Public genre references may show a bibliographic citation; raw files and private paths are not served to visitors.

Unpublished dossiers, the coverage inventory, and governance plans stay in the workspace control plane and are ignored by the nested application's Git repository. The reviewed genre catalogue and exact article-title mappings are application data. Back up the workspace if these local research records need preservation beyond this machine.

Build the public, static genre and coverage files after editing research:

```sh
python3 scripts/build_static_data.py
python3 scripts/build_static_data.py --check
python3 scripts/validate_genres.py
```

The same script can capture missing encyclopedia introductions and geographic figures when a research environment can reach Wikimedia. It saves each successful article immediately, so a later run continues from the remaining gaps:

```sh
python3 scripts/build_static_data.py --fetch --scope countries
python3 scripts/build_static_data.py --fetch --scope genres
python3 scripts/build_static_data.py --fetch --scope regions --limit 100
```

The import uses official Wikimedia endpoints, checkpoints resumable batches, and respects rate
limits. The current snapshot covers 34 of 107 country introductions, all 53 genres with an exact
mapped Wikipedia page, and all 1,955 distinct region labels represented by the map's 1,976
geometries. Region titles resolve primarily through Natural Earth's Wikidata identifiers; reviewed
fallbacks cover source records without a usable English sitelink and documented duplicate labels.
`python3 scripts/validate_region_articles.py` is the completion gate. The site does not fetch
articles during visits. Wikipedia is reading context, not evidence for music-history claims.

After any application, data, or configuration change, the project handoff requires a LAN build
using the host's current private Wi-Fi IPv4:

```sh
ATLAS_BIND_HOST=<current-private-wifi-ipv4> docker compose up --build -d --wait
curl --fail http://<current-private-wifi-ipv4>:5186/health
```

This copies updated static files into the container and verifies the actual LAN listener. See
`AGENTS.md` for the mandatory agent verification contract.
