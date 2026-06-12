# Graph Report - .  (2026-06-11)

## Corpus Check
- Corpus is ~22,244 words - fits in a single context window. You may not need a graph.

## Summary
- 449 nodes · 1791 edges · 24 communities (20 shown, 4 thin omitted)
- Extraction: 42% EXTRACTED · 58% INFERRED · 0% AMBIGUOUS · INFERRED: 1039 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

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

## God Nodes (most connected - your core abstractions)
1. `ReservationRequest` - 73 edges
2. `Slot` - 68 edges
3. `ResyConfig` - 65 edges
4. `TimedReservationRequest` - 58 edges
5. `ResyManager` - 52 edges
6. `ResyApiAccess` - 50 edges
7. `FindRequestBody` - 44 edges
8. `AuthRequestBody` - 43 edges
9. `DetailsRequestBody` - 43 edges
10. `DetailsResponseBody` - 43 edges

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
- 2-file cycle: `backend/resy_bot/api_access.py -> backend/resy_bot/manager.py -> backend/resy_bot/api_access.py`
- 2-file cycle: `backend/resy_bot/manager.py -> backend/resy_bot/model_builders.py -> backend/resy_bot/manager.py`
- 2-file cycle: `backend/resy_bot/manager.py -> backend/resy_bot/models.py -> backend/resy_bot/manager.py`
- 2-file cycle: `backend/resy_bot/manager.py -> backend/resy_bot/selectors.py -> backend/resy_bot/manager.py`
- 2-file cycle: `backend/resy_bot/manager.py -> backend/resy_bot/venue_resolver.py -> backend/resy_bot/manager.py`
- 3-file cycle: `backend/resy_bot/api_access.py -> backend/resy_bot/models.py -> backend/resy_bot/manager.py -> backend/resy_bot/api_access.py`
- 3-file cycle: `backend/resy_bot/api_access.py -> backend/resy_bot/venue_resolver.py -> backend/resy_bot/manager.py -> backend/resy_bot/api_access.py`
- 3-file cycle: `backend/resy_bot/manager.py -> backend/resy_bot/model_builders.py -> backend/resy_bot/models.py -> backend/resy_bot/manager.py`
- 3-file cycle: `backend/resy_bot/manager.py -> backend/resy_bot/selectors.py -> backend/resy_bot/models.py -> backend/resy_bot/manager.py`

## Hyperedges (group relationships)
- **graphify Pipeline Reference Docs** — graphify_skill_graphify, references_extraction_spec_semantic_extraction_schema, references_query_graphify_query, references_update_incremental_update, references_exports_optional_exports, references_add_watch_url_ingest, references_transcribe_video_audio_transcription, references_hooks_post_commit_hook, references_github_and_merge_cross_repo_merge [EXTRACTED 1.00]
- **Dockerized Full Stack App** — workflows_docker_docker_ci, docker_docker_compose_runtime, compose_backend_service, compose_frontend_service, readme_fastapi_backend, readme_nextjs_frontend [EXTRACTED 1.00]
- **Reservation Console Capabilities** — readme_resy_bot, readme_reservation_console, readme_venue_search, readme_sqlite_job_persistence, readme_access_key_gate, backend_readme_timed_reservation_request [EXTRACTED 1.00]

## Communities (24 total, 4 thin omitted)

### Community 0 - "Job Store And Selectors"
Cohesion: 0.10
Nodes (56): AbstractSelector, _database_path(), JobStore, _now(), StoredJob, cancel_job(), _format_time(), get_job() (+48 more)

### Community 1 - "Pydantic API Models"
Cohesion: 0.32
Nodes (58): AuthResponseBody, Any, AuthRequestBody, BookRequestBody, DetailsRequestBody, DetailsResponseBody, FindRequestBody, ResyConfig (+50 more)

### Community 2 - "Reservation Manager"
Cohesion: 0.08
Nodes (31): ABC, ReservationRequest, ResolvedVenue, datetime, Enum, _load_app_timezone(), _raise_if_cancelled(), cycle until we hit the opening time, then run & return the reservation (+23 more)

### Community 3 - "SSR Reservation Form"
Cohesion: 0.09
Nodes (29): apiRequest(), ApiSlot, ApiVenue, buildReservationRequest(), cancelJob(), checkSlots(), createReservation(), decodeSlotResult() (+21 more)

### Community 4 - "Resy API Access"
Cohesion: 0.11
Nodes (15): VenueCandidate, build_session(), requests lib doesn't urlencode nested dictionaries,         so dump struct_payme, ResyApiAccess, test_auth(), test_bad_auth(), test_book_slot(), test_book_slot_bad_resp() (+7 more)

### Community 5 - "Docs And Deployment"
Cohesion: 0.10
Nodes (27): Python Quality Hooks, Resy API Credentials, TimedReservationRequest, API MVP Phases, backend_data Volume, Backend Service, Frontend Service, Docker Compose Runtime (+19 more)

### Community 6 - "Frontend Package Config"
Cohesion: 0.08
Nodes (24): dependencies, next, react, react-dom, devDependencies, eslint, eslint-config-next, tailwindcss (+16 more)

### Community 7 - "Venue Resolver Cache"
Cohesion: 0.19
Nodes (10): Any, Connection, Path, Row, normalize_venue_text(), _now(), _venue_cache_path(), VenueCache (+2 more)

### Community 8 - "Model Builders Tests"
Cohesion: 0.11
Nodes (10): date, build_auth_request_body(), build_book_request_body(), build_get_slot_details_body(), test_reserve_creates_job(), test_slots(), test_build_auth_request_body(), test_build_book_request_body() (+2 more)

### Community 9 - "TypeScript Compiler Config"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 10 - "Graphify Workflow Docs"
Cohesion: 0.13
Nodes (18): graphify Agent Rules, Existing Graph Fast Path, Graph Outputs, graphify Skill, Semantic Extraction Subagents, Structural AST Extraction, Folder Watch, URL Ingest (+10 more)

### Community 11 - "Backend App Services"
Cohesion: 0.23
Nodes (15): load_backend_env(), _load_env_file(), Path, Event, ReservationRequest, ResyConfig, TimedReservationRequest, ResyManager (+7 more)

### Community 12 - "App Layout Metadata"
Cohesion: 0.40
Nodes (3): geistMono, geistSans, metadata

### Community 13 - "Demo Experience"
Cohesion: 0.40
Nodes (3): bookingSteps, demoSlots, DemoStage

### Community 14 - "Access Gate Page"
Cohesion: 0.83
Nodes (3): getAccessToken(), Home(), verifyKey()

## Knowledge Gaps
- **80 isolated node(s):** `Path`, `Connection`, `Row`, `Connection`, `Row` (+75 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `datetime` connect `Reservation Manager` to `Job Store And Selectors`, `Pydantic API Models`, `Resy API Access`, `Venue Resolver Cache`, `Model Builders Tests`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Why does `ResyApiAccess` connect `Resy API Access` to `Job Store And Selectors`, `Pydantic API Models`, `Reservation Manager`, `Venue Resolver Cache`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `ResyManager` connect `Reservation Manager` to `Job Store And Selectors`, `Pydantic API Models`, `Resy API Access`, `Venue Resolver Cache`, `Backend App Services`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Are the 68 inferred relationships involving `ReservationRequest` (e.g. with `AbstractSelector` and `JobStatus`) actually correct?**
  _`ReservationRequest` has 68 INFERRED edges - model-reasoned connections that need verification._
- **Are the 66 inferred relationships involving `Slot` (e.g. with `JobStatus` and `ReservationDetails`) actually correct?**
  _`Slot` has 66 INFERRED edges - model-reasoned connections that need verification._
- **Are the 62 inferred relationships involving `ResyConfig` (e.g. with `AbstractSelector` and `AuthResponseBody`) actually correct?**
  _`ResyConfig` has 62 INFERRED edges - model-reasoned connections that need verification._
- **Are the 56 inferred relationships involving `TimedReservationRequest` (e.g. with `AbstractSelector` and `JobStatus`) actually correct?**
  _`TimedReservationRequest` has 56 INFERRED edges - model-reasoned connections that need verification._