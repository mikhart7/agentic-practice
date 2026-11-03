# Ручная проверка разметки train

Сгенерировано `python case/dataset/review_accept.py`: 29 семейств с acceptable (все) и 15 без него (случайно, seed 3).

В каждом семействе отметьте вердикт и, если не согласны, напишите, что исправить:
- `[x] верно` — primary правильный, список acceptable полный и без лишних;
- `[x] исправить` — укажите, какой навык добавить или убрать в acceptable, либо заменить primary.

## arxiv-mcp-server#1

Намерение: *search arXiv preprints*. Кластер `research-papers`.

- `cmd`: arxiv papers on mixture of experts 2026
- `verbose`: I'm writing a survey; search arXiv for recent preprints on retrieval-augmented generation evaluation.
- `indirect`: find recent preprints in the physics-and-cs repository about speculative decoding
- `typo`: serch arxiv for diffusion models

| навык | описание | разметка |
|---|---|---|
| `arxiv-mcp-server` | Search arXiv, fetch paper metadata, and read full-text content. | **primary** |
| `semanticscholar` | Search 200M+ papers, authors, citations, and recommendations via Semantic Scholar | acceptable |
| `papernexus` | Find related scientific papers through their citation network, from OpenAlex and Semantic Scholar. |  |
| `onecite` | Generate academic citations from DOI, arXiv, titles, or URLs in BibTeX, APA, MLA formats. |  |
| `zotero-library-mcp` | Add papers and books to Zotero by DOI, arXiv ID, or ISBN and manage your library |  |
| `fulltext-article-downloader` | Full text of research papers by DOI, arXiv, PMC or OpenReview id, verified against the record |  |
| `codeofpaper` | Find GitHub implementations of arXiv research papers — paper lookup, ranked code, search. |  |
| `aria-mcp-server` | Search 35M+ PubMed, 400K+ ClinicalTrials.gov & ISRCTN trials. Prompts included. No API key. |  |

- [ ] верно
- [ ] исправить: 

## crypto_prices_mcp#1

Намерение: *current cryptocurrency price*. Кластер `crypto`.

- `cmd`: btc price now
- `casual`: whats eth at rn
- `question`: how much is one solana worth in usd today?
- `indirect`: what's the going rate for the original digital coin at the moment?

| навык | описание | разметка |
|---|---|---|
| `celo-mcp` | Query Celo blockchain data: blocks, tokens, NFTs, contracts, governance and staking |  |
| `crypto-safety` | Free crypto scam checks: token and contract risk, scam or sanctioned addresses, phishing links. |  |
| `crypto_prices_mcp` | Unlock the power of real-time cryptocurrency data with our Crypto Price Insights MCP server. | **primary** |
| `cryptohopper-data` | Real-time crypto market data: candles, tickers, orderbooks across 13+ exchanges via MCP. | acceptable |
| `solana-pulse-gateway` | Dry-run Solana txs before agents sign: exact balance changes, intent match, token traps. 25 free/day |  |
| `vaultrubric` | Sourced, scored comparisons of crypto exchanges, wallets, savings accounts and brokerages. |  |

- [ ] верно
- [ ] исправить: 

## email-mcp#2

Намерение: *send an email through own SMTP server*. Кластер `email`.

- `cmd`: send email via my smtp server to team@corp.com
- `indirect`: write back to the vendor from my own mail server, not some third-party service
- `question`: can you send a reply from my fastmail account using smtp?
- `casual`: shoot an email to bob from my account

| навык | описание | разметка |
|---|---|---|
| `email-mcp` | IMAP/SMTP email MCP server — 52 tools, stdio + HTTP, IMAP IDLE push, multi-account, AI triage. | **primary** |
| `ahasend` | Send email, check deliverability, set up domains, and run templates, contacts and campaigns. |  |
| `mail-receive` | Receive inbound email as clean JSON — manage domains, routes, and webhooks. MailKite. |  |
| `kanta` | Kanta Verify, Find, and Database: email verification, email finding, and B2B contact search. |  |
| `dmarc-spf-audit` | Complete domain email-auth audit in one call: SPF with RFC 7208 lookup counting, DKIM selector pr... |  |
| `salamailer` | Send end-to-end encrypted email and files. Encryption happens on your machine, not our server. | acceptable |
| `trykitt` | TryKitt MCP — wraps the TryKitt.ai B2B email finder API (trykitt.ai) |  |

- [ ] верно
- [ ] исправить: 

## gannet-mcp#2

Намерение: *general web search for an agent*. Кластер `web-search`.

- `casual`: just do a normal web search for "best hiking trails near zurich"
- `cmd`: web search "how to descale kettle vinegar"
- `indirect`: go online and find some pages about repotting a monstera
- `typo`: look up on the internet tips for training a puppie

| навык | описание | разметка |
|---|---|---|
| `serpapi-mcp` | Official SerpApi MCP server for Google, Bing, and other search engines. |  |
| `mcp-google-custom-search` | MCP server for Google Custom Search: web and image search via a Programmable Search Engine. |  |
| `yandex-search` | Yandex search results, images, and SERP data via the Apify Yandex Search Scraper, hosted MCP. |  |
| `miapi` | Web search and AI answers with real source citations and a confidence score. | acceptable |
| `gannet-mcp` | MCP server for web searching and webpage fetching | **primary** |
| `google-serp` | Structured Google search, news, and local results at scale - organic results, news, and local packs |  |
| `seolytics` | SEO & GEO data: keywords, live SERPs with AI Overviews, backlinks, site audits, rank tracking. |  |

- [ ] верно
- [ ] исправить: 

## google-cal-mcp#2

Намерение: *list upcoming events*. Кластер `calendar`.

- `question`: what's on my calendar for the rest of the week?
- `casual`: whats on my schedule tmrw
- `indirect`: am I free on Monday afternoon or do I have stuff booked?
- `cmd`: list my events this week

| навык | описание | разметка |
|---|---|---|
| `google-cal-mcp` | Allow AI systems to list, create, update, and manage Google Calendar events. | **primary** |
| `mcp-icloud-caldav` | iCloud Calendar over CalDAV: list, create, update, move and delete events. Optional read-only mode. | acceptable |
| `calendarmcp` | MCP server for macOS Calendar.app — calendar and event management via AppleScript | acceptable |
| `meet-bot` | AI-native scheduling and booking: check availability, book meetings, share links. |  |
| `sync-day` | Free no-signup group scheduling; share a link and rank times by who's free. |  |
| `mcp-jp-calendar` | MCP server for Japanese business days, holidays, and fiscal-period calculations. |  |
| `holiday-calendar` | U.S. federal holidays with observed dates and business-day math. Example from an open-source kit. |  |
| `vietnamese-calendar` | Vietnamese Lunar Calendar for date and calendar conversion, and cultural insights. |  |

- [ ] верно
- [ ] исправить: 

## google-drive-mcp#2

Намерение: *search files in cloud storage*. Кластер `cloud-storage`.

- `question`: where in my drive is the spreadsheet with the 2025 budget?
- `indirect`: find that document I saved months ago about the apartment lease
- `casual`: find my budget file in drive
- `cmd`: search drive files

| навык | описание | разметка |
|---|---|---|
| `google-drive-mcp` | Allow AI systems to list, search, upload, download, and manage files and folders in Google Drive. | **primary** |
| `google-drive-comments-mcp` | Minimal MCP server for reading comments on Google Drive files (Docs, Sheets, Slides). Read-only. |  |
| `ms-onedrive-mcp` | Microsoft OneDrive MCP server — browse, read, and manage files and folders through Microsoft Graph. | acceptable |
| `dropbox` | Dropbox MCP Pack — wraps the Dropbox API v2 | acceptable |
| `mcp-s3` | Read-only S3/MinIO/R2 object storage for AI agents — list buckets/objects, metadata, fetch. |  |
| `b2-mcp` | Official Backblaze B2 MCP server for buckets, files, keys, Object Lock, and S3 storage. |  |
| `remote-filesystem` | MCP server for remote filesystem operations on cloud storage (Google Cloud Storage). |  |
| `arkame-backup` | Backups of servers, Docker and Zimbra to your own S3. Restore by chat; changes need 2FA approval. |  |

- [ ] верно
- [ ] исправить: 

## google-maps#1

Намерение: *find nearby places*. Кластер `maps-geo`.

- `cmd`: coffee shops near alexanderplatz
- `casual`: any good ramen spots near me in shibuya?
- `question`: what pharmacies are open near union square right now?
- `indirect`: where can I grab breakfast within walking distance of the louvre?

| навык | описание | разметка |
|---|---|---|
| `google-maps` | Google Maps places: local search, place details, reviews, and turn-by-turn directions. | **primary** |
| `google-maps-places-mcp` | Allow AI systems to search for places and get business info via Google Maps Places API. | acceptable |
| `google-maps-reviews` | Google Maps reviews of any place: stars, text, date, photos, owner reply. Links, place IDs or names. |  |
| `itineraires` | Address geocoding and bike, scooter, motorcycle, wheelchair and walking routes across Europe. |  |
| `mapmap` | Maps for agents: truck/ADR routing, geocoding, places, matrices, isochrones, EV and fleet planning. |  |
| `acuris-mcp` | Address validation & geocoding for AI agents: 240+ countries, UK PAF, free US/CA enrichment |  |
| `rewindmap` | Historical borders and dated map events with source attribution and coverage limits. |  |
| `mindmeister` | Create, edit, and organize MindMeister mind maps from your AI assistant. |  |

- [ ] верно
- [ ] исправить: 

## google-maps-places-mcp#1

Намерение: *get business info for a place*. Кластер `maps-geo`.

- `cmd`: opening hours and phone of blue bottle coffee sf
- `verbose`: I need the address, phone number and opening hours of the dentist office called "Smile Studio" in Austin.
- `indirect`: is that bakery on main street open sundays and what's their number?
- `typo`: business info for the restarant on elm st

| навык | описание | разметка |
|---|---|---|
| `google-maps` | Google Maps places: local search, place details, reviews, and turn-by-turn directions. | acceptable |
| `google-maps-places-mcp` | Allow AI systems to search for places and get business info via Google Maps Places API. | **primary** |
| `google-maps-reviews` | Google Maps reviews of any place: stars, text, date, photos, owner reply. Links, place IDs or names. |  |
| `itineraires` | Address geocoding and bike, scooter, motorcycle, wheelchair and walking routes across Europe. |  |
| `mapmap` | Maps for agents: truck/ADR routing, geocoding, places, matrices, isochrones, EV and fleet planning. |  |
| `acuris-mcp` | Address validation & geocoding for AI agents: 240+ countries, UK PAF, free US/CA enrichment |  |
| `rewindmap` | Historical borders and dated map events with source attribution and coverage limits. |  |
| `mindmeister` | Create, edit, and organize MindMeister mind maps from your AI assistant. |  |

- [ ] верно
- [ ] исправить: 

## google-serp#2

Намерение: *structured Google news results at scale*. Кластер `web-search`.

- `cmd`: google news results for 500 brand keywords
- `indirect`: for each of these 200 company names give me what the news tab of the biggest search engine shows, as structured data
- `question`: how do I get organic and news results from google in bulk for a keyword list?
- `casual`: need google news + organic for like a thousand queries, json pls

| навык | описание | разметка |
|---|---|---|
| `serpapi-mcp` | Official SerpApi MCP server for Google, Bing, and other search engines. | acceptable |
| `mcp-google-custom-search` | MCP server for Google Custom Search: web and image search via a Programmable Search Engine. |  |
| `yandex-search` | Yandex search results, images, and SERP data via the Apify Yandex Search Scraper, hosted MCP. |  |
| `miapi` | Web search and AI answers with real source citations and a confidence score. |  |
| `gannet-mcp` | MCP server for web searching and webpage fetching |  |
| `google-serp` | Structured Google search, news, and local results at scale - organic results, news, and local packs | **primary** |
| `seolytics` | SEO & GEO data: keywords, live SERPs with AI Overviews, backlinks, site audits, rank tracking. |  |

- [ ] верно
- [ ] исправить: 

## iwe#1

Намерение: *use a local markdown notes folder as agent memory*. Кластер `notes-knowledge`.

- `cmd`: use my notes directory as knowledge base
- `verbose`: I have a folder of interlinked Markdown notes on disk; let the agent use it as long-term memory and search it while we work.
- `indirect`: treat the folder of .md files I'm in as your memory of my projects
- `typo`: markdown knowlege base from notes folder

| навык | описание | разметка |
|---|---|---|
| `notion` | Search, read and write your Notion workspaces, with pages as Markdown and typed database queries. |  |
| `mcp-obsidian-via-rest` | Access Obsidian vaults via Local REST API - read, search, and interact with notes | acceptable |
| `simplenote-mcp` | MCP server for reading Simplenote notes across macOS, Linux, and Windows |  |
| `wikijs-mcp` | Search, read and edit Wiki.js pages, and manage its assets, users, groups and comments |  |
| `iwe` | Markdown knowledge base as agent memory. Runs against the notes directory it is started in. | **primary** |
| `tiro` | Meeting notes and team wiki: search notes, transcripts, and wiki pages from your Tiro workspace. |  |
| `sidenote` | Read, search and edit your Sidenote notepads (Chrome side-panel notes) with your sync key. |  |
| `repowiki` | Read DeepWiki repository wikis and ask questions about public GitHub repos. |  |

- [ ] верно
- [ ] исправить: 

## mcp-google-custom-search#2

Намерение: *image search via Google*. Кластер `web-search`.

- `cmd`: find images of art deco lobby interiors
- `casual`: grab me some pics of red pandas from google images lol
- `indirect`: I want pictures, not pages — show me photos of brutalist libraries
- `typo`: image serch for vintage typewritter ads

| навык | описание | разметка |
|---|---|---|
| `serpapi-mcp` | Official SerpApi MCP server for Google, Bing, and other search engines. | acceptable |
| `mcp-google-custom-search` | MCP server for Google Custom Search: web and image search via a Programmable Search Engine. | **primary** |
| `yandex-search` | Yandex search results, images, and SERP data via the Apify Yandex Search Scraper, hosted MCP. |  |
| `miapi` | Web search and AI answers with real source citations and a confidence score. |  |
| `gannet-mcp` | MCP server for web searching and webpage fetching |  |
| `google-serp` | Structured Google search, news, and local results at scale - organic results, news, and local packs |  |
| `seolytics` | SEO & GEO data: keywords, live SERPs with AI Overviews, backlinks, site audits, rank tracking. |  |

- [ ] верно
- [ ] исправить: 

## mcp-s3#1

Намерение: *list objects in an S3 bucket read-only*. Кластер `cloud-storage`.

- `cmd`: list objects in s3 bucket logs
- `verbose`: I need to check which log files exist in our S3 bucket for yesterday, without any permission to modify anything.
- `indirect`: look at which log dumps amazon is holding for us from yesterday, without the ability to change them
- `typo`: list s3 buket objects

| навык | описание | разметка |
|---|---|---|
| `google-drive-mcp` | Allow AI systems to list, search, upload, download, and manage files and folders in Google Drive. |  |
| `google-drive-comments-mcp` | Minimal MCP server for reading comments on Google Drive files (Docs, Sheets, Slides). Read-only. |  |
| `ms-onedrive-mcp` | Microsoft OneDrive MCP server — browse, read, and manage files and folders through Microsoft Graph. |  |
| `dropbox` | Dropbox MCP Pack — wraps the Dropbox API v2 |  |
| `mcp-s3` | Read-only S3/MinIO/R2 object storage for AI agents — list buckets/objects, metadata, fetch. | **primary** |
| `b2-mcp` | Official Backblaze B2 MCP server for buckets, files, keys, Object Lock, and S3 storage. | acceptable |
| `remote-filesystem` | MCP server for remote filesystem operations on cloud storage (Google Cloud Storage). |  |
| `arkame-backup` | Backups of servers, Docker and Zimbra to your own S3. Restore by chat; changes need 2FA approval. |  |

- [ ] верно
- [ ] исправить: 

## memento#1

Намерение: *persistent knowledge graph memory*. Кластер `agent-memory`.

- `cmd`: remember this in long-term memory
- `verbose`: Store the fact that our staging DB is on port 5433 and the client's name is Ortega in persistent memory, linked as a knowledge graph.
- `indirect`: keep this in mind for future sessions and relate it to what you know about the project
- `typo`: save to persitent memory

| навык | описание | разметка |
|---|---|---|
| `memento` | Persistent memory for AI tools. Local-first knowledge graph with hybrid search. | **primary** |
| `frugal-memory` | Memory for AI assistants in one SQLite file: full-text search, no vectors, no embeddings. |  |
| `yantrikdb-mcp` | Cognitive memory for AI agents — semantic recall, knowledge graph, and contradiction detection | acceptable |
| `promise` | Evidence-backed follow-through memory for what you owe, await, and need to remember. |  |
| `monet` | Local-first, state-centric memory for coding agents. MCP server + CLI. |  |
| `kika` | Shared memory for client engagements: decisions with reasons, blockers, promises, what was tried. |  |

- [ ] верно
- [ ] исправить: 

## miapi#2

Намерение: *quick web lookup of a current fact*. Кластер `web-search`.

- `casual`: whats the current population of tokyo, look it up online
- `indirect`: I don't trust your memory on this one, check online: who won the latest turing award?
- `typo`: serch the web who is the ceo of nvidia now
- `cmd`: web search: current euro to yen exchange rate news

| навык | описание | разметка |
|---|---|---|
| `serpapi-mcp` | Official SerpApi MCP server for Google, Bing, and other search engines. |  |
| `mcp-google-custom-search` | MCP server for Google Custom Search: web and image search via a Programmable Search Engine. |  |
| `yandex-search` | Yandex search results, images, and SERP data via the Apify Yandex Search Scraper, hosted MCP. |  |
| `miapi` | Web search and AI answers with real source citations and a confidence score. | **primary** |
| `gannet-mcp` | MCP server for web searching and webpage fetching | acceptable |
| `google-serp` | Structured Google search, news, and local results at scale - organic results, news, and local packs |  |
| `seolytics` | SEO & GEO data: keywords, live SERPs with AI Overviews, backlinks, site audits, rank tracking. |  |

- [ ] верно
- [ ] исправить: 

## mysql-ops-mcp#2

Намерение: *browse MySQL schema*. Кластер `sql-database`.

- `question`: what tables and columns does our mysql database have?
- `indirect`: show me the structure of the wordpress db, which tables exist
- `casual`: list the mysql tables real quick
- `cmd`: describe mysql schema

| навык | описание | разметка |
|---|---|---|
| `pgport` | Read-only SQL queries against a PostgreSQL database. |  |
| `mysql-ops-mcp` | MySQL MCP server: browse schema, query, CRUD. Delete/drop gated by user approval. | **primary** |
| `litebase` | SQLite database access for agents: query, write, create and describe tables, record insights. |  |
| `database-admin` | Database admin MCP: schema inspection, query optimization for PostgreSQL and MySQL | acceptable |
| `dbtrail` | MySQL change tracking with instant row-level recovery and forensic attribution for compliance. |  |
| `pgcloud` | Neon Postgres projects, branches, SQL, and migrations from your MCP client. |  |
| `sqlike-mcp` | Lints SQL and checks rewrites return the same rows. Postgres, MySQL, MariaDB, SQLite, MSSQL, DuckDB |  |
| `veto` | Deterministic safety, correctness & cost gate that vets Postgres SQL before your AI agent runs it. |  |

- [ ] верно
- [ ] исправить: 

## ocrspace#1

Намерение: *OCR a scanned image to text*. Кластер `pdf`.

- `cmd`: ocr this receipt photo
- `indirect`: the text in this photo of a whiteboard — I need it as something I can copy
- `typo`: extract text from scaned image png
- `question`: can you read the words off this screenshot of a sign and give me the text?

| навык | описание | разметка |
|---|---|---|
| `pdfsamenvoegen` | Merge your own PDFs in a confirmed order and get one downloadable PDF. |  |
| `pdf-to-md` | Convert PDF documents to Markdown for AI agents through an authenticated remote MCP server. |  |
| `ocrspace` | OCR.space MCP — wraps the OCR.space API (ocr.space) for image/PDF → text OCR. | **primary** |
| `smoothsign` | Send PDFs for e-signature by email and SMS code. Check signing status. No document storage. |  |
| `marqpdf` | PDF tools for agents: compress to a size, Arabic + English OCR, Office conversion, JSON extraction. | acceptable |
| `document-scanner` | Finds PII and credentials in PDFs, screenshots and scanned documents |  |
| `isomor` | Translate text PDFs, keep the layout, get bilingual PDFs. MCP: EN/ZH. Website: 92 languages. |  |

- [ ] верно
- [ ] исправить: 

## open-meteo-mcp-server#1

Намерение: *weather forecast for a city*. Кластер `weather`.

- `cmd`: weather forecast berlin next 3 days
- `casual`: is it gonna rain in lisbon tmrw
- `question`: what will the temperature be in Nairobi this weekend?
- `indirect`: should I pack an umbrella for my trip to Prague on Friday?

| навык | описание | разметка |
|---|---|---|
| `open-meteo-mcp-server` | Global weather via Open-Meteo: forecast, historical, marine, air quality, geocoding, elevation. | **primary** |
| `weathersight` | Historical weather and climate: 100+ years of station data, normals, extremes, and trends. |  |
| `shearline` | Analyst-grade US severe weather: warnings, SPC outlooks, RAP environment, MRMS, GLM lightning |  |
| `spaceweather-mcp` | Space weather & geomagnetic conditions (NOAA SWPC, NASA DONKI, USGS, Kyoto) via MCP. |  |
| `ww3-mcp` | GFS-Wave (WAVEWATCH III) forecasts and NDBC buoy wave observations |  |
| `wttr-mcp` | Weather text from wttr.in. No key required. | acceptable |
| `cwa-mcp-server` | MCP server for Taiwan CWA open data: weather forecast, earthquake, warnings, typhoon. |  |

- [ ] верно
- [ ] исправить: 

## pdf-to-md#1

Намерение: *convert a PDF into Markdown*. Кластер `pdf`.

- `cmd`: convert whitepaper.pdf to markdown
- `indirect`: I want this report as plain text with headings and lists I can paste into my notes repo
- `question`: is there a way to turn a pdf manual into a .md file for my docs site?
- `typo`: pdf to markdwon conversion for the attached paper

| навык | описание | разметка |
|---|---|---|
| `pdfsamenvoegen` | Merge your own PDFs in a confirmed order and get one downloadable PDF. |  |
| `pdf-to-md` | Convert PDF documents to Markdown for AI agents through an authenticated remote MCP server. | **primary** |
| `ocrspace` | OCR.space MCP — wraps the OCR.space API (ocr.space) for image/PDF → text OCR. |  |
| `smoothsign` | Send PDFs for e-signature by email and SMS code. Check signing status. No document storage. |  |
| `marqpdf` | PDF tools for agents: compress to a size, Arabic + English OCR, Office conversion, JSON extraction. | acceptable |
| `document-scanner` | Finds PII and credentials in PDFs, screenshots and scanned documents |  |
| `isomor` | Translate text PDFs, keep the layout, get bilingual PDFs. MCP: EN/ZH. Website: 92 languages. |  |

- [ ] верно
- [ ] исправить: 

## perigon#1

Намерение: *real-time news search*. Кластер `news`.

- `cmd`: real-time news on openai
- `verbose`: Track breaking news about our competitor Acme Corp and show articles published in the last hour.
- `indirect`: what's being reported right now about the bank collapse?
- `typo`: realtime news search on tesla

| навык | описание | разметка |
|---|---|---|
| `hackernews-mcp` | Hacker News: front page, new and best feeds, item detail, user profiles, full-text search. |  |
| `gdelt-mcp` | Search the global news archive by keyword with recency and language filters. No key required. | acceptable |
| `rss-mcp` | RSS in one place: direct feed parsing and rss2json conversion for any feed URL. No key required. |  |
| `feed-forge` | Turn any website into an RSS, Atom, or JSON feed using CSS selectors and scheduled polling. |  |
| `spaceflight-news-mcp` | Space industry news articles from Spaceflight News. No key required. |  |
| `perigon` | Search real-time news articles, companies, journalists, and trending topics | **primary** |
| `thinkpattern-news` | Grounded, attributed news: what happened, which outlets reported it, and how many covered it. |  |
| `biotech-news` | Biotech News MCP — aggregated biotech & pharma industry news: FDA approvals, clinical readouts… |  |

- [ ] верно
- [ ] исправить: 

## pgport#2

Намерение: *inspect data in a Postgres table*. Кластер `sql-database`.

- `question`: how many rows in the postgres events table have status = 'failed'?
- `casual`: check the pg db how many failed payments today
- `indirect`: look up last week's refunds in our main relational db (it's postgres)
- `cmd`: query postgres refunds last week

| навык | описание | разметка |
|---|---|---|
| `pgport` | Read-only SQL queries against a PostgreSQL database. | **primary** |
| `mysql-ops-mcp` | MySQL MCP server: browse schema, query, CRUD. Delete/drop gated by user approval. | acceptable |
| `litebase` | SQLite database access for agents: query, write, create and describe tables, record insights. |  |
| `database-admin` | Database admin MCP: schema inspection, query optimization for PostgreSQL and MySQL | acceptable |
| `dbtrail` | MySQL change tracking with instant row-level recovery and forensic attribution for compliance. |  |
| `pgcloud` | Neon Postgres projects, branches, SQL, and migrations from your MCP client. |  |
| `sqlike-mcp` | Lints SQL and checks rewrites return the same rows. Postgres, MySQL, MariaDB, SQLite, MSSQL, DuckDB |  |
| `veto` | Deterministic safety, correctness & cost gate that vets Postgres SQL before your AI agent runs it. |  |

- [ ] верно
- [ ] исправить: 

## semanticscholar#1

Намерение: *find citations of a paper*. Кластер `research-papers`.

- `cmd`: who cites attention is all you need
- `verbose`: For my literature review I need the most cited papers that cite "BERT" and their authors.
- `indirect`: which later works built on this famous 2017 paper?
- `typo`: citations for paper semantic scholar

| навык | описание | разметка |
|---|---|---|
| `arxiv-mcp-server` | Search arXiv, fetch paper metadata, and read full-text content. |  |
| `semanticscholar` | Search 200M+ papers, authors, citations, and recommendations via Semantic Scholar | **primary** |
| `papernexus` | Find related scientific papers through their citation network, from OpenAlex and Semantic Scholar. | acceptable |
| `onecite` | Generate academic citations from DOI, arXiv, titles, or URLs in BibTeX, APA, MLA formats. |  |
| `zotero-library-mcp` | Add papers and books to Zotero by DOI, arXiv ID, or ISBN and manage your library |  |
| `fulltext-article-downloader` | Full text of research papers by DOI, arXiv, PMC or OpenReview id, verified against the record |  |
| `codeofpaper` | Find GitHub implementations of arXiv research papers — paper lookup, ranked code, search. |  |
| `aria-mcp-server` | Search 35M+ PubMed, 400K+ ClinicalTrials.gov & ISRCTN trials. Prompts included. No API key. |  |

- [ ] верно
- [ ] исправить: 

## serpapi-mcp#1

Намерение: *get raw Google search results for a query*. Кластер `web-search`.

- `cmd`: google results for "best mechanical keyboards 2026"
- `indirect`: I need the actual result listing a big search engine shows for "rust async runtime comparison", positions and links included
- `question`: how can I pull the top google and bing results for "vegan protein powder"?
- `typo`: get me serp resutls from bing for electric bike laws in california

| навык | описание | разметка |
|---|---|---|
| `serpapi-mcp` | Official SerpApi MCP server for Google, Bing, and other search engines. | **primary** |
| `mcp-google-custom-search` | MCP server for Google Custom Search: web and image search via a Programmable Search Engine. |  |
| `yandex-search` | Yandex search results, images, and SERP data via the Apify Yandex Search Scraper, hosted MCP. |  |
| `miapi` | Web search and AI answers with real source citations and a confidence score. |  |
| `gannet-mcp` | MCP server for web searching and webpage fetching |  |
| `google-serp` | Structured Google search, news, and local results at scale - organic results, news, and local packs | acceptable |
| `seolytics` | SEO & GEO data: keywords, live SERPs with AI Overviews, backlinks, site audits, rank tracking. |  |

- [ ] верно
- [ ] исправить: 

## solana-pulse-gateway#2

Намерение: *detect token traps in a Solana transaction*. Кластер `crypto`.

- `question`: does this solana transaction contain any hidden token approvals or traps?
- `indirect`: check whether the thing I'm about to sign does what the dapp claims
- `casual`: is this sol tx safe to sign?
- `cmd`: solana tx intent check

| навык | описание | разметка |
|---|---|---|
| `celo-mcp` | Query Celo blockchain data: blocks, tokens, NFTs, contracts, governance and staking |  |
| `crypto-safety` | Free crypto scam checks: token and contract risk, scam or sanctioned addresses, phishing links. | acceptable |
| `crypto_prices_mcp` | Unlock the power of real-time cryptocurrency data with our Crypto Price Insights MCP server. |  |
| `cryptohopper-data` | Real-time crypto market data: candles, tickers, orderbooks across 13+ exchanges via MCP. |  |
| `solana-pulse-gateway` | Dry-run Solana txs before agents sign: exact balance changes, intent match, token traps. 25 free/day | **primary** |
| `vaultrubric` | Sourced, scored comparisons of crypto exchanges, wallets, savings accounts and brokerages. |  |

- [ ] верно
- [ ] исправить: 

## tiro#2

Намерение: *look up team wiki pages*. Кластер `notes-knowledge`.

- `question`: is there a page in our team wiki about expense reimbursement?
- `indirect`: check our team's shared knowledge pages for the travel policy
- `casual`: anything in the wiki about expenses?
- `cmd`: team wiki search

| навык | описание | разметка |
|---|---|---|
| `notion` | Search, read and write your Notion workspaces, with pages as Markdown and typed database queries. | acceptable |
| `mcp-obsidian-via-rest` | Access Obsidian vaults via Local REST API - read, search, and interact with notes |  |
| `simplenote-mcp` | MCP server for reading Simplenote notes across macOS, Linux, and Windows |  |
| `wikijs-mcp` | Search, read and edit Wiki.js pages, and manage its assets, users, groups and comments | acceptable |
| `iwe` | Markdown knowledge base as agent memory. Runs against the notes directory it is started in. |  |
| `tiro` | Meeting notes and team wiki: search notes, transcripts, and wiki pages from your Tiro workspace. | **primary** |
| `sidenote` | Read, search and edit your Sidenote notepads (Chrome side-panel notes) with your sync key. |  |
| `repowiki` | Read DeepWiki repository wikis and ask questions about public GitHub repos. |  |

- [ ] верно
- [ ] исправить: 

## tolgee#2

Намерение: *search existing app translations*. Кластер `translation`.

- `question`: what's the current german translation for "save changes" in our project?
- `indirect`: look up how we already translated this ui phrase in our translation management tool
- `casual`: whats our french string for logout
- `cmd`: find translation for key

| навык | описание | разметка |
|---|---|---|
| `langbly` | Translate text or HTML, detect languages, and list supported languages with Langbly. |  |
| `kaeris-mcp` | Translate app language files into 46 languages and check placeholders, plurals and missing keys. |  |
| `tolgee` | Your app's translations in Tolgee: search keys, create translations, trigger machine translation | **primary** |
| `crowdin` | MCP server for Crowdin — projects, files, strings, translation progress, tasks, and members. | acceptable |
| `rosetta-mcp` | AI-powered Excel translation preserving formatting, formulas, and data integrity. |  |
| `dialectos` | Spanish dialect translation MCP server: 25 regional variants, glossary enforcement, quality gates. |  |
| `cron-translator` | Explain cron expressions in English, list next run times, and catch scheduling gotchas. |  |

- [ ] верно
- [ ] исправить: 

## trykitt#1

Намерение: *B2B email finder for a list of prospects*. Кластер `email`.

- `verbose`: I have a spreadsheet of 50 VP of Sales names and their companies, find their business email addresses for outreach.
- `indirect`: get me contact addresses for these decision makers so sales can reach out
- `cmd`: find b2b emails for prospect list
- `casual`: need emails for these leads asap

| навык | описание | разметка |
|---|---|---|
| `email-mcp` | IMAP/SMTP email MCP server — 52 tools, stdio + HTTP, IMAP IDLE push, multi-account, AI triage. |  |
| `ahasend` | Send email, check deliverability, set up domains, and run templates, contacts and campaigns. |  |
| `mail-receive` | Receive inbound email as clean JSON — manage domains, routes, and webhooks. MailKite. |  |
| `kanta` | Kanta Verify, Find, and Database: email verification, email finding, and B2B contact search. | acceptable |
| `dmarc-spf-audit` | Complete domain email-auth audit in one call: SPF with RFC 7208 lookup counting, DKIM selector pr... |  |
| `salamailer` | Send end-to-end encrypted email and files. Encryption happens on your machine, not our server. |  |
| `trykitt` | TryKitt MCP — wraps the TryKitt.ai B2B email finder API (trykitt.ai) | **primary** |

- [ ] верно
- [ ] исправить: 

## webreaper#2

Намерение: *scrape one page to clean text*. Кластер `browser-automation`.

- `question`: can you scrape this article page and give me just the main content?
- `indirect`: pull the readable text from this url without menus and ads
- `casual`: scrape this page pls
- `cmd`: scrape url to clean markdown

| навык | описание | разметка |
|---|---|---|
| `mcp-server-browser-automation` | Browser automation MCP server: navigate, fill forms, click, screenshot, and manage tabs |  |
| `webreaper` | AI-native web scraper: scrape, crawl and map any site to clean markdown over stdio. MIT-licensed. | **primary** |
| `playwright-report-mcp` | Run Playwright tests and surface structured results for AI agents doing test failure analysis. |  |
| `mcp-accessibility-scanner` | MCP server for automated web accessibility scanning with Playwright and Axe-core. |  |
| `playwright-trace-decoder-mcp` | MCP server for unpacking and analyzing Playwright trace.zip archives |  |
| `screenshot-mcp` | Website screenshots, URL/HTML to PDF, scrolling videos, and web scraping via ScreenshotAPI. | acceptable |

- [ ] верно
- [ ] исправить: 

## wttr-mcp#1

Намерение: *quick plain-text weather without API key*. Кластер `weather`.

- `cmd`: weather in oslo as text
- `casual`: quick weather check for madrid, just text
- `indirect`: I just want a one-line summary of today's conditions in Kyiv, no setup or keys
- `typo`: whats the wether in dublin now

| навык | описание | разметка |
|---|---|---|
| `open-meteo-mcp-server` | Global weather via Open-Meteo: forecast, historical, marine, air quality, geocoding, elevation. | acceptable |
| `weathersight` | Historical weather and climate: 100+ years of station data, normals, extremes, and trends. |  |
| `shearline` | Analyst-grade US severe weather: warnings, SPC outlooks, RAP environment, MRMS, GLM lightning |  |
| `spaceweather-mcp` | Space weather & geomagnetic conditions (NOAA SWPC, NASA DONKI, USGS, Kyoto) via MCP. |  |
| `ww3-mcp` | GFS-Wave (WAVEWATCH III) forecasts and NDBC buoy wave observations |  |
| `wttr-mcp` | Weather text from wttr.in. No key required. | **primary** |
| `cwa-mcp-server` | MCP server for Taiwan CWA open data: weather forecast, earthquake, warnings, typhoon. |  |

- [ ] верно
- [ ] исправить: 

## ww3-mcp#1

Намерение: *ocean wave forecast for surfing/sailing*. Кластер `weather`.

- `cmd`: wave forecast hawaii north shore
- `verbose`: I'm surfing in Ericeira this weekend; what wave heights and periods does the wave model predict?
- `indirect`: how big will the swell be at the beach in santa cruz on saturday?
- `typo`: swell forcast for the outer banks

| навык | описание | разметка |
|---|---|---|
| `open-meteo-mcp-server` | Global weather via Open-Meteo: forecast, historical, marine, air quality, geocoding, elevation. | acceptable |
| `weathersight` | Historical weather and climate: 100+ years of station data, normals, extremes, and trends. |  |
| `shearline` | Analyst-grade US severe weather: warnings, SPC outlooks, RAP environment, MRMS, GLM lightning |  |
| `spaceweather-mcp` | Space weather & geomagnetic conditions (NOAA SWPC, NASA DONKI, USGS, Kyoto) via MCP. |  |
| `ww3-mcp` | GFS-Wave (WAVEWATCH III) forecasts and NDBC buoy wave observations | **primary** |
| `wttr-mcp` | Weather text from wttr.in. No key required. |  |
| `cwa-mcp-server` | MCP server for Taiwan CWA open data: weather forecast, earthquake, warnings, typhoon. |  |

- [ ] верно
- [ ] исправить: 

## airtable#2

Намерение: *query Airtable tables*. Кластер `spreadsheets`.

- `question`: which records in our airtable content table are marked "ready to publish"?
- `indirect`: filter our no-code database for items assigned to me
- `casual`: whats ready in airtable
- `cmd`: list airtable records filter

| навык | описание | разметка |
|---|---|---|
| `mcp-google-sheets` | MCP server for the Google Sheets API: read and write ranges, sheets, formatting, charts, sharing. |  |
| `agent-spreadsheet` | Agent-safe Excel workbook analysis, editing, recalc, and verification tools. |  |
| `airtable` | Create, read, update, and delete records in Airtable bases and tables | **primary** |
| `csv-mcp` | Parse, filter, and inspect CSV data locally. No network and no key. |  |
| `dataloupe` | Offline MCP server to explore CSV/JSON/Parquet/Excel: preview, query, diff, render interactive HTML |  |
| `csv-repair` | Free CSV validation and repair, up to 20 data lines, no storage. Annual browser licence available. |  |
| `sheet-shift` | Convert and clean tables: CSV, JSON, dedupe, stats. Free. |  |
| `chargescout` | Find subscriptions, price increases and double charges in a bank statement CSV, on your machine. |  |

- [ ] верно
- [ ] исправить: 

## bolsai-mcp#2

Намерение: *Brazilian real estate funds (FIIs)*. Кластер `market-data`.

- `question`: what is the dividend yield of the fii hglg11?
- `indirect`: compare the payouts of brazilian real estate investment funds
- `casual`: best fiis by yield?
- `cmd`: fii yield comparison

| навык | описание | разметка |
|---|---|---|
| `yahoo-finance-mcp-server` | Get real-time stock quotes, historical data, and compare stocks via Yahoo Finance |  |
| `deepviews` | Free financial data: company analysis, DCF, comps, benchmarks, screening. No API key. |  |
| `tickerinside-mcp` | US ETF and mutual fund holdings, which ETFs hold a stock, overlap, look-through. Free, no API key. |  |
| `market-news` | Real-time US stock news, press releases, and legal notices. Pro or trial key required. |  |
| `bolsai-mcp` | Brazilian stock market data (B3, CVM, BCB) for AI assistants: quotes, fundamentals, dividends, FIIs. | **primary** |
| `polymarket-toolkit` | Read-only Polymarket data tools for AI agents: profiles, PnL, market scans. No keys, no orders. |  |
| `municipal-data` | Financial data, fiscal health scores, and economic indicators for 20,000+ U.S. municipalities. |  |

- [ ] верно
- [ ] исправить: 

## cwa-mcp-server#2

Намерение: *Taiwan earthquake reports*. Кластер `weather`.

- `question`: was there an earthquake in hualien today and how strong was it?
- `indirect`: the building shook in taichung a minute ago — what was the magnitude?
- `casual`: earthquake in taiwan just now?
- `cmd`: taiwan earthquake report latest

| навык | описание | разметка |
|---|---|---|
| `open-meteo-mcp-server` | Global weather via Open-Meteo: forecast, historical, marine, air quality, geocoding, elevation. |  |
| `weathersight` | Historical weather and climate: 100+ years of station data, normals, extremes, and trends. |  |
| `shearline` | Analyst-grade US severe weather: warnings, SPC outlooks, RAP environment, MRMS, GLM lightning |  |
| `spaceweather-mcp` | Space weather & geomagnetic conditions (NOAA SWPC, NASA DONKI, USGS, Kyoto) via MCP. |  |
| `ww3-mcp` | GFS-Wave (WAVEWATCH III) forecasts and NDBC buoy wave observations |  |
| `wttr-mcp` | Weather text from wttr.in. No key required. |  |
| `cwa-mcp-server` | MCP server for Taiwan CWA open data: weather forecast, earthquake, warnings, typhoon. | **primary** |

- [ ] верно
- [ ] исправить: 

## gradient#2

Намерение: *conic gradient for a design*. Кластер `misc`.

- `question`: how do I make a conic gradient for a pie-chart-like ring?
- `indirect`: create a circular color sweep for a loading spinner style
- `casual`: conic gradient pls
- `cmd`: conic gradient css

| навык | описание | разметка |
|---|---|---|
| `words` | A daily word puzzle: guess a cheeky British insult or a grim weather word in six tries. Free. |  |
| `benchboss` | Play Chess, RPS-N and Safehouse Protocol via MCP. Public replays; GitHub verification required. |  |
| `loan-schedule` | Amortization schedules for a loan: the level payment, the interest, and what settling early saves. |  |
| `bible-api-mcp` | Read Bible verses and passages in 30+ translations, with reference lookup and a random verse |  |
| `chowdown` | Your recipes as plain files in your own Google Drive, searchable by your AI assistant. |  |
| `gradient` | MCP server for CSS gradient generation — linear, radial, conic | **primary** |
| `equation-steps` | Step-by-step solver for linear/quadratic equations in one variable, signs and ± always right. |  |
| `opportunity-mcp` | Search youth opportunities (scholarships, fellowships, internships) from any AI assistant. |  |
| `rpgmaker-mz-mcp` | MCP server for RPG Maker MZ: maps, tile painting, events, database editing, and validation. |  |
| `esim` | Search & buy travel data eSIMs for 70+ destinations — pay by Stripe link, get the eSIM QR. USD. |  |
| `aviasurf` | Search and compare flight prices, calendars, airports, routes, and destinations with Aviasurf. |  |
| `blender-mcp` | Drive a local Blender headlessly: inspect, convert, render and script 3D files. |  |
| `kilimo-mcp` | Kenya farming guides: crop calendar, fertilizer, pests, market timing, varieties, input costs. |  |

- [ ] верно
- [ ] исправить: 

## hackernews-mcp#2

Намерение: *search Hacker News discussions*. Кластер `news`.

- `verbose`: Find Hacker News threads discussing SQLite in production and show the top comments.
- `indirect`: what did people on the orange tech forum say when this startup launched?
- `cmd`: search hn for "show hn rust"
- `typo`: hackernews coments about bun

| навык | описание | разметка |
|---|---|---|
| `hackernews-mcp` | Hacker News: front page, new and best feeds, item detail, user profiles, full-text search. | **primary** |
| `gdelt-mcp` | Search the global news archive by keyword with recency and language filters. No key required. |  |
| `rss-mcp` | RSS in one place: direct feed parsing and rss2json conversion for any feed URL. No key required. |  |
| `feed-forge` | Turn any website into an RSS, Atom, or JSON feed using CSS selectors and scheduled polling. |  |
| `spaceflight-news-mcp` | Space industry news articles from Spaceflight News. No key required. |  |
| `perigon` | Search real-time news articles, companies, journalists, and trending topics |  |
| `thinkpattern-news` | Grounded, attributed news: what happened, which outlets reported it, and how many covered it. |  |
| `biotech-news` | Biotech News MCP — aggregated biotech & pharma industry news: FDA approvals, clinical readouts… |  |

- [ ] верно
- [ ] исправить: 

## invoicepdfs#1

Намерение: *check an invoice against EN 16931*. Кластер `payments`.

- `cmd`: validate invoice against en 16931
- `verbose`: We invoice German public agencies and need to make sure our invoices comply with the EN 16931 e-invoicing standard.
- `indirect`: will this bill pass the european e-invoicing rules that government buyers require?
- `typo`: check e-invoice compliance en16931

| навык | описание | разметка |
|---|---|---|
| `payport` | Customers, products, prices, invoices, and payments through the Stripe API. |  |
| `stripe-analytics` | Stripe analytics — revenue, customers, subscriptions, refunds, churn from Claude. |  |
| `modern-treasury` | MCP server for Modern Treasury — payment orders, transactions, counterparties and ledgers. |  |
| `invoice-generator` | Free invoice drafts, templates and direct PDF generation for AI agents. No account needed. |  |
| `invoice-reader` | Reads invoices and receipts from PDF to JSON and checks the math. $0.04/page via x402. |  |
| `invoicepdfs` | Render invoices and credit notes as PDFs, and check them against EN 16931 e-invoicing rules. | **primary** |
| `mexico-invoice-mcp` | Mexico CFDI 4.0 invoices for AI agents - issue, query, cancel facturas via Facturapi. |  |
| `coinvello` | Non-custodial crypto payments: checkout sessions, invoices, webhooks and test payments. No KYC. |  |

- [ ] верно
- [ ] исправить: 

## mdpipeline#1

Намерение: *export Jira as local Markdown files*. Кластер `project-management`.

- `cmd`: export jira to markdown files
- `verbose`: I want our team's Jira issues mirrored as Markdown files on my laptop so my coding agent can read them offline.
- `indirect`: keep a local text copy of our atlassian tickets for my agent to read
- `typo`: jira as markdwon local

| навык | описание | разметка |
|---|---|---|
| `mcp-jira-stdio` | MCP server for Jira Cloud — issues, search, comments, attachments, transitions. |  |
| `issueport` | Linear teams, projects, issues and comments via GraphQL, as MCP tools. |  |
| `asana` | Manage tasks, projects, portfolios, and team workflows |  |
| `trello-mcp` | Local Trello MCP with compact responses, workspace allowlists and read-only opt-in. |  |
| `mdpipeline` | Your team's Jira as clean Markdown files, kept current for your AI agent. Local and read-only. | **primary** |
| `estimay` | Planning poker rooms: import stories from Jira or GitHub, run rounds, write the estimates back. |  |
| `standup-mcp` | Generate your daily standup from real GitHub, Jira, Linear, and Slack activity. |  |

- [ ] верно
- [ ] исправить: 

## rpgmaker-mz-mcp#1

Намерение: *edit an RPG Maker MZ map*. Кластер `misc`.

- `cmd`: paint tiles on rpg maker mz map
- `verbose`: In my RPG Maker MZ project, paint a forest area on map 3 and add an NPC event at the village entrance.
- `indirect`: build the town level in my retro jrpg game project with houses and an npc
- `typo`: rpg maker map editing

| навык | описание | разметка |
|---|---|---|
| `words` | A daily word puzzle: guess a cheeky British insult or a grim weather word in six tries. Free. |  |
| `benchboss` | Play Chess, RPS-N and Safehouse Protocol via MCP. Public replays; GitHub verification required. |  |
| `loan-schedule` | Amortization schedules for a loan: the level payment, the interest, and what settling early saves. |  |
| `bible-api-mcp` | Read Bible verses and passages in 30+ translations, with reference lookup and a random verse |  |
| `chowdown` | Your recipes as plain files in your own Google Drive, searchable by your AI assistant. |  |
| `gradient` | MCP server for CSS gradient generation — linear, radial, conic |  |
| `equation-steps` | Step-by-step solver for linear/quadratic equations in one variable, signs and ± always right. |  |
| `opportunity-mcp` | Search youth opportunities (scholarships, fellowships, internships) from any AI assistant. |  |
| `rpgmaker-mz-mcp` | MCP server for RPG Maker MZ: maps, tile painting, events, database editing, and validation. | **primary** |
| `esim` | Search & buy travel data eSIMs for 70+ destinations — pay by Stripe link, get the eSIM QR. USD. |  |
| `aviasurf` | Search and compare flight prices, calendars, airports, routes, and destinations with Aviasurf. |  |
| `blender-mcp` | Drive a local Blender headlessly: inspect, convert, render and script 3D files. |  |
| `kilimo-mcp` | Kenya farming guides: crop calendar, fertilizer, pests, market timing, varieties, input costs. |  |

- [ ] верно
- [ ] исправить: 

## rss-mcp#2

Намерение: *convert RSS to JSON*. Кластер `news`.

- `question`: can you turn this podcast feed into json?
- `indirect`: give me the items of this xml feed as structured data
- `casual`: rss to json pls
- `cmd`: rss2json

| навык | описание | разметка |
|---|---|---|
| `hackernews-mcp` | Hacker News: front page, new and best feeds, item detail, user profiles, full-text search. |  |
| `gdelt-mcp` | Search the global news archive by keyword with recency and language filters. No key required. |  |
| `rss-mcp` | RSS in one place: direct feed parsing and rss2json conversion for any feed URL. No key required. | **primary** |
| `feed-forge` | Turn any website into an RSS, Atom, or JSON feed using CSS selectors and scheduled polling. |  |
| `spaceflight-news-mcp` | Space industry news articles from Spaceflight News. No key required. |  |
| `perigon` | Search real-time news articles, companies, journalists, and trending topics |  |
| `thinkpattern-news` | Grounded, attributed news: what happened, which outlets reported it, and how many covered it. |  |
| `biotech-news` | Biotech News MCP — aggregated biotech & pharma industry news: FDA approvals, clinical readouts… |  |

- [ ] верно
- [ ] исправить: 

## telegram-archive-mcp#1

Намерение: *search old Telegram chats*. Кластер `team-chat`.

- `cmd`: search my telegram archive for "passport"
- `verbose`: Two years ago a friend sent me an apartment address in a Telegram chat; search my archived messages to find it.
- `indirect`: find that message with the wifi password someone sent me ages ago in the blue messenger app
- `typo`: search archived telegarm chats

| навык | описание | разметка |
|---|---|---|
| `mcp-server-slack` | Slack MCP server: channels, messages, threads, reactions, users, files, and scheduled messages |  |
| `slack-explorer-mcp` | MCP server specialized in retrieving information from Slack messages and threads |  |
| `microsoft-teams-mcp` | Microsoft Teams for Claude — read any chat or channel and its unread messages; send and react |  |
| `discord-mcp` | A lightweight, multi-guild Discord MCP server with 95+ tools |  |
| `telegram-archive-mcp` | Search and read your archived Telegram chats and messages | **primary** |
| `telegram-bot-mcp-server` | Self-hosted Telegram Bot MCP server for rich text, media and interactive buttons. |  |
| `telegram-channel-admin` | Run a Telegram channel from your AI agent. Posts go out through your own bot, not your account. |  |
| `yeetpost` | Post and schedule to LinkedIn, X, Bluesky, Discord, Telegram and Mastodon from AI agents. |  |

- [ ] верно
- [ ] исправить: 

## telegram-channel-admin#1

Намерение: *publish a post to a Telegram channel*. Кластер `team-chat`.

- `cmd`: post to my telegram channel
- `verbose`: I run a news channel on Telegram with 20k subscribers; publish today's digest there through my bot.
- `indirect`: send today's update to my subscribers on the messenger channel I run
- `typo`: publsh post in telegram channel

| навык | описание | разметка |
|---|---|---|
| `mcp-server-slack` | Slack MCP server: channels, messages, threads, reactions, users, files, and scheduled messages |  |
| `slack-explorer-mcp` | MCP server specialized in retrieving information from Slack messages and threads |  |
| `microsoft-teams-mcp` | Microsoft Teams for Claude — read any chat or channel and its unread messages; send and react |  |
| `discord-mcp` | A lightweight, multi-guild Discord MCP server with 95+ tools |  |
| `telegram-archive-mcp` | Search and read your archived Telegram chats and messages |  |
| `telegram-bot-mcp-server` | Self-hosted Telegram Bot MCP server for rich text, media and interactive buttons. |  |
| `telegram-channel-admin` | Run a Telegram channel from your AI agent. Posts go out through your own bot, not your account. | **primary** |
| `yeetpost` | Post and schedule to LinkedIn, X, Bluesky, Discord, Telegram and Mastodon from AI agents. |  |

- [ ] верно
- [ ] исправить: 

## viberaven#2

Намерение: *verify webhook and grant configuration before launch*. Кластер `devops`.

- `question`: are our supabase grants and webhooks configured safely for launch?
- `indirect`: audit the database permissions and incoming hooks of our vibe-coded app before shipping
- `casual`: is my supabase setup safe?
- `cmd`: supabase grants webhooks check

| навык | описание | разметка |
|---|---|---|
| `dockerhub` | Docker Hub MCP — wraps the Docker Hub v2 API (free, no auth required for public data) |  |
| `clusterport` | Core kubectl operations: get, describe, logs, apply, scale, patch, rollout and explain. |  |
| `kubeview` | Read-only Model Context Protocol MCP server enabling code-driven AI analysis of Kubernetes clusters. |  |
| `bash-mcp` | Structured JSON wrappers for git, kubectl, terraform, helm, argocd, gh, glab and other CLIs. |  |
| `laravel-forge` | Manage Laravel Forge servers, sites, and deployments from your AI assistant. |  |
| `trigger-dev` | Debug background jobs — runs, traces, spans, schedules, queues and deployments. |  |
| `code-engine-mcp-server` | Deploy to IBM Code Engine from Cursor, Copilot, Claude & Cline. Build, push, deploy via MCP. |  |
| `viberaven` | Checks a Vercel + Supabase repo before deploy: RLS, grants, leaked keys, webhooks. Runs locally. | **primary** |
| `cronicorn-mcp-server` | Manage adaptive cron jobs and HTTP endpoint scheduling via AI assistants. |  |

- [ ] верно
- [ ] исправить: 

## weathersight#2

Намерение: *climate normals and extremes*. Кластер `weather`.

- `question`: what's the record high temperature ever measured in phoenix and the normal for july?
- `indirect`: how hot does it typically get in august in seville compared to its all-time extreme?
- `casual`: hottest day ever recorded in vegas?
- `cmd`: climate normals and extremes for a city

| навык | описание | разметка |
|---|---|---|
| `open-meteo-mcp-server` | Global weather via Open-Meteo: forecast, historical, marine, air quality, geocoding, elevation. |  |
| `weathersight` | Historical weather and climate: 100+ years of station data, normals, extremes, and trends. | **primary** |
| `shearline` | Analyst-grade US severe weather: warnings, SPC outlooks, RAP environment, MRMS, GLM lightning |  |
| `spaceweather-mcp` | Space weather & geomagnetic conditions (NOAA SWPC, NASA DONKI, USGS, Kyoto) via MCP. |  |
| `ww3-mcp` | GFS-Wave (WAVEWATCH III) forecasts and NDBC buoy wave observations |  |
| `wttr-mcp` | Weather text from wttr.in. No key required. |  |
| `cwa-mcp-server` | MCP server for Taiwan CWA open data: weather forecast, earthquake, warnings, typhoon. |  |

- [ ] верно
- [ ] исправить: 

## yahoo-finance-mcp-server#2

Намерение: *compare historical stock prices*. Кластер `market-data`.

- `verbose`: Compare how NVDA, AMD and INTC have performed over the last 5 years, with historical prices.
- `indirect`: which of these three chip companies grew more since 2021?
- `cmd`: compare stock history nvda amd
- `typo`: historical stock prises for google vs meta

| навык | описание | разметка |
|---|---|---|
| `yahoo-finance-mcp-server` | Get real-time stock quotes, historical data, and compare stocks via Yahoo Finance | **primary** |
| `deepviews` | Free financial data: company analysis, DCF, comps, benchmarks, screening. No API key. |  |
| `tickerinside-mcp` | US ETF and mutual fund holdings, which ETFs hold a stock, overlap, look-through. Free, no API key. |  |
| `market-news` | Real-time US stock news, press releases, and legal notices. Pro or trial key required. |  |
| `bolsai-mcp` | Brazilian stock market data (B3, CVM, BCB) for AI assistants: quotes, fundamentals, dividends, FIIs. |  |
| `polymarket-toolkit` | Read-only Polymarket data tools for AI agents: profiles, PnL, market scans. No keys, no orders. |  |
| `municipal-data` | Financial data, fiscal health scores, and economic indicators for 20,000+ U.S. municipalities. |  |

- [ ] верно
- [ ] исправить: 

## yandex-search#1

Намерение: *search results from Yandex*. Кластер `web-search`.

- `cmd`: yandex results for "лучшие ноутбуки 2026"
- `verbose`: Our marketing team targets Russia, so I need to see what Yandex shows for "online accounting service" and the snippets it uses.
- `indirect`: check what the main russian search engine ranks first for "dacha heating"
- `question`: can I get the search result page from yandex for "used cars kazan"?

| навык | описание | разметка |
|---|---|---|
| `serpapi-mcp` | Official SerpApi MCP server for Google, Bing, and other search engines. |  |
| `mcp-google-custom-search` | MCP server for Google Custom Search: web and image search via a Programmable Search Engine. |  |
| `yandex-search` | Yandex search results, images, and SERP data via the Apify Yandex Search Scraper, hosted MCP. | **primary** |
| `miapi` | Web search and AI answers with real source citations and a confidence score. |  |
| `gannet-mcp` | MCP server for web searching and webpage fetching |  |
| `google-serp` | Structured Google search, news, and local results at scale - organic results, news, and local packs |  |
| `seolytics` | SEO & GEO data: keywords, live SERPs with AI Overviews, backlinks, site audits, rank tracking. |  |

- [ ] верно
- [ ] исправить: 
