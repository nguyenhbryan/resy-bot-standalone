# Graph Report - resy-bot  (2026-06-11)

## Corpus Check
- 62 files · ~23,872 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 564 nodes · 1992 edges · 38 communities (27 shown, 11 thin omitted)
- Extraction: 45% EXTRACTED · 55% INFERRED · 0% AMBIGUOUS · INFERRED: 1104 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5b1dd0b8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Job Store And Selectors|Job Store And Selectors]]
- [[_COMMUNITY_Pydantic API Models|Pydantic API Models]]
- [[_COMMUNITY_Reservation Manager|Reservation Manager]]
- [[_COMMUNITY_SSR Reservation Form|SSR Reservation Form]]
- [[_COMMUNITY_Resy API Access|Resy API Access]]
- [[_COMMUNITY_Docs And Deployment|Docs And Deployment]]
- [[_COMMUNITY_Frontend Package Config|Frontend Package Config]]
- [[_COMMUNITY_Venue Resolver Cache|Venue Resolver Cache]]
- [[_COMMUNITY_Model Builders Tests|Model Builders Tests]]
- [[_COMMUNITY_TypeScript Compiler Config|TypeScript Compiler Config]]
- [[_COMMUNITY_Graphify Workflow Docs|Graphify Workflow Docs]]
- [[_COMMUNITY_Backend App Services|Backend App Services]]
- [[_COMMUNITY_App Layout Metadata|App Layout Metadata]]
- [[_COMMUNITY_Demo Experience|Demo Experience]]
- [[_COMMUNITY_Access Gate Page|Access Gate Page]]
- [[_COMMUNITY_Slot Validators|Slot Validators]]
- [[_COMMUNITY_ESLint Config|ESLint Config]]
- [[_COMMUNITY_Next Config|Next Config]]
- [[_COMMUNITY_PostCSS Config|PostCSS Config]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]

## God Nodes (most connected - your core abstractions)
1. `ReservationRequest` - 80 edges
2. `Slot` - 70 edges
3. `ResyConfig` - 68 edges
4. `TimedReservationRequest` - 60 edges
5. `ResyManager` - 57 edges
6. `ResyApiAccess` - 51 edges
7. `BookingMethod` - 47 edges
8. `FindRequestBody` - 46 edges
9. `AuthRequestBody` - 45 edges
10. `DetailsRequestBody` - 45 edges

## Surprising Connections (you probably didn't know these)
- `Globe Icon` --semantically_similar_to--> `Next.js Frontend`  [INFERRED] [semantically similar]
  frontend/public/globe.svg → README.md
- `Browser Window Icon` --semantically_similar_to--> `Reservation Console`  [INFERRED] [semantically similar]
  frontend/public/window.svg → README.md
- `Next.js Logo` --references--> `Next.js Frontend`  [INFERRED]
  frontend/public/next.svg → README.md
- `CLAUDE.md Integration` --semantically_similar_to--> `graphify Agent Rules`  [INFERRED] [semantically similar]
  .codex/skills/graphify/references/hooks.md → AGENTS.md
- `Document File Icon` --semantically_similar_to--> `Next.js Create App README`  [INFERRED] [semantically similar]
  frontend/public/file.svg → frontend/README.md

## Import Cycles
- 1-file cycle: `backend/resy_bot/manager.py -> backend/resy_bot/manager.py`
- 2-file cycle: `backend/resy_bot/manager.py -> backend/resy_bot/selectors.py -> backend/resy_bot/manager.py`
- 2-file cycle: `backend/resy_bot/manager.py -> backend/resy_bot/venue_resolver.py -> backend/resy_bot/manager.py`
- 2-file cycle: `backend/resy_bot/api_access.py -> backend/resy_bot/manager.py -> backend/resy_bot/api_access.py`
- 2-file cycle: `backend/resy_bot/manager.py -> backend/resy_bot/model_builders.py -> backend/resy_bot/manager.py`
- 2-file cycle: `backend/resy_bot/manager.py -> backend/resy_bot/models.py -> backend/resy_bot/manager.py`
- 3-file cycle: `backend/resy_bot/manager.py -> backend/resy_bot/selectors.py -> backend/resy_bot/models.py -> backend/resy_bot/manager.py`
- 3-file cycle: `backend/resy_bot/api_access.py -> backend/resy_bot/venue_resolver.py -> backend/resy_bot/manager.py -> backend/resy_bot/api_access.py`
- 3-file cycle: `backend/resy_bot/api_access.py -> backend/resy_bot/models.py -> backend/resy_bot/manager.py -> backend/resy_bot/api_access.py`
- 3-file cycle: `backend/resy_bot/manager.py -> backend/resy_bot/model_builders.py -> backend/resy_bot/models.py -> backend/resy_bot/manager.py`

## Hyperedges (group relationships)
- **graphify Pipeline Reference Docs** — graphify_skill_graphify, references_extraction_spec_semantic_extraction_schema, references_query_graphify_query, references_update_incremental_update, references_exports_optional_exports, references_add_watch_url_ingest, references_transcribe_video_audio_transcription, references_hooks_post_commit_hook, references_github_and_merge_cross_repo_merge [EXTRACTED 1.00]
- **Dockerized Full Stack App** — workflows_docker_docker_ci, docker_docker_compose_runtime, compose_backend_service, compose_frontend_service, readme_fastapi_backend, readme_nextjs_frontend [EXTRACTED 1.00]
- **Reservation Console Capabilities** — readme_resy_bot, readme_reservation_console, readme_venue_search, readme_sqlite_job_persistence, readme_access_key_gate, backend_readme_timed_reservation_request [EXTRACTED 1.00]

## Communities (38 total, 11 thin omitted)

### Community 0 - "Job Store And Selectors"
Cohesion: 0.10
Nodes (71): AbstractSelector, load_backend_env(), _load_env_file(), StoredJob, cancel_job(), _format_time(), get_job(), _job_reservation_details() (+63 more)

### Community 1 - "Pydantic API Models"
Cohesion: 0.28
Nodes (62): AuthResponseBody, Any, AuthRequestBody, BookRequestBody, DetailsRequestBody, DetailsResponseBody, FindRequestBody, ResyConfig (+54 more)

### Community 2 - "Reservation Manager"
Cohesion: 0.08
Nodes (35): ABC, datetime, _load_app_timezone(), cycle until we hit the opening time, then run & return the reservation, ResyManager, build_auth_request_body(), build_find_request_body(), simple selection algo that assumes a sorted list of slots         if preferred s (+27 more)

### Community 3 - "SSR Reservation Form"
Cohesion: 0.07
Nodes (41): apiRequest(), ApiSlot, ApiVenue, buildReservationRequest(), canCancelJob(), cancelJob(), checkSlots(), createReservation() (+33 more)

### Community 4 - "Resy API Access"
Cohesion: 0.12
Nodes (14): build_session(), requests lib doesn't urlencode nested dictionaries,         so dump struct_payme, ResyApiAccess, test_auth(), test_bad_auth(), test_book_slot(), test_book_slot_bad_resp(), test_build_session() (+6 more)

### Community 5 - "Docs And Deployment"
Cohesion: 0.05
Nodes (43): Python Quality Hooks, Command Line Execution, Dependencies, Local Configuration, Resy API Credentials, Resy-Bot, ResyConfig, Running (+35 more)

### Community 6 - "Frontend Package Config"
Cohesion: 0.08
Nodes (24): dependencies, next, react, react-dom, devDependencies, eslint, eslint-config-next, tailwindcss (+16 more)

### Community 7 - "Venue Resolver Cache"
Cohesion: 0.18
Nodes (9): Any, Connection, Path, Row, normalize_venue_text(), _now(), _venue_cache_path(), VenueCache (+1 more)

### Community 8 - "Model Builders Tests"
Cohesion: 0.10
Nodes (9): date, test_monitor_reserve_books_first_acceptable_date(), test_reserve_creates_job(), test_slots(), test_slots_returns_monitor_slots_by_date(), test_monitor_accepts_multiple_dates_and_preserves_order(), test_monitor_uses_legacy_ideal_date_as_single_monitor_date(), test_scheduled_accepts_ideal_date() (+1 more)

### Community 9 - "TypeScript Compiler Config"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 10 - "Graphify Workflow Docs"
Cohesion: 0.05
Nodes (40): graphify Agent Rules, Existing Graph Fast Path, For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, Graph Outputs, /graphify (+32 more)

### Community 11 - "Backend App Services"
Cohesion: 0.21
Nodes (6): _database_path(), JobStore, _now(), Connection, Path, Row

### Community 12 - "App Layout Metadata"
Cohesion: 0.40
Nodes (3): geistMono, geistSans, metadata

### Community 13 - "Demo Experience"
Cohesion: 0.40
Nodes (3): bookingSteps, demoSlots, DemoStage

### Community 14 - "Access Gate Page"
Cohesion: 0.83
Nodes (3): getAccessToken(), Home(), verifyKey()

### Community 24 - "Community 24"
Cohesion: 0.25
Nodes (7): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 25 - "Community 25"
Cohesion: 0.50
Nodes (3): Deploy on Vercel, Getting Started, Learn More

### Community 26 - "Community 26"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 27 - "Community 27"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 28 - "Community 28"
Cohesion: 0.50
Nodes (3): For /graphify explain, For /graphify path, graphify reference: query, path, explain

### Community 29 - "Community 29"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

## Knowledge Gaps
- **138 isolated node(s):** `Path`, `Connection`, `Row`, `Connection`, `Row` (+133 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `datetime` connect `Reservation Manager` to `Job Store And Selectors`, `Pydantic API Models`, `Resy API Access`, `Venue Resolver Cache`, `Model Builders Tests`, `Backend App Services`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `ResyApiAccess` connect `Resy API Access` to `Job Store And Selectors`, `Pydantic API Models`, `Reservation Manager`, `Venue Resolver Cache`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `ResyManager` connect `Reservation Manager` to `Job Store And Selectors`, `Pydantic API Models`, `Resy API Access`, `Venue Resolver Cache`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Are the 71 inferred relationships involving `ReservationRequest` (e.g. with `AbstractSelector` and `JobStatus`) actually correct?**
  _`ReservationRequest` has 71 INFERRED edges - model-reasoned connections that need verification._
- **Are the 68 inferred relationships involving `Slot` (e.g. with `JobStatus` and `ReservationDetails`) actually correct?**
  _`Slot` has 68 INFERRED edges - model-reasoned connections that need verification._
- **Are the 65 inferred relationships involving `ResyConfig` (e.g. with `AbstractSelector` and `AuthResponseBody`) actually correct?**
  _`ResyConfig` has 65 INFERRED edges - model-reasoned connections that need verification._
- **Are the 58 inferred relationships involving `TimedReservationRequest` (e.g. with `AbstractSelector` and `JobStatus`) actually correct?**
  _`TimedReservationRequest` has 58 INFERRED edges - model-reasoned connections that need verification._