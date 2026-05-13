TDD-frontend.md
# Charm Studio — Frontend Technical Design Document

## Overview

The **charmkeeper.studio** frontend is a single-page React application styled
with Canonical's [Vanilla Framework](https://vanillaframework.io/). It provides
a project import form, a real-time pipeline progress view, and a session history
sidebar. It communicates exclusively with the `studio_agent` HTTP API.

---

## Design Principles

| Concern | Choice |
|---|---|
| Simple layout primitives, typography, form controls | **Vanilla Framework CSS** |
| Component state, reactivity, conditional rendering | **React 18** |
| HTTP polling | `fetch` + `useEffect` + `setInterval` |
| Routing | **React Router v6** (single route, history via query param) |
| Build tool | **Vite** |

---

## Application Layout

```
┌──────────────────────────────────────────────────────────┐
│  charmkeeper.studio                            [logo]    │
├────────────┬─────────────────────────────────────────────┤
│  Sidebar   │  Main panel                                  │
│            │                                              │
│  History   │  [Import form] ──(submit)──▶ [Progress view]│
│  ─────     │                                              │
│  run #4 ◀  │                                              │
│  run #3    │                                              │
│  run #2    │                                              │
│  run #1    │                                              │
│            │                                              │
└────────────┴─────────────────────────────────────────────┘
```

The sidebar is always visible. The main panel flips between two views:

- **ImportView** — shown when no pipeline is active or selected.
- **PipelineView** — shown after submit, or when a history item is clicked.

---

## Component Tree

```
<App>
  <NavigationBar />          — top Vanilla header bar
  <div class="l-application">
    <Sidebar>
      <HistoryList>
        <HistoryItem />      — one per past pipeline_id
      </HistoryList>
    </Sidebar>
    <main>
      <ImportView />         — project import form
      <PipelineView />       — progress + results
    </main>
  </div>
```

---

## Sidebar — History

- On mount, reads `localStorage` key `cs_history` (array of
  `{pipeline_id, label, timestamp, status}`).
- Each item displays: label (repo name or URL hostname), relative timestamp,
  and a coloured status chip (`pending` / `running` / `done` / `failed`).
- Clicking an item loads that pipeline into **PipelineView** by polling
  `GET /status/<pipeline_id>` once.
- A **New import** button at the top of the sidebar resets to **ImportView**.

---

## ImportView — Project Import Form

Provides three import methods via a Vanilla tab strip:

| Tab | Label | Fields |
|---|---|---|
| `git` | Git | Repository URL, optional branch, optional credentials |
| `bitbucket` | Bitbucket | Workspace / Repo slug, optional branch, access token |
| `url` | Direct URL | Archive URL (`.zip` / `.tar.gz`) |

**Pre-submit flow:**

1. User fills in fields for the chosen tab.
2. Front-end constructs a `project_id` (slug derived from the URL/slug input).
3. On **Submit**, the form is validated client-side (required fields, URL format).
4. A spinner replaces the button; `POST /pipeline { "project_id" }` is called.
5. On success, the returned `pipeline_id` is persisted to history and
   **PipelineView** is shown.
6. On HTTP error, a Vanilla error notification is shown inline.

---

## PipelineView — Progress Display

Polls `GET /status/<pipeline_id>` every **2 seconds** until `done === true`.

### Stage Card

Each of the three stages (`analyze`, `pack`, `deploy`) is rendered as a
Vanilla card with:

| Element | Detail |
|---|---|
| Stage name | Bold heading |
| Status chip | colour-coded: grey=pending, blue=running, green=done, red=failed |
| Elapsed time | live timer while `running`, total duration once `done`/`failed` |
| Log accordion | collapsed by default; expands to show `stdout` + `stderr` |

### Terminal-style Log Panel

A scrollable `<pre>` block per stage, styled with a dark background, renders
the captured `stdout` / `stderr` text. Auto-scrolls to the bottom while running.

### Cancel Button

A **Cancel pipeline** button (Vanilla `p-button--negative`) is rendered in the
PipelineView header whenever `done === false`. Clicking it:

1. Sends `DELETE /pipeline/<pipeline_id>` to the backend.
2. Disables the button and shows an inline spinner to prevent double-clicks.
3. On `204 No Content` — stops the polling loop, marks the history entry
   `status: "cancelled"`, and shows a Vanilla caution notification:
   _"Pipeline cancelled. Partially completed stages are preserved in the log."_
4. On error — shows an error notification; polling resumes.

The button is hidden once `done === true` (success, failure, or cancellation).

---

### Result Banner

Shown only when `done === true` and `error === null`:

```
✅  Pipeline complete
    Charm:   /path/to/charm.charm
    Rock:    /path/to/image.rock
    Model:   <juju_model>
    App:     <juju_app>
```

### Error Banner

Shown when `error !== null`. Displays the error string and highlights the
failed stage card with a red border.

---

## API Contract (Frontend perspective)

| Method | Path | Trigger |
|---|---|---|
| `POST /pipeline` | `{ "project_id": string }` | Submit button |
| `GET /status/<pipeline_id>` | — | After submit (2 s poll), and on history item click |
| `DELETE /pipeline/<pipeline_id>` | — | Cancel button (only while `done === false`) |

All requests include `Content-Type: application/json`. The base URL is read
from the `VITE_API_BASE_URL` environment variable (defaults to `http://localhost:8000`).

---

## State Machine (ImportView → PipelineView)

```
IDLE  ──(submit)──▶  SUBMITTING  ──(201 OK)──▶  POLLING
                           │                        │  │
                           └─(4xx/5xx)──▶  ERROR   │  └─(done=true)──▶  DONE
                                                    │  │
                                                    │  └─(error≠null)──▶  FAILED
                                                    │
                                                    └─(cancel click)──▶  CANCELLING
                                                                              │
                                                          (204 OK) ──────────┘──▶  CANCELLED
                                                          (error)  ────────────▶  POLLING (resume)
```

---

## Local Storage Schema

```json
{
  "cs_history": [
    {
      "pipeline_id": "a1b2c3",
      "label": "my-charm-repo",
      "timestamp": "2026-05-13T07:00:00Z",
      "status": "done | cancelled"
    }
  ]
}
```

History is capped at **20 entries** (oldest evicted first). Status is updated
each time the associated pipeline is polled to completion.

---

## Project Layout

```
frontend/
├── index.html
├── vite.config.ts
├── src/
│   ├── main.tsx               — React root, Router
│   ├── App.tsx                — top-level layout
│   ├── components/
│   │   ├── NavigationBar.tsx
│   │   ├── Sidebar/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── HistoryList.tsx
│   │   │   └── HistoryItem.tsx
│   │   ├── ImportView/
│   │   │   ├── ImportView.tsx
│   │   │   ├── GitTab.tsx
│   │   │   ├── BitbucketTab.tsx
│   │   │   └── UrlTab.tsx
│   │   └── PipelineView/
│   │       ├── PipelineView.tsx
│   │       ├── StageCard.tsx
│   │       ├── LogPanel.tsx
│   │       ├── ResultBanner.tsx
│   │       └── ErrorBanner.tsx
│   ├── hooks/
│   │   ├── usePipelineStatus.ts   — polling hook (GET /status)
│   │   └── useHistory.ts          — localStorage CRUD
│   ├── api/
│   │   └── client.ts              — fetch wrappers for POST /pipeline, GET /status
│   └── types.ts                   — PipelineStatus, Stage, HistoryEntry interfaces
├── public/
│   └── favicon.ico
└── .env.example                   — VITE_API_BASE_URL=http://localhost:8000
```

---

## Vanilla Framework Integration

- Load Vanilla via npm (`vanilla-framework` package); import `scss` in `main.tsx`.
- Use Vanilla utility classes for layout (`l-application`, `l-aside`), buttons
  (`p-button--positive`), notifications (`p-notification--caution`), chips
  (`p-chip`), and tabs (`p-tabs`).
- Avoid custom CSS where a Vanilla pattern exists; only add project-specific
  overrides in a `custom.scss` file.

---

## Future Considerations

- **Log streaming** — replace polling with `EventSource` (SSE) once a
  `GET /logs/<pipeline_id>` endpoint is available.
- **Graceful shutdown** — on cancellation, show which stage was interrupted and
  offer a **Re-run from this stage** shortcut once individual stage endpoints
  (`POST /analyze`, `POST /pack`, `POST /deploy`) are available.
- **Auth** — add Candid/SSO token header once multi-user support is needed.
- **Dark mode** — Vanilla provides a dark theme toggle; wire it to
  `prefers-color-scheme`.
