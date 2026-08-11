# Web UI Plan

This document captures the proposed architecture and implementation plan for the `snipcontext serve` web dashboard.

## Goal
Provide a modern, responsive web dashboard that makes SnipContext accessible to non‑CLI users and complements the editor plugins.

## Tech Stack
| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Backend** | Existing FastAPI + WebSocket (`fastapi` + `websockets`) | Reuse the current `snipcontext serve` API; add WebSocket for live index updates |
| **Frontend** | React + TypeScript + Vite | Lightweight, fast, component-based |
| **UI Library** | Tailwind CSS + shadcn/ui | Clean, accessible, easy to customize |
| **State** | React Query | Server state, caching, and mutations |
| **Routing** | React Router | Dashboard navigation |

## Core Features (MVP)
1. **Dashboard**
   - Total snippet count, language breakdown, last updated.
   - Recent snippets (sorted by `updated_at`).
   - Quick search bar with semantic/hybrid toggle.

2. **Search & Browse**
   - Debounced search input with live results.
   - Filter by tags, language, framework.
   - Sort by relevance, date, title.
   - Pagination / infinite scroll.

3. **Snippet View/Edit**
   - Expand snippet in a modal or detail panel.
   - Metadata: title, language, tags, framework, version, source.
   - Inline edit with auto-save.
   - Soft delete with confirmation.

4. **Export Integration**
   - Download selected snippets as Claude XML, OpenAI, Cursor, or Generic Markdown.
   - Batch selection support.

5. **Tag Management**
   - Tag cloud or list with counts.
   - Rename/merge tags.

6. **Search Index Status**
   - Show index type (FLAT/IVFPQ), vector count, last rebuild time.
   - Trigger rebuild from the UI.

## API Enhancements Needed
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/snippets` | GET | List with pagination, sorting, filtering |
| `/snippets/{id}` | GET | Get single snippet with full metadata |
| `/snippets/{id}` | PUT | Update snippet |
| `/snippets/{id}` | DELETE | Soft delete |
| `/tags` | GET | List tags with counts |
| `/tags/{tag}` | PUT | Rename tag |
| `/tags/{tag}` | DELETE | Remove tag |
| `/search` | GET | Search (`q`, `mode`, `top_k`, `filter`) |
| `/export` | POST | Export selected snippets by format |
| `/index/status` | GET | Index type, vector count, last rebuild |
| `/index/rebuild` | POST | Trigger background rebuild |
| `/ws` | WebSocket | Push index status and watcher events |

## UI Layout
- **Sidebar**: navigation (Dashboard, Snippets, Tags, Export, Settings).
- **Main Area**: context-sensitive view based on route.
- **Detail View**: modal or right drawer for snippet editing.
- **Tags**: tag cloud/list with filtering.
- **Export**: selection + format dropdown + download.

## Implementation Phases
1. **Phase 0** – API augmentation
2. **Phase 1** – Frontend skeleton
3. **Phase 2** – Search & browse
4. **Phase 3** – Snippet detail & editing
5. **Phase 4** – Tag management
6. **Phase 5** – Export integration
7. **Phase 6** – Index management

## Timeline
- **Phase 0**: 2 days
- **Phase 1**: 3 days
- **Phase 2**: 3 days
- **Phase 3**: 2 days
- **Phase 4**: 2 days
- **Phase 5**: 1 day
- **Phase 6**: 1 day
- **Total MVP**: ~14 days

## Next Step
Begin **Phase 0** by drafting backend API additions and a WebSocket skeleton.
