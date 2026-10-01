# Country and decade music research plan

This is a research queue, not a completed history or a claim that every decade had a distinct genre. The target is at least one **source-supported living or historical practice** for each 1900s–2020s country-decade cell, plus a representative set of major traditions and relevant artists. An empty cell means evidence is unreviewed or unavailable, never that music was absent.

Snapshot: 2026-09-28. The current atlas shows a genre in 949 of 1391 country-decade cells. None of the national history audits is complete. Current visibility can rest on a genre's broad editorial lifespan and is **not** proof of decade-by-decade continuity.

The queue also names the saved Wikipedia status and credited artists of each live layer. An exact genre article may not exist; a focused section or clearly attributed local text is the honest fallback. For collective traditions, document an ensemble or bearer community when individual artist credit would be misleading.

## Parallel regional work lanes

Each mapped area has exactly one `research_lane` and one `assigned_agent` in the JSON queue. Agent numbers are stable work assignments, not currently running processes. These lanes divide editing responsibility; they do not define musical borders. North Asian Russia is outside the current map, while Mongolia belongs to `asia_central_north`. Western Asia is split between the Caucasus/Anatolia and the rest of the Middle East so existing Middle East material can be reused without hiding the Caucasus gap.

| Agent | Lane | Areas | Count | Acquired source IDs |
| --- | --- | --- | ---: | --- |
| Agent 1 | `africa_north` | Algeria (DZA), Egypt (EGY), Libya (LBY), Morocco (MAR), Mauritania (MRT), Western Sahara (SAH), Sudan (SDN), Tunisia (TUN) | 8 | bloomsbury-mena-genres-v10-2015, garland-africa-v1-1998, garland-african-handbook-2008, sudan-madih-performance-1930-2000, unesco-urgent-safeguarding-2010-2011 |
| Agent 2 | `africa_west` | Benin (BEN), Burkina Faso (BFA), Ivory Coast (CIV), Cape Verde (CPV), Ghana (GHA), Guinea (GIN), The Gambia (GMB), Guinea-Bissau (GNB), Liberia (LBR), Mali (MLI), Niger (NER), Nigeria (NGA), Senegal (SEN), Sierra Leone (SLE), Togo (TGO) | 15 | garland-africa-v1-1998, garland-african-handbook-2008, jackson-gumbe-transatlantic-2012, rodrigues-morna-identity-2015, unesco-masterpieces-2001-2005 |
| Agent 3 | `africa_central` | Central African Republic (CAF), Cameroon (CMR), Democratic Republic of the Congo (COD), Republic of the Congo (COG), Gabon (GAB), Equatorial Guinea (GNQ), São Tomé and Príncipe (STP), Chad (TCD) | 8 | garland-africa-v1-1998, garland-african-handbook-2008, jackson-gumbe-transatlantic-2012, smithsonian-folkways-aka-pygmy-music-arom, unesco-congolese-rumba-inventories-2019-2020 |
| Agent 4 | `africa_east_horn` | Burundi (BDI), Djibouti (DJI), Eritrea (ERI), Ethiopia (ETH), Kenya (KEN), Rwanda (RWA), South Sudan (SDS), Somaliland (SOL), Somalia (SOM), Tanzania (TZA), Uganda (UGA) | 11 | garland-africa-v1-1998, garland-african-handbook-2008, johnson-heello-modern-somali-poetry |
| Agent 5 | `africa_south_islands` | Angola (AGO), Botswana (BWA), Comoros (COM), Lesotho (LSO), Madagascar (MDG), Mozambique (MOZ), Malawi (MWI), Namibia (NAM), Eswatini (SWZ), South Africa (ZAF), Zambia (ZMB), Zimbabwe (ZWE) | 12 | garland-africa-v1-1998, garland-african-handbook-2008, unesco-masterpieces-2001-2005, unesco-tsapiky-2024-2025 |
| Agent 6 | `asia_central_north` | Kazakhstan (KAZ), Kyrgyzstan (KGZ), Mongolia (MNG), Tajikistan (TJK), Turkmenistan (TKM), Uzbekistan (UZB) | 6 | music-of-central-asia-further-reading-2017, smithsonian-folkways-central-asian-music-overview-2011, turkic-soundscapes-2018 |
| Agent 7 | `asia_west_caucasus` | Armenia (ARM), Azerbaijan (AZE), Turkish Republic of Northern Cyprus (CYN), Cyprus (CYP), Georgia (GEO), Turkey (TUR) | 6 | bloomsbury-mena-genres-v10-2015, turkic-soundscapes-2018, unesco-duduk-record-2026, unesco-georgian-polyphony-record-2026, unesco-masterpieces-2001-2005 |
| Agent 8 | `asia_west_middle_east` | United Arab Emirates (ARE), Bahrain (BHR), Iran (IRN), Iraq (IRQ), Israel (ISR), Jordan (JOR), Kuwait (KWT), Lebanon (LBN), Oman (OMN), Palestine (PSX), Qatar (QAT), Saudi Arabia (SAU), Syria (SYR), Yemen (YEM) | 14 | bloomsbury-mena-genres-v10-2015, haydar-lebanese-zajal-1989, unesco-al-ayyala-booklet-2022, unesco-al-barah-record-2026, unesco-al-qudoud-source-set-2021, unesco-iraqi-maqam-record-2026, unesco-masterpieces-2001-2005, unesco-qudoud-nomination-2021, unesco-song-of-sanaa-record-2026 |
| Agent 9 | `asia_east` | People's Republic of China (CHN), Hong Kong (HKG), Japan (JPN), South Korea (KOR), Macau (MAC), North Korea (PRK), Taiwan (TWN) | 7 | cheng-chinese-popular-music-2023, unesco-representative-list-2009 |
| Agent 10 | `asia_south` | Afghanistan (AFG), Bangladesh (BGD), Bhutan (BTN), India (IND), Australian Indian Ocean Territories (IOA), Siachen Glacier (KAS), Sri Lanka (LKA), Nepal (NPL), Pakistan (PAK) | 9 | garland-south-asia-v5-2000, samarasinghe-nethsinghe-jayasuriya-field-recordings-2025, unesco-masterpieces-2001-2005, unesco-rukada-natya-2017-2018 |
| Agent 11 | `asia_southeast` | Brunei (BRN), Indonesia (IDN), Cambodia (KHM), Laos (LAO), Myanmar (MMR), Malaysia (MYS), Philippines (PHL), Singapore (SGP), Thailand (THA), East Timor (TLS), Vietnam (VNM) | 11 | garland-southeast-asia-v4-1998, unesco-chapei-source-set-2016, unesco-nora-source-set-2021 |

**Agent 12 — catalog integrator:** owns shared `research/genre_catalogue.json`, Wikipedia article matching/snapshots, generated site data, duplicate resolution, cross-border association review, and publication checks. Research agents own only their assigned country dossiers. Run agents in waves according to available capacity; preserve the same assignment when a wave resumes.

### Parallel editing contract

Private acquired documents are registered in `.local/acquired_sources/index.json` and assigned by mapped country code. The generator lists them in each country's `acquired_documents`; it does not read or interpret their contents. Agents must read the relevant file and cited pages, record claim-level findings in their country dossier, and distinguish a document's claims from their own inferences.

For every assigned country: open the Arts Knowledge source note to locate relevant chapters or entries, read those passages in the exact raw file, then record document ID, page/section, claim, place, date, artist, and uncertainty in `research/countries/<CODE>.json`. The wiki note is a navigation aid; it does not replace the source passage. A missing or unreadable passage remains a gap, not a verified claim.

1. Each agent owns only `research/countries/<CODE>.json` files in its lane. Record source URLs, page or section pointers, access language, place/period claims, performers, uncertainty, and open decade gaps there. Never force one genre into every decade without continuity evidence.
2. Agents may nominate cross-border genres in their dossiers, but must send the affected country code and exact supporting claim to that lane's owner. The receiving owner verifies local practice, location, and dates. Keep one canonical genre identity; treat other countries as separately sourced associations.
3. Agents do not concurrently edit `research/genre_catalogue.json`, `research/wiki_articles.json`, generated static data, or this plan. Agent 12 reviews dossiers and source ledgers, resolves duplicate names and contested geography, promotes entries, saves exact Wikipedia matches, then runs the builders and validators. The public source is a bibliographic citation with an exact locator, never a private raw path.
4. Handoff per country: reviewed candidates, a source-backed period chronology, mapped region names or justified country scope, artist and article status, remaining decade gaps, and an explicit coverage judgment. The integrator marks the country complete only after the breadth audit in `GENRE_RESEARCH_PLAN.md`.

## Research sequence for every country

1. Establish the mapped area's scope, major communities and local search languages. Write a short chronology of colonial, independence, migration, broadcast, recording and digital eras where relevant; do not impose those events on countries where they do not fit.
2. Review the existing dossier and the first access links below. Search national archives, libraries, broadcasters, university repositories, community institutions and local-language scholarship. Read every assigned acquired document or record why it could not be read. Use UNESCO and Wikidata rows as discovery leads only.
3. Build a source ledger for each candidate: name/aliases, musical characteristics, practice or influence area, first documentation, later transmission, named performers, and exact page or archive item. Separate a recording's release date from a genre's origin and an inscription date from continued practice.
4. Audit the thirteen decades individually. A genre may cover several decades when a source supports transmission through them. When evidence is thin, keep the cell open and seek fieldwork or specialist history; never invent a filler genre.
5. For each published genre, map a matching standalone Wikipedia page or focused section and save its revision in `research/wiki_articles.json`. If no precise article exists, retain the reviewed no-match reason and a source-backed local note. Verify artists against recordings, scholarly accounts or cultural institutions; use a named ensemble or community bearer where individual attribution is inappropriate. Attach YouTube playback only for exact reviewed videos from an official artist, verified artist, label, or other rights-holder channel.
6. Publish the reviewed country dossier and genre areas, regenerate static data, validate, inspect the map at each decade, and update the audit. Recheck boundary changes before mapping a historical locality to a modern region.

## Access routes

- [UNESCO heritage files](https://ich.unesco.org/en/lists) supply nominations and living-practice leads; they are not a complete genre ranking.
- [Smithsonian Folkways](https://folkways.si.edu/faq) provides free album liner notes that can supply performer, place and recording context.
- [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API) helps resolve artist and recording identifiers; verify genre and geography in independent sources.
- Local archives, university repositories, national broadcasters and community institutions provide the missing country-specific histories. Record access terms and citation pages in the dossier; keep full copyrighted books out of public site assets.
- 10 area plans do not yet have a candidate-specific direct source URL. Their saved search queries and private intake request are the first access task, not evidence of an absent musical history.

## Country queue

The linked JSON has the exact missing-decade list, source URLs, verified or candidate leads, and next actions for **every mapped area**. `Lead` below means a topic to investigate, not a confirmed main genre. An inspect-source link starts the country's source review and may document a different candidate than the first named lead. The map includes several territories or disputed areas; those rows require a scope review before national claims.

### Africa

| Area | Live layers | Decades without live genre | First lead and access |
| --- | ---: | --- | --- |
| Angola (AGO) | 2 | 1900s–1940s, 2000s–2020s | kizomba; [inspect source](https://ich.unesco.org/en/assistances/safeguarding-semba-by-creating-new-levers-for-intergenerational-transmission-and-income-generating-opportunities-02124) |
| Burundi (BDI) | 1 | 1950s–2020s | Ritual dance of the royal drum; [inspect source](https://ich.unesco.org/en/RL/00989) |
| Benin (BEN) | 1 | 1950s–2020s | expand Gélédé chants history; [inspect source](https://ich.unesco.org/en/lists?RL=00002) |
| Burkina Faso (BFA) | 1 | 1950s–2020s | Cultural practices and expressions linked to Balafon and Kolintang in Mali, Burkina Faso, Côte d'Ivoire and Indonesia; [inspect source](https://ich.unesco.org/en/RL/02131) |
| Botswana (BWA) | 2 | 1950s–2020s | Dikopelo folk music of Bakgatla ba Kgafela in Kgatleng District; [inspect source](https://ich.unesco.org/en/USL/01290) |
| Central African Republic (CAF) | 2 | 1950s–1970s, 2000s–2020s | Polyphonic singing of the Aka Pygmies of Central Africa; [inspect source](https://ich.unesco.org/en/RL/00082) |
| Ivory Coast (CIV) | 4 | none | Cultural practices and expressions linked to Balafon and Kolintang in Mali, Burkina Faso, Côte d'Ivoire and Indonesia; [inspect source](https://ich.unesco.org/en/RL/00005) |
| Cameroon (CMR) | 3 | 1980s–2000s | Mvet Oyeng, musical art, practices and skills associated with the Ekang community; [inspect source](https://ich.unesco.org/en/RL/02253) |
| Democratic Republic of the Congo (COD) | 2 | 1900s–1930s, 2000s | Congolese rumba; [inspect source](https://ich.unesco.org/en/RL/01711) |
| Republic of the Congo (COG) | 3 | 1950s–2000s | Congolese rumba; [inspect source](https://ich.unesco.org/en/RL/02253) |
| Comoros (COM) | 3 | none | expand Taarab in Kenya history; [inspect source](https://ich.unesco.org/en/projects/safeguarding-the-songs-of-the-moon-traditional-swahili-music-from-tanzania-unguja-and-pemba-and-the-comoros-00101) |
| Cape Verde (CPV) | 4 | none | Morna, musical practice of Cabo Verde; [inspect source](https://ich.unesco.org/en/RL/01469) |
| Djibouti (DJI) | 2 | 2000s–2020s | expand Somali sung poetry, hees and cayaar classes history; [inspect source](https://books.google.com/books/about/Culture_and_Customs_of_Somalia.html?id=tSyBAAAAMAAJ) |
| Algeria (DZA) | 4 | 1970s–2020s | Ahellil of Gourara; [inspect source](https://ich.unesco.org/en/RL/01894) |
| Egypt (EGY) | 5 | 1950s–1960s | Al-Sirah Al-Hilaliyyah epic; [inspect source](https://www.usna.edu/AAT/songs-poetry/popular-songs/readings/shaabi-egypt.php) |
| Eritrea (ERI) | 1 | 1900s–1950s, 2010s–2020s | guayla; [inspect source](https://escholarship.org/uc/item/2207257c) |
| Ethiopia (ETH) | 5 | 1950s, 2010s–2020s | expand Zema history; [inspect source](https://ich.unesco.org/en/ethiopia-recording-of-music-and-dance-traditions-00262) |
| Gabon (GAB) | 3 | 1950s–2000s | Mvet Oyeng, musical art, practices and skills associated with the Ekang community; [inspect source](https://ich.unesco.org/en/RL/02253) |
| Ghana (GHA) | 5 | none | Highlife music and dance; [inspect source](https://ich.unesco.org/en/RL/02141) |
| Guinea (GIN) | 1 | 1950s–2020s | Cultural space of Sosso-Bala; [inspect source](https://ich.unesco.org/en/RL/00009) |
| The Gambia (GMB) | 1 | 1950s–2020s | expand Kankurang music history; [inspect source](https://ich.unesco.org/en/assistances/building-capacities-on-intangible-cultural-heritage-inventorying-safeguarding-and-awareness-raising-activities-in-the-gambia-02344) |
| Guinea-Bissau (GNB) | 1 | none | gumbé; [inspect source](https://journal.ru.ac.za/index.php/africanmusic/article/view/1807) |
| Equatorial Guinea (GNQ) | 3 | 1950s–2000s | expand Mvet Oyeng history; [inspect source](https://dicames.online/jspui/bitstream/20.500.12177/3954/1/NicoleTamba.pdf) |
| Kenya (KEN) | 7 | none | Isukuti dance of Isukha and Idakho communities of Western Kenya; [inspect source](https://ich.unesco.org/en/USL/00981) |
| Liberia (LBR) | 2 | 1950s–1960s, 2000s–2020s | palm-wine music; [inspect source](https://folkways.si.edu/music-of-the-kpelle-of-liberia/world/album/smithsonian) |
| Libya (LBY) | 1 | 1950s–2020s | alriyfy music; [inspect source](https://books.google.com/books?id=vEOfxFoWmScC) |
| Lesotho (LSO) | 2 | 1990s–2020s | famo; [inspect source](https://www.lena.gov.ls/qachas-nek-holds-music-festival/) |
| Morocco (MAR) | 5 | 2010s–2020s | Gnawa; [inspect source](https://ich.unesco.org/en/RL/01170) |
| Madagascar (MDG) | 1 | 1950s–2020s | Tsapiky, rhythm and musical style characteristic of the South-West region of Madagascar; [inspect source](https://ich.unesco.org/en/RL/02272) |
| Mali (MLI) | 4 | 1950s–1960s | Cultural practices and expressions linked to Balafon and Kolintang in Mali, Burkina Faso, Côte d'Ivoire and Indonesia; [inspect source](https://ich.unesco.org/fr/assistances/les-pratiques-et-expressions-culturelles-liees-au-m-bolon-instrument-de-musique-traditionnel-a-percussion-01583) |
| Mozambique (MOZ) | 1 | 1950s–2020s | Chopi Timbila; [inspect source](https://ich.unesco.org/en/RL/00133) |
| Mauritania (MRT) | 3 | 1950s–2020s | expand T’heydinn epic performance history |
| Malawi (MWI) | 2 | none | Art of crafting and playing Mbira/Sansi, the finger-plucking traditional musical instrument in Malawi and Zimbabwe; [inspect source](https://folkways.si.edu/malipenga-dance-music-from-the-tonga-speaking-people-of-malawi/world/music/album/smithsonian) |
| Namibia (NAM) | 3 | 1950s | Aboxan Musik ǀŌb ǂÂns tsî ǁKhasigu, ancestral musical sound knowledge and skills; [inspect source](https://ich.unesco.org/en/assistances/aixan-gana-b-ans-tsi-khasigu-ancestral-musical-sound-knowledge-and-skills-01418) |
| Niger (NER) | 1 | 1950s–2020s | Practices and knowledge linked to the Imzad of the Tuareg communities of Algeria, Mali and Niger; [inspect source](https://ich.unesco.org/en/RL/00891) |
| Nigeria (NGA) | 7 | 2020s | expand Jùjú history; [inspect source](https://www.cambridge.org/core/journals/popular-music/article/abs/diachronic-study-of-change-in-juju-music/6C359B104E11472083E09727E7958672) |
| Rwanda (RWA) | 1 | 1950s–2020s | expand Intore history; [inspect source](https://ich.unesco.org/en/RL/02129) |
| Western Sahara (SAH) * | 1 | 1950s–2020s | expand Haul music history; [inspect source](https://journal.ru.ac.za/index.php/africanmusic/article/view/2313) |
| Sudan (SDN) | 2 | 2010s–2020s | expand Madīḥ history |
| South Sudan (SDS) | 2 | 2000s–2020s | expand Dinka song traditions history; [inspect source](https://www.research.ed.ac.uk/en/datasets/a-collection-of-dinka-songs/) |
| Senegal (SEN) | 4 | 1950s–1960s, 2020s | Xooy, a divination ceremony among the Serer of Senegal; [inspect source](https://musicinafrica.net/magazine/mbalax-senegal/) |
| Sierra Leone (SLE) | 1 | 1950s–2020s | gumbé; [inspect source](https://mbsse.gov.sl/wp-content/uploads/2023/09/SSS-Syllabus-Music-as-an-Applied-Subject.pdf) |
| Somaliland (SOL) * | 2 | 2000s–2020s | expand Heello-hees history |
| Somalia (SOM) | 2 | 2000s–2020s | expand Somali sung poetry, hees and cayaar classes history |
| São Tomé and Príncipe (STP) | 2 | none | expand Tchiloli history; [inspect source](https://ich.unesco.org/en/RL/02309) |
| Eswatini (SWZ) | 1 | 1950s–2020s | expand Sibhaca history; [inspect source](https://parliament.gov.sz/publications/parliament_reports/docs/ANNUAL%20REPORT%20SPORTS%202025.pdf) |
| Chad (TCD) | 5 | none | expand Ngàmbáye vocal music history; [inspect source](https://www.editions-harmattan.fr/catalogue/livre/la-musique-traditionnelle-ngambaye-tchad/3015) |
| Togo (TGO) | 1 | 1950s–2020s | expand Gélédé chants history; [inspect source](https://ich.unesco.org/en/lists?RL=00002) |
| Tunisia (TUN) | 1 | 1950s–2020s | expand Twāyef of Ghbonten history; [inspect source](https://ich.unesco.org/en/RL/01875) |
| Tanzania (TZA) | 5 | none | bongo flava; [inspect source](https://musicinafrica.net/magazine/taarab-music-coastal-music-flair/) |
| Uganda (UGA) | 3 | 1950s, 2010s–2020s | Bigwala, gourd trumpet music and dance of the Busoga Kingdom in Uganda; [inspect source](https://ich.unesco.org/en/USL/00749) |
| South Africa (ZAF) | 2 | 1970s–2020s | Afro fusion; [inspect source](https://www.education.gov.za/Portals/0/Documents/Manuals/2022%20Study%20Guides/MUSIC%20.pdf?ver=2022-09-07-102740-933) |
| Zambia (ZMB) | 1 | 1950s–2020s | Kalela dance; [inspect source](https://ich.unesco.org/en/RL/01372) |
| Zimbabwe (ZWE) | 1 | 1950s–2020s | Art of crafting and playing Mbira/Sansi, the finger-plucking traditional musical instrument in Malawi and Zimbabwe; [inspect source](https://ich.unesco.org/en/RL/00169) |

### Asia

| Area | Live layers | Decades without live genre | First lead and access |
| --- | ---: | --- | --- |
| Afghanistan (AFG) | 3 | 2020s | Art of crafting and playing rubab/rabab; [inspect source](https://ich.unesco.org/en/RL/02143) |
| United Arab Emirates (ARE) | 2 | 1950s–1970s | Al Ahalla, a living performing art in the United Arab Emirates; [inspect source](https://ich.unesco.org/en/RL/01012) |
| Armenia (ARM) | 3 | 1970s–1980s | Duduk and its music; [inspect source](https://ich.unesco.org/en/RL/00092) |
| Azerbaijan (AZE) | 6 | 1950s | Art of Azerbaijani Ashiq; [inspect source](https://ich.unesco.org/en/RL/00039) |
| Bangladesh (BGD) | 4 | none | Baul songs; [inspect source](https://ich.unesco.org/en/RL/00107) |
| Bahrain (BHR) | 2 | 1950s–1970s | Fjiri; [inspect source](https://ich.unesco.org/en/RL/01747) |
| Brunei (BRN) | 2 | 1950s–1970s | expand Sung pantun history; [inspect source](https://ich.unesco.org/en/RL/02274) |
| Bhutan (BTN) | 2 | 1950s–1960s, 2020s | Mask dance of the drums from Drametse; [inspect source](https://ich.unesco.org/en/RL/00161) |
| People's Republic of China (CHN) | 3 | none | Chinese shadow puppetry; [inspect source](https://ich.unesco.org/en/RL/00199) |
| Turkish Republic of Northern Cyprus (CYN) * | 1 | 1950s–2020s | expand Byzantine chant history |
| Cyprus (CYP) | 1 | 1950s–2020s | Byzantine chant; [inspect source](https://ich.unesco.org/en/RL/01508) |
| Georgia (GEO) | 1 | 1950s–2020s | Chidaoba, wrestling in Georgia; [inspect source](https://ich.unesco.org/en/RL/00008) |
| Hong Kong (HKG) * | 2 | 2000s–2020s | Hong Kong hip hop; [inspect source](https://www.jstor.org/stable/j.ctt1rfzz86) |
| Indonesia (IDN) | 6 | 2010s | Cultural practices and expressions linked to Balafon and Kolintang in Mali, Burkina Faso, Côte d'Ivoire and Indonesia; [inspect source](https://ich.unesco.org/en/RL/01607) |
| India (IND) | 7 | none | Buddhist chanting of Ladakh: recitation of sacred Buddhist texts in the trans-Himalayan Ladakh region, Jammu and Kashmir, India; [inspect source](https://ich.unesco.org/en/projects/action-plan-for-the-safeguarding-of-baul-songs-00047) |
| Australian Indian Ocean Territories (IOA) * | 1 | 1900s–2020s | expand Cocos Malay biola history; [inspect source](https://tandf.figshare.com/articles/dataset/Strings_across_the_ocean_practices_traditions_and_histories_of_the_Cocos_Malay_i_biola_i_in_the_Cocos_Keeling_Islands_Indian_Ocean/12263795) |
| Iran (IRN) | 6 | none | Art of crafting and playing rubab/rabab; [inspect source](https://ich.unesco.org/en/RL/00279) |
| Iraq (IRQ) | 1 | 1950s–2020s | Iraqi Maqam; [inspect source](https://ich.unesco.org/en/RL/00076) |
| Israel (ISR) | 1 | none | contemporary Jewish religious music |
| Jordan (JOR) | 1 | 1950s–2020s | As-Samer in Jordan; [inspect source](https://ich.unesco.org/en/RL/01301) |
| Japan (JPN) | 4 | 1950s–1960s, 2020s | Furyu-odori, ritual dances imbued with people’s hopes and prayers; [inspect source](https://ich.unesco.org/en/RL/00265) |
| Siachen Glacier (KAS) * | 1 | 1950s–2020s | expand Buddhist chanting of Ladakh history |
| Kazakhstan (KAZ) | 5 | none | Aitysh/Aitys, art of improvisation; [inspect source](https://ich.unesco.org/en/RL/00996) |
| Kyrgyzstan (KGZ) | 2 | 1950s–2020s | Aitysh/Aitys, art of improvisation; [inspect source](https://ich.unesco.org/en/RL/00065) |
| Cambodia (KHM) | 2 | 1950s–2000s | Chapei Dang Veng; [inspect source](https://ich.unesco.org/en/USL/01165) |
| South Korea (KOR) | 5 | none | Arirang, lyrical folk song in the Republic of Korea; [inspect source](https://ich.unesco.org/en/RL/00070) |
| Kuwait (KWT) | 4 | 1950s–1970s | expand Khalījī music history |
| Laos (LAO) | 2 | 1950s–1960s, 2000s–2020s | Khaen music of the Lao people; [inspect source](https://ich.unesco.org/en/RL/01296) |
| Lebanon (LBN) | 2 | none | Al-Zajal, recited or sung poetry; [inspect source](https://ich.unesco.org/en/RL/01000) |
| Sri Lanka (LKA) | 5 | none | expand Baila history; [inspect source](https://ich.unesco.org/en/RL/01370) |
| Macau (MAC) * | 2 | 1950s–2020s | expand Cantonese Naamyam history; [inspect source](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2026.1856681/full) |
| Myanmar (MMR) | 2 | none | expand Hsainwain history |
| Mongolia (MNG) | 5 | none | Coaxing ritual for camels; [inspect source](https://ich.unesco.org/en/RL/00396) |
| Malaysia (MYS) | 3 | 2000s–2020s | Dondang Sayang; [inspect source](https://ich.unesco.org/en/RL/00167) |
| Nepal (NPL) | 3 | 1950s–1990s | adhunik geet; [inspect source](https://folkways.si.edu/nepal-ritual-and-entertainment/world/music/album/smithsonian) |
| Oman (OMN) | 1 | 1950s–2020s | Al ‘azi, elegy, processional march and poetry; [inspect source](https://ich.unesco.org/en/RL/00372) |
| Pakistan (PAK) | 5 | 2000s–2020s | Boreendo, Bhorindo: ancient dying folk musical instrument, its melodies, knowledge, and skills; [inspect source](https://folkways.si.edu/pakistan-the-music-of-the-qawal/world/music/album/smithsonian) |
| Philippines (PHL) | 3 | 1950s–1970s | Darangen epic of the Maranao people of Lake Lanao; [inspect source](https://ich.unesco.org/en/RL/00015) |
| North Korea (PRK) | 2 | 1950s–1970s | Arirang folk song in the Democratic People’s Republic of Korea; [inspect source](https://repository.up.ac.za/handle/2263/76823) |
| Palestine (PSX) * | 3 | 1950s–2020s | Dabkeh, traditional dance in Palestine; [inspect source](https://ich.unesco.org/en/RL/01998) |
| Qatar (QAT) | 3 | 1950s–1970s | expand Khalījī music history |
| Saudi Arabia (SAU) | 3 | 1950s–1970s | Alardah Alnajdiyah, dance, drumming and poetry in Saudi Arabia; [inspect source](https://ich.unesco.org/en/RL/01196) |
| Singapore (SGP) | 3 | none | Malay music; [inspect source](https://www.roots.gov.sg/ich-landing/ich/xinyao) |
| Syria (SYR) | 2 | none | Al-Qudoud al-Halabiya; [inspect source](https://ich.unesco.org/en/RL/01578) |
| Thailand (THA) | 3 | 1950s–1960s, 2000s–2010s | expand Nora history; [inspect source](https://ich.unesco.org/en/RL/01587) |
| Tajikistan (TJK) | 3 | none | Art of crafting and playing rubab/rabab; [inspect source](https://ich.unesco.org/en/RL/00089) |
| Turkmenistan (TKM) | 3 | 1950s–2020s | Dutar making craftsmanship and traditional music performing art combined with singing; [inspect source](https://ich.unesco.org/en/RL/01259) |
| East Timor (TLS) | 1 | 1900s–2010s | expand Tebe history; [inspect source](https://natcomunesco.gov.tl/2024/03/30/tlncu-launched-the-booklet-and-video-tebe-traditional-of-timor-leste/) |
| Turkey (TUR) | 8 | none | Craftsmanship and performing art of balaban/mey; [inspect source](https://ich.unesco.org/en/RL/00179) |
| Taiwan (TWN) * | 2 | 1980s–2020s | Beiguan; [inspect source](https://www.moc.gov.tw/en/News_Content2.aspx?n=495&s=18183) |
| Uzbekistan (UZB) | 3 | none | Art of crafting and playing Kobyz; [inspect source](https://ich.unesco.org/en/RL/00089) |
| Vietnam (VNM) | 9 | none | Art of Đờn ca tài tử music and song in southern Viet Nam; [inspect source](https://ich.unesco.org/en/RL/00733) |
| Yemen (YEM) | 1 | 1950s–2020s | Hadrami Dan gathering; [inspect source](https://ich.unesco.org/en/RL/00077) |

* Scope review required.

## Source material that would accelerate the audit

If you already have lawful access, a **private** research copy or bibliographic pages from these sources would help. Do not place full copyrighted books in `web/`; record only short paraphrases and citations in dossiers.

1. *The Garland Encyclopedia of World Music*: Africa (vol. 1), Southeast Asia (vol. 4), South Asia (vol. 5), Middle East/Central Asia (vol. 6), East Asia (vol. 7). [Publisher series](https://www.routledge.com/Garland-Encyclopedia-of-World-Music/book-series/TFSE00091). These provide country and community histories and bibliographies.
2. *Bloomsbury Encyclopedia of Popular Music of the World*, vol. 6 (Africa/Middle East locations) and vol. 12 (Sub-Saharan African genres). [Vol. 6](https://www.bloomsbury.com/us/bloomsbury-encyclopedia-of-popular-music-of-the-world-volume-6-9781501324468/), [vol. 12](https://www.bloomsbury.com/us/bloomsbury-encyclopedia-of-popular-music-of-the-world-volume-12-9781501342028/). These help with twentieth-century genre chronology and named practitioners.
3. For countries with no dossier or thin early-decade evidence, country-specific academic articles, discographies, radio catalogues and field recordings are more valuable than another broad encyclopedia. Prioritize a scan or citation for the relevant chapter/decade, including title, author, edition, page numbers, and access rights.

Store privately supplied files in a user-approved research intake location; only source metadata and paraphrased findings enter the public catalog.

