# World Historian Dashboard Specification

**Document:** `WORLD_HISTORIAN_DASHBOARD_SPEC.md`  
**Status:** Implementation specification  
**Version:** 1.0  
**Date:** 2026-09-28  
**Primary surface:** Obsidian desktop plugin view  
**Product:** PAP / World Historian

---

## 1. Purpose

The World Historian Dashboard is an interactive read and navigation layer for the World Historian corpus.

It is **not** a Markdown dashboard, BI dashboard, news reader, generic knowledge graph, or second source of truth. It is an application-like Obsidian workspace view over World Historian's structured historical objects.

The dashboard must make the same corpus explorable through multiple projections:

- **Thread** — narrative / problem-space projection.
- **Timeline** — temporal projection.
- **Entity** — cross-thread index projection.
- **Map** — geographic projection.
- **Graph** — relational projection.

Local statistical charts may appear where they help interpret a specific Thread, Entity, or filtered scope, but charts are not a primary navigation surface.

The central product idea is:

> **Thread is the narrative unit; Event is the temporal unit; Claim/Source are epistemic units; Entity is a cross-cutting projection; Map and Graph are spatial and relational projections of the same underlying historical corpus.**

---

## 2. Goals

### G1 — Make Threads the primary browsing object

The default dashboard must answer:

- What Threads are active?
- Which Threads have materially changed?
- Which Threads need attention?
- What is the current state of a Thread?
- What questions remain unresolved?
- What happened inside the Thread and when?

### G2 — Preserve historical and epistemic structure

The UI must visually distinguish:

- Event.
- Claim.
- Source.
- Open Question.
- Manual annotation.
- Generated synthesis.
- Corrected / superseded claim.
- Uncertain or analytical statement.

The dashboard must not visually flatten all content into undifferentiated prose.

### G3 — Support Time × Space × Relation

A user must be able to examine the same scoped corpus as:

- chronological activity;
- geographic activity;
- relational structure.

Filters applied in one projection should carry into the others when semantically valid.

### G4 — Remain auditable

Every important rendered object must be traceable back to its canonical World Historian representation or artifact.

The UI must make it easy to open the underlying Thread note, Event source material, or canonical record.

### G5 — Keep the dashboard local-first and rebuildable

The dashboard read model must be disposable and derivable from canonical World Historian data.

Deleting dashboard indexes must not destroy historical knowledge.

### G6 — Behave like an app page inside Obsidian

The primary implementation surface must be an Obsidian `ItemView`, not a generated Markdown note.

The experience should support:

- persistent toolbar;
- search;
- filters;
- multi-pane layouts;
- keyboard navigation;
- interactive inspection;
- list/timeline/map/graph switching;
- responsive resizing;
- theme integration.

---

## 3. Non-goals

The following are explicitly outside the initial scope:

- AI chat over the historian corpus.
- General-purpose BI / analytics workspace.
- Editing dashboard JSON directly as canonical state.
- Replacing the original World Historian Markdown/artifacts.
- Automatically writing new historical conclusions from UI browsing.
- Full arbitrary graph-database authoring.
- Social sharing or cloud collaboration.
- Real-time multi-user synchronization.
- A generic Obsidian knowledge graph replacement.
- A generic map of all notes in the Vault.

Local contextual charts are allowed, but a dedicated top-level `Analytics` page is not part of this specification.

---

## 4. Product Principles

### P1 — One corpus, multiple projections

Timeline, Map, Graph, Entity, and Thread views must operate over the same normalized read model.

They must not maintain independent interpretations of the source material.

### P2 — Read model, not second truth store

The dashboard may cache and index aggressively, but canonical historical state remains outside the dashboard read model.

The read model must be:

- schema-versioned;
- deterministic where possible;
- disposable;
- rebuildable;
- incrementally refreshable;
- traceable to source objects.

### P3 — Meaningful change over file modification

`mtime` is not historical freshness.

Where possible, the dashboard must distinguish:

- last Event occurrence;
- last Claim change;
- last Open Question change;
- last source ingestion;
- last manual annotation;
- last projector rebuild.

The default "recently updated" ordering should use **last meaningful historical change**, not file modification time alone.

### P4 — Dense, calm, inspectable

The interface should optimize for high information density without visual noise.

Avoid:

- decorative gradients;
- excessive large cards;
- dashboard wallpaper metrics;
- graph hairballs;
- meaningless map markers;
- animation for its own sake.

Prefer:

- compact badges;
- strong titles;
- weak metadata;
- clear hierarchy;
- restrained separators;
- expandable detail;
- persistent context.

### P5 — Progressive disclosure

List views expose only enough information to decide what to inspect.

Epistemic depth should unfold as:

`Thread → Event → Claim → Source`

or:

`Entity → Thread/Event → Claim → Source`

The default UI must not display full source payloads.

---

## 5. Domain Model

The dashboard read model recognizes the following object classes.

### 5.1 Thread

A Thread is the primary narrative and monitoring unit.

Minimum dashboard semantics:

```text
Thread
├── identity
├── status
├── priority
├── current state
├── time range
├── latest meaningful change
├── open questions
├── events
├── entities
├── locations
├── related threads
├── watch state / watch queries
├── annotations
└── canonical source reference
```

Suggested status values:

```text
active
watching
dormant
resolved
archived
```

Suggested priority values:

```text
high
normal
low
```

The dashboard must not hard-code these values if World Historian already emits a canonical vocabulary. The projector should normalize source vocabularies into a stable dashboard enum.

### 5.2 Event

An Event is a historical occurrence inside one or more Threads.

Important time fields may include:

```text
occurred_at
published_at
first_observed_at
updated_at
```

The default timeline position uses `occurred_at` where known.

If `occurred_at` is uncertain or interval-valued, the UI must expose that uncertainty instead of silently inventing precision.

### 5.3 Claim

A Claim is a proposition associated with an Event, Thread, Entity, or source.

Recommended claim states:

```text
supported
uncertain
analytical
contested
corrected
superseded
retracted
```

A Claim may reference one or more supporting and contradicting Sources.

### 5.4 Source

A Source is the evidence or publication backing a Claim/Event.

The dashboard stores only bounded source metadata and references needed for browsing.

It must not duplicate full raw source bodies unless the canonical historian architecture already requires such a cache.

### 5.5 Open Question

An Open Question represents unresolved historical uncertainty.

Suggested states:

```text
open
partially_answered
answered
expired
```

Questions may belong to Threads, Events, or Entities.

### 5.6 Entity

An Entity is a cross-thread indexable object.

Initial entity kinds:

```text
person
organization
country
government_body
place
product
technology
project
other
```

The dashboard should support unknown/custom kinds without crashing.

### 5.7 Location

A Location is a normalized geographic object suitable for Map projection.

A Location should include:

```text
location_id
name
kind
country_code?
region?
lat?
lon?
geo_precision
canonical_source_ref?
```

Suggested `geo_precision`:

```text
exact
city
region
country
approximate
unknown
```

The UI must not pretend that country-level evidence is city-level evidence.

### 5.8 Relation

Relations power the Graph projection.

A relation should contain:

```text
relation_id
source_node_id
target_node_id
type
direction
confidence?
occurred_at?
valid_from?
valid_to?
evidence_refs[]
```

Initial relation types may include:

```text
thread_related_to_thread
thread_contains_event
thread_involves_entity
event_involves_entity
event_occurs_at_location
claim_about_entity
claim_supported_by_source
claim_contradicted_by_source
entity_related_to_entity
question_about_entity
question_about_thread
```

---

## 6. Application Shell

### 6.1 Top-level navigation

The dashboard must provide these top-level views:

```text
Threads | Timeline | Entities | Map | Graph
```

No top-level `Analytics` view is required.

### 6.2 Global toolbar

All top-level views share a common shell with:

- global search;
- current scope summary;
- date-range filter;
- status filter;
- priority filter;
- entity filter;
- Thread filter;
- location filter where relevant;
- refresh action;
- open settings action;
- view-specific controls.

### 6.3 Global scope state

The app maintains a shared `DashboardScope`.

Example:

```json
{
  "date_range": {
    "mode": "relative",
    "value": "30d"
  },
  "thread_ids": [],
  "entity_ids": [],
  "location_ids": [],
  "statuses": ["active", "watching"],
  "priorities": [],
  "claim_states": [],
  "search": ""
}
```

Requirements:

- Switching `Timeline → Map → Graph` should preserve compatible scope.
- Opening a Thread detail adds that Thread as local context without destroying the global scope.
- Users must be able to clear scope in one action.
- View-specific filters may extend but not silently mutate the global scope.

### 6.4 Workspace behavior

The dashboard should open in a dedicated Obsidian `ItemView`.

Preferred behavior:

- one primary World Historian dashboard leaf;
- reopening the dashboard focuses the existing leaf by default;
- Thread/Entity detail may appear within the same view;
- optionally support "open detail in new leaf" later.

---

## 7. Threads Browser

### 7.1 Purpose

The Threads Browser is the default landing page.

It answers:

> What historical Threads exist, what has changed, and what deserves attention?

### 7.2 Layout

Desktop default:

```text
┌───────────────┬──────────────────────────────┬───────────────────────┐
│ Saved Views   │ Thread List                  │ Inspector             │
│ Filters       │                              │                       │
│ Counts        │                              │                       │
└───────────────┴──────────────────────────────┴───────────────────────┘
```

At medium width:

```text
Sidebar | Thread List
```

Inspector becomes a drawer.

At narrow width:

```text
Thread List
```

Filters and inspector become overlay panels.

### 7.3 Saved views

Initial saved views:

```text
Attention
Active
Watching
Dormant
Resolved
Open Questions
Stale
Recently Changed
```

These are query presets, not separate persisted datasets.

### 7.4 Attention view

`Attention` should be rule-driven and explainable.

Candidate reasons:

- high-priority Thread received a new meaningful Event;
- a previously open question may now be answerable;
- a Claim was corrected/superseded;
- a contradictory source appeared;
- a watch condition is overdue;
- a high-priority Thread has become stale;
- a Thread's current-state synthesis is older than its newest material Event.

Each item must expose the reason, e.g.:

```text
Needs attention: 2 new events since last review
Needs attention: claim corrected
Needs attention: open question may be answerable
```

### 7.5 Thread row

A Thread row should expose:

```text
title
status
priority
last meaningful change
recent change summary
open question count
top entities
latest event summary
attention reason if present
```

Optional compact metadata:

```text
event count
source count
tracking since
```

Do not show every available field.

### 7.6 Sorting

Required sort modes:

```text
attention
last meaningful change
priority
title
tracking start
```

### 7.7 Thread inspector

Selecting a Thread without opening full detail shows:

- current-state excerpt;
- latest Event;
- top entities;
- open questions;
- last meaningful change;
- "Open Thread" action;
- "Open source note" action.

---

## 8. Thread Detail

### 8.1 Purpose

Thread Detail is the core reading surface.

The first question it must answer is:

> What is the current state of this Thread now?

The second is:

> How did it get here?

### 8.2 Header

Required:

```text
title
status
priority
tracking_since
last_meaningful_change_at
canonical source action
```

Optional:

```text
watch state
source coverage state
review state
```

### 8.3 Current State

`Current State` is a first-class block at the top.

Requirements:

- concise synthesis;
- provenance marker;
- generated/manual marker if relevant;
- timestamp or revision;
- explicit stale-state warning if newer Events exist than the synthesis.

### 8.4 Thread projection switcher

Inside Thread Detail:

```text
Overview | Timeline | Map | Graph
```

These are projections of the current Thread.

`Overview` contains current state, open questions, latest change, key entities, and recent events.

### 8.5 Open Questions

Open Questions appear above the full historical timeline if unresolved questions exist.

Each question shows:

```text
question
state
opened_at
last_updated_at
related entities/events
```

Answered questions remain accessible but are collapsed by default.

### 8.6 Event timeline

Collapsed event node:

```text
date
event title
one-line summary
claim count
source count
top entities
```

Expanded event node adds:

```text
occurred_at
published_at
first_observed_at
confidence / uncertainty
claims
sources
locations
annotations
canonical refs
```

### 8.7 Claim rendering

Claims must have distinct semantic markers.

Recommended visual semantics:

```text
✓ supported
△ uncertain / analytical
⇄ contested
↺ corrected / superseded
⊘ retracted
```

Color may reinforce state but must not be the only differentiator.

### 8.8 Source rendering

A Source row should show:

```text
publisher / origin
title
published_at
source type
claim relationship
open source action
```

Full source body remains out of the default detail view.

### 8.9 Related Threads

Related Threads should expose typed reasons where available:

```text
shared entity
causal relation
same policy area
follow-on event
contradictory development
manually linked
```

### 8.10 Thread-local Map

The Thread Map visualizes locations connected to the scoped Thread.

Required interactions:

- click location → location inspector;
- filter Thread timeline to location;
- highlight Events at location;
- time-range filter;
- location clustering where needed.

### 8.11 Thread-local Graph

Default graph should be an **ego graph**, not the global corpus graph.

Default nodes:

```text
current Thread
top entities
recent/key Events
related Threads
```

Claims and Sources are hidden by default and can be progressively expanded.

---

## 9. Global Timeline

### 9.1 Purpose

The Timeline answers:

> What happened across the World Historian corpus during this period?

### 9.2 Default grouping

Default:

```text
group by date
```

Additional modes:

```text
group by Thread
group by Entity
```

### 9.3 Required controls

```text
date range
Thread filter
Entity filter
Location filter
Claim state filter
search
group mode
density
```

### 9.4 Timeline row

Each Event row should show:

```text
occurred_at
Thread
Event title
summary
top entities
location if meaningful
claim/source counts
```

### 9.5 Interaction

- selecting an Event opens inspector;
- opening Event navigates to owning Thread Detail at that Event;
- switching to Map preserves date/entity/Thread scope;
- switching to Graph preserves date/entity/Thread scope.

---

## 10. Entities

### 10.1 Entity Directory

Purpose:

> Which people, organizations, countries, technologies, products, or places recur across Threads?

Required fields:

```text
name
kind
Thread count
Event count
last seen
top Threads
```

Required filters:

```text
kind
date range
Thread
search
minimum activity
```

### 10.2 Entity Detail

Header:

```text
name
kind
aliases
last seen
canonical reference if available
```

Sections:

```text
Current involvement
Threads
Event activity
Related entities
Open questions
Map if geographic data exists
Graph
```

### 10.3 Event activity

A compact activity sparkline or line chart may be used here when it improves temporal comprehension.

This is a contextual chart, not a top-level analytics surface.

---

## 11. Map

### 11.1 Purpose

The Map answers:

> Where are historically relevant Events, Entities, and Thread developments occurring?

### 11.2 Map modes

Required modes:

```text
Events
Threads
Entities
```

Default mode: `Events`.

### 11.3 Event Map

Markers represent geocoded Events or Event clusters.

Marker aggregation must avoid creating hundreds of overlapping points.

At low zoom:

```text
country/region clusters
```

At high zoom:

```text
specific normalized locations
```

### 11.4 Thread Map

The Thread map shows spatial structure of a specific Thread.

Examples of valid spatial links:

```text
event occurred at location
entity based in location
route/location explicitly relevant to Thread
```

Do not infer geographic relevance merely because a Source publisher is located somewhere.

### 11.5 Entity Map

Entity Map may show:

- Event locations involving the Entity;
- geographic jurisdictions linked to the Entity;
- location history where supported.

Do not conflate headquarters, nationality, operating region, and Event occurrence.

### 11.6 Map inspector

Clicking a marker or cluster shows:

```text
location name
precision
event count
Thread count
top entities
date range
latest events
```

Actions:

```text
filter Timeline to location
filter Threads to location
open related Thread
switch scoped data to Graph
```

### 11.7 Geospatial integrity

The projector should provide normalized coordinates whenever possible.

The UI should not silently call an external geocoder for arbitrary ambiguous strings.

If future geocoding is added:

- it should be deterministic/cached;
- ambiguity must be represented;
- results must record source and precision;
- the read model remains rebuildable.

---

## 12. Graph

### 12.1 Purpose

The Graph answers:

> How are Threads, Events, Entities, Claims, Sources, Questions, and Locations related?

It is not a generic Markdown backlink graph.

### 12.2 Default graph philosophy

Use progressive disclosure.

Default global Graph should show a bounded subgraph based on current scope.

Default Thread Graph should show an ego graph around the Thread.

Avoid loading all nodes and edges by default.

### 12.3 Node types

Initial node types:

```text
Thread
Event
Entity
Claim
Source
Question
Location
```

### 12.4 Edge types

Initial edge types:

```text
Thread → Event
Thread ↔ Thread
Thread ↔ Entity
Event ↔ Entity
Event → Location
Event → Claim
Claim → Source
Claim ↔ Entity
Question ↔ Thread
Question ↔ Entity
Entity ↔ Entity
```

### 12.5 Graph controls

Required:

```text
node type toggles
edge type toggles
date range
depth
max nodes
layout reset
focus selected node
expand neighbors
hide node
pin node
search node
```

### 12.6 Graph presets

Useful initial presets:

```text
Thread relationships
Entity network
Event–Entity network
Evidence chain
Full scoped graph
```

`Full scoped graph` must still respect a maximum node budget.

### 12.7 Node inspector

Shows:

```text
type
title/name
summary
key metadata
degree within current graph
relation list
canonical source action
```

### 12.8 Edge inspector

Shows:

```text
relation type
direction
confidence if applicable
time validity if applicable
evidence refs
```

### 12.9 Graph safety against hairballs

Requirements:

- hard initial node cap;
- hard edge cap;
- progressive expansion;
- typed filters;
- ego focus;
- clustering optional;
- labels only for important/hovered nodes at dense zoom;
- no automatic "show everything" on load.

Suggested defaults:

```text
initial max nodes: 80
initial max edges: 160
neighbor expansion: 20
maximum interactive nodes before warning: 500
```

These are implementation defaults and may be tuned after profiling.

---

## 13. Contextual Charts

Charts are secondary components used only where a quantitative view helps interpret the selected historical object.

Allowed examples:

### Thread Detail

```text
Event activity over time
Source coverage over time
Claim state over time
```

### Entity Detail

```text
Event activity over time
Thread participation over time
```

### Location Inspector

```text
Event volume over time
```

Avoid charts whose only purpose is vanity counting.

Do not create a top-level dashboard full of:

```text
total Events
total Claims
total Sources
pie charts of statuses
```

unless a concrete historical workflow later demonstrates a need.

---

## 14. Search

### 14.1 Global search

Search should cover at minimum:

```text
Thread titles
Thread current-state text
Event titles/summaries
Entity names/aliases
Open Questions
Claim summaries
Source titles
locations
```

### 14.2 Search result grouping

Results should group by type:

```text
Threads
Events
Entities
Questions
Claims
Sources
```

### 14.3 Search action

Opening a result navigates to the canonical dashboard projection:

- Thread → Thread Detail.
- Event → owning Thread at Event.
- Entity → Entity Detail.
- Question → owning Thread / Entity.
- Claim → owning Event/Thread.
- Source → inspector / canonical source.

---

## 15. Read Model Architecture

### 15.1 Data flow

```text
Canonical World Historian data
        ↓
Deterministic projector
        ↓
Versioned dashboard read model
        ↓
Obsidian ItemView
```

### 15.2 Suggested generated structure

```text
.world-historian/
└── dashboard/
    ├── manifest.json
    ├── threads.json
    ├── entities.json
    ├── locations.json
    ├── graph-index.json
    ├── timeline-index.json
    ├── threads/
    │   └── <thread-id>.json
    ├── entities/
    │   └── <entity-id>.json
    └── locations/
        └── <location-id>.json
```

This path is illustrative. The implementation may use a cache directory outside the Vault if that better avoids Vault churn.

### 15.3 Manifest

Example:

```json
{
  "schema_version": "world-historian-dashboard.v1",
  "generated_at": "2026-09-28T10:00:00+08:00",
  "generator_version": "0.1.0",
  "source_revision": "opaque-source-revision",
  "thread_count": 42,
  "event_count": 618,
  "entity_count": 311,
  "location_count": 94
}
```

### 15.4 Thread list item

Example:

```json
{
  "thread_id": "thread_red_sea_shipping",
  "title": "Red Sea shipping",
  "status": "active",
  "priority": "high",
  "tracking_since": "2024-01-10",
  "last_meaningful_change_at": "2026-09-28T09:42:00+08:00",
  "last_event_at": "2026-09-27T00:00:00Z",
  "current_state_excerpt": "Shipping disruption remains elevated...",
  "open_question_count": 3,
  "event_count": 48,
  "source_count": 122,
  "top_entity_ids": [
    "entity_maersk",
    "entity_houthis",
    "entity_red_sea"
  ],
  "attention": {
    "required": true,
    "reasons": [
      "new_event",
      "current_state_stale"
    ]
  },
  "canonical_ref": {
    "kind": "obsidian_file",
    "path": "2Area/41 新闻及事件/Red Sea shipping.md"
  }
}
```

### 15.5 Thread detail object

Example skeleton:

```json
{
  "thread_id": "thread_red_sea_shipping",
  "title": "Red Sea shipping",
  "status": "active",
  "priority": "high",
  "tracking_since": "2024-01-10",
  "current_state": {
    "text": "Shipping disruption remains elevated...",
    "updated_at": "2026-09-28T09:30:00+08:00",
    "provenance": "historian_generated",
    "stale": false
  },
  "open_questions": [],
  "events": [],
  "entity_ids": [],
  "location_ids": [],
  "related_threads": [],
  "canonical_ref": {}
}
```

### 15.6 Event object

Example:

```json
{
  "event_id": "event_...",
  "thread_ids": ["thread_red_sea_shipping"],
  "title": "Carrier extends Cape routing",
  "summary": "A carrier extended...",
  "time": {
    "occurred_at": "2026-09-27",
    "published_at": "2026-09-27T14:22:00Z",
    "first_observed_at": "2026-09-28T07:15:00+08:00",
    "precision": "day"
  },
  "entity_ids": ["entity_maersk"],
  "location_ids": ["location_red_sea"],
  "claim_ids": ["claim_1", "claim_2"],
  "source_ids": ["source_1", "source_2"]
}
```

### 15.7 Entity object

```json
{
  "entity_id": "entity_nvidia",
  "name": "NVIDIA",
  "kind": "organization",
  "aliases": ["Nvidia"],
  "thread_ids": [],
  "event_ids": [],
  "related_entity_ids": [],
  "open_question_ids": [],
  "last_seen_at": "2026-09-27T00:00:00Z"
}
```

### 15.8 Location object

```json
{
  "location_id": "location_bab_el_mandeb",
  "name": "Bab el-Mandeb",
  "kind": "strait",
  "country_code": null,
  "region": "Red Sea",
  "lat": 12.58,
  "lon": 43.33,
  "geo_precision": "region",
  "event_ids": [],
  "thread_ids": []
}
```

Coordinates above are illustrative schema values; canonical coordinates should come from the projector's normalized geographic source, not from hard-coded UI data.

### 15.9 Graph index

A graph index may be stored as adjacency lists:

```json
{
  "nodes": {
    "thread_red_sea_shipping": {
      "type": "thread",
      "label": "Red Sea shipping"
    }
  },
  "adjacency": {
    "thread_red_sea_shipping": [
      {
        "target": "entity_maersk",
        "type": "thread_involves_entity",
        "weight": 1.0
      }
    ]
  }
}
```

For large corpora, use a more efficient local index rather than loading one huge JSON file.

---

## 16. Projector Requirements

### PRJ-001 — Deterministic output

Given the same canonical input revision and projector version, the generated read model should be stable except for explicitly nondeterministic metadata such as generation timestamp.

### PRJ-002 — Atomic publication

The UI must never observe a half-written read model.

Preferred strategy:

```text
write temp generation
validate
fsync / finalize
atomic rename or manifest pointer switch
```

### PRJ-003 — Incremental rebuild

The projector should support updating only affected:

- Threads;
- Events;
- Entities;
- Locations;
- graph adjacency;
- timeline partitions.

A full rebuild must remain available.

### PRJ-004 — Schema validation

Every generated generation must be validated against the dashboard schema before publication.

### PRJ-005 — Stable IDs

Thread/Event/Entity/Location IDs must remain stable across file renames where the historian model can preserve identity.

File paths must not be used as object IDs.

### PRJ-006 — No canonical mutation

Projector execution never mutates canonical historical source notes solely to make dashboard rendering easier.

---

## 17. Obsidian Plugin Architecture

### 17.1 Host

Use an Obsidian `ItemView`.

Conceptual structure:

```text
WorldHistorianDashboardView extends ItemView
        ↓
mount application root
        ↓
WorldHistorianApp
```

### 17.2 UI framework

Preferred implementation:

```text
ItemView host
+ Svelte application
+ TypeScript
+ Obsidian theme variables
```

The UI should not be implemented as one very large imperative DOM renderer.

### 17.3 Suggested component tree

```text
WorldHistorianApp
├── AppShell
│   ├── TopNav
│   ├── GlobalSearch
│   ├── ScopeBar
│   └── ViewToolbar
├── ThreadsView
│   ├── SavedViewSidebar
│   ├── ThreadList
│   ├── ThreadRow
│   └── ThreadInspector
├── ThreadDetailView
│   ├── ThreadHeader
│   ├── CurrentState
│   ├── OpenQuestions
│   ├── ThreadProjectionTabs
│   ├── EventTimeline
│   ├── ThreadMap
│   └── ThreadGraph
├── TimelineView
├── EntitiesView
├── EntityDetailView
├── MapView
├── GraphView
└── Common
    ├── EventInspector
    ├── ClaimView
    ├── SourceRow
    ├── EntityChip
    ├── LocationChip
    ├── EmptyState
    ├── ErrorState
    └── LoadingState
```

### 17.4 State stores

Suggested stores:

```text
navigationStore
scopeStore
selectionStore
readModelStore
settingsStore
```

Do not mix canonical historian state with ephemeral UI state.

### 17.5 Read-model access

Define a repository/service abstraction:

```ts
interface HistorianReadModel {
  listThreads(query: ThreadQuery): Promise<ThreadListItem[]>;
  getThread(id: string): Promise<ThreadDetail>;
  listEvents(query: EventQuery): Promise<EventSummary[]>;
  listEntities(query: EntityQuery): Promise<EntitySummary[]>;
  getEntity(id: string): Promise<EntityDetail>;
  listLocations(query: LocationQuery): Promise<LocationSummary[]>;
  getGraph(query: GraphQuery): Promise<GraphSlice>;
}
```

The Svelte components should consume this abstraction rather than parse source files directly.

---

## 18. Navigation Model

Internal navigation states:

```text
threads
thread/:threadId
timeline
entities
entity/:entityId
map
graph
```

A selection may add:

```text
event/:eventId
claim/:claimId
location/:locationId
```

Requirements:

- Back/forward navigation works inside the dashboard.
- Search results deep-link to the relevant object.
- View switching preserves global scope.
- Detail navigation preserves previous list scroll position where feasible.

---

## 19. Keyboard Interaction

Initial shortcuts:

```text
/             focus search
j / ↓         next list item
k / ↑         previous list item
Enter         open selected object
Esc           close inspector / return
g then t      Threads
g then l      Timeline
g then e      Entities
g then m      Map
g then g      Graph
r             refresh read model
```

Shortcuts must not override core Obsidian shortcuts without checking conflicts.

---

## 20. Loading, Empty, Stale, and Error States

### Loading

Use skeleton/list placeholders where useful.

Avoid full-view spinner when partial cached data is available.

### Empty

Examples:

```text
No Threads match this scope.
No geocoded Events in this date range.
No relations are available for this graph scope.
```

Offer a one-click filter reset.

### Stale read model

If source data changed after the current projector generation:

```text
Dashboard may be stale
[Refresh]
```

### Invalid generation

If schema validation fails:

- keep the last valid generation;
- show a non-blocking error banner;
- expose diagnostics;
- never render partially invalid data as authoritative.

---

## 21. Performance Requirements

Target corpus assumptions should be configurable, but V1 should remain responsive at approximately:

```text
Threads:        1,000
Events:        100,000
Claims:        500,000
Entities:       50,000
Relations:      1,000,000
```

These are capacity targets, not claims about current corpus size.

### PERF-001

Thread list first render should not require loading all Event/Claim/Source details.

### PERF-002

Thread detail should lazy-load large Event histories where necessary.

### PERF-003

Timeline should be windowed/virtualized for long result sets.

### PERF-004

Graph must fetch/render bounded slices.

### PERF-005

Map must cluster large marker sets.

### PERF-006

Search should use a local index rather than scanning all generated JSON on every keystroke.

### PERF-007

The UI should remain usable while a projector refresh is running against the previous valid generation.

---

## 22. Visual Design Requirements

### 22.1 Theme

Use Obsidian CSS variables and support light/dark modes automatically.

### 22.2 Density

Default density should resemble an issue tracker, research browser, or mail client rather than a marketing dashboard.

### 22.3 Color

Color encodes state, but must not be the only channel.

Examples:

- status;
- claim state;
- priority;
- map cluster intensity.

### 22.4 Typography

Hierarchy:

```text
object title       strongest
summary            normal
metadata           subdued
provenance         subdued / compact
IDs/debug data     hidden by default
```

### 22.5 Motion

Use motion only to preserve spatial context:

- panel open/close;
- graph focus;
- map zoom;
- list/detail transition.

Avoid decorative animation.

---

## 23. Local Analytics / Charts

Charts are allowed only when tied to a concrete question.

A component must state its semantic measure clearly.

Examples:

```text
Event activity — count of Events by week
Source coverage — number of independent Sources by week
Claim states — supported/contested/corrected Claims over time
```

Charts should not mix incompatible measures on one axis.

Default chart time window follows global or object-local scope.

---

## 24. Data Integrity and Provenance

### DI-001

Every Event shown must retain a canonical object reference.

### DI-002

Every Claim shown must expose its state and supporting/contradicting evidence where available.

### DI-003

Generated current-state text must be visually distinguishable from manually authored annotation when provenance differs.

### DI-004

Map coordinates must carry precision.

### DI-005

Graph edges must be typed.

### DI-006

A relation inferred by a model should be distinguishable from a manually asserted or deterministic relation if the canonical historian data models that difference.

### DI-007

Dashboard caches may summarize or truncate for display, but must not replace canonical source content.

---

## 25. Privacy and Security

The dashboard is local-first.

Requirements:

- no external analytics by default;
- no silent upload of historian corpus;
- no silent external geocoding;
- no remote graph processing by default;
- external source links may open only on explicit user action;
- generated cache directories should inherit local filesystem privacy expectations;
- diagnostics must avoid dumping full sensitive source text unless explicitly requested.

---

## 26. Testing Strategy

### Unit tests

Cover:

```text
scope filtering
meaningful-change calculation
saved-view predicates
entity aggregation
location normalization
graph slice construction
schema migration
navigation state
```

### Projector tests

Use fixtures covering:

```text
Thread with no Events
Thread with many Events
multiple timestamp semantics
corrected Claim
contested Claim
answered Open Question
shared Entity across Threads
ambiguous Location
country-level Location
related Threads
missing source
source correction
file rename with stable ID
```

### UI tests

Cover:

```text
Thread filtering
Thread → Event navigation
Timeline → Map scope preservation
Timeline → Graph scope preservation
Entity → Thread navigation
Map marker → Timeline filter
Graph node expansion
stale-generation banner
invalid-generation fallback
keyboard navigation
light/dark theme
```

### Performance tests

At synthetic scale:

```text
1k Threads
100k Events
500k Claims
50k Entities
1m Relations
```

---

## 27. Acceptance Criteria

### AC-001 — Threads Browser

Given a valid read model, the user can:

- open World Historian Dashboard;
- see Threads ordered by an explicit sort;
- search Threads;
- filter by status/priority/entity/date;
- open saved views;
- inspect a Thread;
- open Thread Detail.

### AC-002 — Thread Detail

The user can:

- see Current State;
- see Open Questions;
- browse Event Timeline;
- expand Event → Claim → Source;
- see related Entities;
- see related Threads;
- open canonical source note;
- switch Thread projection among Overview / Timeline / Map / Graph.

### AC-003 — Timeline

The user can:

- browse Events chronologically;
- filter by Thread/Entity/date/location;
- group by date/Thread/Entity;
- open an Event in context;
- switch to Map or Graph without losing compatible scope.

### AC-004 — Entities

The user can:

- search/filter Entity directory;
- open Entity Detail;
- view related Threads;
- view Event activity;
- view related Entities;
- open Entity-scoped Graph;
- open Entity-scoped Map when geographic data exists.

### AC-005 — Map

The user can:

- view scoped Events geographically;
- zoom and cluster;
- select a location;
- inspect related Events/Threads/Entities;
- filter Timeline to selected location;
- preserve date/entity/Thread scope.

### AC-006 — Graph

The user can:

- view a bounded typed graph;
- toggle node/edge types;
- focus a node;
- expand neighbors;
- inspect nodes and edges;
- open canonical object detail;
- preserve current date/Thread/Entity scope.

### AC-007 — Read model

The system can:

- build a complete generation;
- validate it;
- publish atomically;
- rebuild from scratch;
- retain last valid generation on failure;
- expose schema/generator version.

### AC-008 — No second truth store

Deleting the dashboard read model and rebuilding it must recover the same semantic dashboard state from canonical World Historian data, excluding ephemeral UI preferences.

---

## 28. Implementation Phases

### Phase 1 — Foundation

Implement:

```text
dashboard schema
projector
manifest
Thread list/detail read model
Entity index
Timeline index
Obsidian ItemView shell
scope/navigation stores
```

Exit condition:

- Threads Browser works;
- Thread Detail works;
- canonical links work;
- rebuild works.

### Phase 2 — Timeline + Entities

Implement:

```text
global Timeline
Entity Directory
Entity Detail
shared filters
global search
```

Exit condition:

- Thread/Timeline/Entity navigation is coherent;
- scope preservation works.

### Phase 3 — Map

Implement:

```text
location normalization contract
Map projection
marker clustering
location inspector
Timeline ↔ Map interactions
Thread Map
Entity Map
```

Exit condition:

- Map is useful without inventing false geographic precision.

### Phase 4 — Graph

Implement:

```text
graph index
bounded graph query
typed nodes/edges
ego graph
progressive expansion
node/edge inspectors
Thread Graph
Entity Graph
```

Exit condition:

- typical graphs remain interpretable;
- graph does not default to a corpus-wide hairball.

### Phase 5 — Contextual Charts + Polish

Implement selectively:

```text
activity sparkline
source coverage chart
claim-state trend where useful
keyboard shortcuts
responsive layout
performance tuning
diagnostics
```

---

## 29. Explicitly Deferred

The following remain outside this plan unless separately specified:

```text
AI chat
natural-language command interface
automatic historical interpretation from UI
collaborative annotations
cloud sync service
generic Vault graph
generic Vault map
dedicated BI analytics center
automatic external geocoding
full source-text reader
mobile-first optimization
```

---

## 30. Recommended Repository Boundary

If the Obsidian UI and PAP/World Historian live in different repositories, use a clear contract:

```text
World Historian / PAP
        │
        │ produces canonical artifacts
        ↓
dashboard projector
        │
        │ produces versioned read model
        ↓
Obsidian World Historian plugin
```

The plugin must not need to understand World Historian's internal agent prompts, scheduler implementation, or model runtime.

The projector contract is the boundary.

This keeps:

- agent architecture replaceable;
- UI replaceable;
- historical data auditable;
- projections rebuildable.

---

## 31. Final Product Definition

World Historian Dashboard is successful when the user can move fluently between five questions without changing data systems:

1. **Thread:** What is happening with this ongoing historical issue?
2. **Timeline:** What happened, and in what order?
3. **Entity:** Where does this actor/object appear across history?
4. **Map:** Where are these developments occurring?
5. **Graph:** How are these historical objects related?

All five questions must be answered from the same underlying World Historian corpus, under one shared scope and provenance model.

That shared-model constraint is more important than any individual visualization.
