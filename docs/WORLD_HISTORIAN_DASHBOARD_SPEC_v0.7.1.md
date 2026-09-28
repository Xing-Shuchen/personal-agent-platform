# World Historian Dashboard Specification v0.7.1

**Document:** `WORLD_HISTORIAN_DASHBOARD_SPEC_v0.7.1.md`  
**Status:** Implementation specification  
**Version:** 0.7.1  
**Supersedes:** v0.7  
**Date:** 2026-09-28  
**Primary surface:** Obsidian desktop plugin view  
**Product:** PAP / World Historian

---

# 0. Revision Intent

v0.7 established the functional scope and read-model architecture for the World Historian Dashboard:

- Thread Browser
- Thread Detail
- Timeline
- Entities
- Map
- Graph
- contextual charts
- rebuildable projector/read model
- Obsidian `ItemView` application shell

The first implementation demonstrated that those requirements can still produce the wrong product if interpreted primarily as a dense issue tracker.

v0.7.1 therefore changes the product emphasis:

> **The World Historian Dashboard is a visual historical observatory, not a textual inbox with additional visualization tabs.**

This revision does **not** replace the underlying architecture from v0.7. It tightens the presentation, interaction, and visualization requirements so that the implemented product expresses the intended historical model visually.

The main corrections are:

1. Visualization becomes a first-class requirement rather than a secondary enhancement.
2. The home screen becomes an **observatory**, not a full-width Thread list.
3. Selecting a Thread must immediately drive visual projections.
4. Timeline, Map, and Graph are not isolated destinations; they are linked projections of the same scoped corpus.
5. Thread rows/cards must encode change visually rather than forcing the user to read prose to infer state.
6. The right-side inspector becomes a required visual workspace on wide screens.
7. Text density remains high enough for research, but prose is no longer the dominant visual encoding.

---

# 1. Product Definition

The World Historian Dashboard is an interactive visual research surface over World Historian's structured historical corpus.

It must support five fundamental historical questions:

1. **Thread** — What is happening with this ongoing issue?
2. **Timeline** — What happened, and in what order?
3. **Entity** — Where does this actor/object recur across history?
4. **Map** — Where are these developments occurring?
5. **Graph** — How are these historical objects related?

All five questions operate over the same underlying data and scope.

The central semantic model remains:

> **Thread is the narrative unit; Event is the temporal unit; Claim/Source are epistemic units; Entity is a cross-cutting projection; Map and Graph are spatial and relational projections of the same historical corpus.**

The central visual model added by v0.7.1 is:

> **Narrative × Time × Space × Relation must be visible, not merely navigable.**

---

# 2. Visual North Star

The target experience should feel closer to:

- a historical observatory;
- an intelligence analysis console;
- a research-oriented situation room;
- a calm visual knowledge browser;

and less like:

- an issue tracker;
- an email client;
- a Markdown file browser;
- a generic admin dashboard;
- a BI KPI wall;
- a card-heavy productivity app.

The interface should be:

```text
visual-first
information-dense
calm
inspectable
linked
historically grounded
epistemically explicit
```

"Visual-first" does **not** mean decorative.

Every visualization must answer a concrete historical question.

---

# 3. Core Visualization Principle

A user should be able to understand important state changes **before reading the full prose**.

For every primary object or view, the UI should encode at least one of:

- temporal change;
- activity intensity;
- relationship structure;
- geographic distribution;
- uncertainty/confidence;
- unresolved questions;
- provenance/evidence state.

A screen dominated by paragraphs, metadata strings, and entity chips does not satisfy this requirement even if Graph and Map exist elsewhere.

---

# 4. Information Architecture

Top-level navigation remains:

```text
Threads | Timeline | Entities | Map | Graph
```

These views have different roles:

```text
Threads   = narrative observatory
Timeline  = temporal projection
Entities  = cross-thread index
Map       = spatial projection
Graph     = relational projection
```

`Analytics` is explicitly not a top-level destination.

Contextual quantitative charts may appear inside relevant views.

---

# 5. Global Visual Grammar

The dashboard must define a stable visual vocabulary shared across views.

## 5.1 Object shapes / markers

Recommended semantics:

```text
Thread        rounded rectangle / labeled capsule
Event         filled circle on timeline
Entity        circle or compact node
Claim         diamond / claim row marker
Question      hollow circle / question mark marker
Source        document/link marker
Location      map pin / geographic point
```

Exact shapes may evolve, but object types must remain visually distinguishable without relying only on text labels.

## 5.2 Semantic state markers

Recommended visual language:

```text
● active Event
○ unresolved Question
✓ supported Claim
△ uncertain / analytical Claim
⇄ contested Claim
↺ corrected / superseded Claim
⊘ retracted Claim
✎ manual annotation
↗ external Source
```

Color may reinforce meaning but must not be the only encoding.

## 5.3 Priority

Priority should be visible but restrained.

Example:

```text
HIGH      stronger visual weight
NORMAL    neutral
LOW       subdued
```

Do not turn priority into large colored banners.

## 5.4 Activity intensity

Activity should be encoded with:

- sparklines;
- compact event-density bars;
- dot sequences;
- recent-change markers;
- local heat intensity where appropriate.

Do not use raw Event count alone as the primary activity signal.

## 5.5 Uncertainty / precision

Uncertainty should affect rendering where possible:

- approximate dates use fuzzy/interval treatment;
- approximate locations use lighter or larger uncertainty radius;
- uncertain claims use distinct marker;
- inferred relations are visually distinct from manually asserted or deterministic relations.

---

# 6. Application Shell

## 6.1 Required wide-screen composition

On sufficiently wide desktop layouts:

```text
┌───────────────────────────────────────────────────────────────────────┐
│ Top navigation + search + global scope                              │
├───────────────────────────────────────────────────────────────────────┤
│ Observatory strip                                                   │
├──────────────┬─────────────────────────────┬──────────────────────────┤
│ Saved Views  │ Threads in Motion           │ Visual Inspector         │
│ Filters      │ / primary object browser    │ Timeline / Graph / Map   │
│              │                             │ + current state/questions│
└──────────────┴─────────────────────────────┴──────────────────────────┘
```

The right-side visual inspector is required on wide screens.

A full-width list occupying nearly the entire screen is **not** the preferred desktop layout.

## 6.2 Medium width

At medium width:

```text
Sidebar + main browser
```

Visual inspector may become:

- slide-over panel;
- bottom panel;
- explicit detail mode.

## 6.3 Narrow width

At narrow width:

- one primary pane;
- filters become a drawer;
- visual inspector becomes a dedicated page/panel;
- Timeline/Map/Graph remain accessible.

---

# 7. Observatory Strip

The Threads home page begins with a compact observatory strip.

The strip exists to summarize **movement**, not corpus size.

Recommended metrics:

```text
Needs Attention
Events in current window
Threads materially changed
Newly answerable questions
Corrected/contested claims
```

Each metric may include:

- sparkline;
- delta;
- mini activity histogram;
- status breakdown if useful.

Avoid vanity metrics such as:

```text
Total Events ever
Total Sources ever
Total Entities ever
```

unless a concrete workflow later requires them.

## 7.1 Example

```text
Needs Attention     Events · 7d      Changed Threads      Questions
8                   31               6                    27
▁▂▂▅▃▇             ▁▃▅▂▆▇         +2 today             3 answerable
```

The strip must remain compact and secondary to the actual historical corpus.

---

# 8. Threads Home: "Threads in Motion"

The default home list is no longer specified as a dense generic issue tracker list.

It is a **Threads in Motion** view.

Each Thread item must expose change visually.

## 8.1 Required Thread visual encodings

At least one of the following is required per Thread:

- activity sparkline;
- recent Event density;
- last meaningful change marker;
- change magnitude;
- open-question marker;
- Claim correction marker;
- source coverage state;
- event burst marker.

Preferred: combine 2–3 compact encodings.

## 8.2 Thread item layout

Recommended structure:

```text
Thread title                  status / priority

one-line current change summary

activity sparkline            recent-change markers

entities                      6 events · 2 questions
```

The prose summary must be shorter than in v0.7-style dense list rows.

The user should not need to read 2–3 long lines of prose for every Thread.

## 8.3 Example

```text
AI infrastructure financing                 HIGH · ACTIVE

Rates repriced financing assumptions; two open questions affected.

▁▁▂▃▅▃▇      ● ●   ↺   ○○

Oracle · Meta · OpenAI          6 events · 2 questions
```

## 8.4 Thread card/row density

The item should be visually richer but not substantially taller than necessary.

Target:

- approximately 80–130 px on desktop;
- compact mode optional later.

## 8.5 Attention reason

Attention must be visible as an explicit state-change signal.

Examples:

```text
2 NEW EVENTS
CLAIM CORRECTED
QUESTION MAY BE ANSWERABLE
CURRENT STATE STALE
SOURCE CONTRADICTION
```

Avoid burying this only in prose.

---

# 9. Visual Inspector

The Visual Inspector is a major v0.7.1 requirement.

Selecting a Thread in the browser must immediately update the inspector without requiring full navigation.

## 9.1 Inspector sections

Default inspector:

```text
Thread identity
Current State
Projection switcher: Time | Graph | Map
Visual projection canvas
Open Questions
Latest material change
Open Thread
```

## 9.2 Projection switcher

The inspector must support:

```text
Time | Graph | Map
```

This is the most important change from a "visualizations live elsewhere" implementation.

The user should form the mental model:

> One Thread, three visual projections.

## 9.3 Inspector persistence

Changing selected Thread updates the inspector.

Changing projection should preserve selected Thread.

Switching to full Thread Detail should preserve the current projection where possible.

---

# 10. Thread Detail

Thread Detail remains the primary deep-reading surface.

## 10.1 Header

Required:

```text
title
status
priority
tracking_since
last meaningful change
canonical source action
```

## 10.2 Current State

`Current State` must remain prominent, but it should not consume the whole first screen.

Recommended composition:

```text
Current State text        visual change summary
                         / small activity plot
```

## 10.3 Projection tabs

Required:

```text
Overview | Timeline | Map | Graph
```

`Overview` itself should contain visual summaries.

It must not be a pure prose page.

## 10.4 Overview composition

Recommended:

```text
Current State
Recent activity sparkline
Open Questions
Latest 3 Events
Key Entities
Mini Graph / Mini Map where applicable
```

---

# 11. Timeline Visualization

Timeline is a core visualization, not a styled list.

## 11.1 Visual structure

Events must be placed on an explicit temporal rail.

Example:

```text
Sep 28    ●──── Event
          │
Sep 27    ●──── Event
          │
Sep 25    ◉──── major Event
          │
Sep 21    ●──── Event
```

The line/rail should provide clear temporal orientation.

## 11.2 Event significance

If World Historian has a meaningful significance/severity signal, Event nodes may vary by:

- node size;
- emphasis;
- label weight.

Do not infer significance solely from number of Sources.

## 11.3 Event state

Timeline marker shape or decoration may encode:

```text
normal Event
uncertain Event
corrected interpretation
event with unresolved contradiction
major update
```

## 11.4 Zoom / density

Required time scopes:

```text
7d
30d
90d
1y
All
Custom
```

Timeline must adapt density.

For long ranges:

- aggregate low-detail periods;
- cluster events visually;
- reveal individual events on zoom/focus.

## 11.5 Event expansion

Expanded Event includes:

```text
occurred_at
published_at
first_observed_at
summary
Claims
Sources
Entities
Locations
Annotations
```

Collapsed state stays strongly visual.

## 11.6 Global Timeline

Global Timeline may support:

```text
group by date
group by Thread
group by Entity
```

Thread identity should be visually encoded via lane, label, or subtle consistent category marker.

Avoid rainbow colors for dozens of Threads.

---

# 12. Graph Visualization

Graph is a primary analytical projection.

It must not resemble Obsidian's generic backlink graph.

## 12.1 Graph purpose

The Graph answers:

> What is related to what, by which typed relation, under the current historical scope?

## 12.2 Default graph behavior

Default Thread Graph:

```text
ego graph around selected Thread
```

Default Entity Graph:

```text
ego graph around selected Entity
```

Default global Graph:

```text
bounded graph under current scope
```

Never load the entire corpus graph by default.

## 12.3 Node types

Initial:

```text
Thread
Event
Entity
Claim
Source
Question
Location
```

## 12.4 Default visibility

For a Thread Graph:

Visible by default:

```text
Thread
key Entities
key/recent Events
related Threads
```

Hidden initially:

```text
Claims
Sources
Questions
low-value relation edges
```

These are progressively expanded.

## 12.5 Typed edges

Edges must encode relationship type.

Examples:

```text
contains
involves
related_to
supports
contradicts
about
occurs_at
answers
```

Edge labels may appear on:

- selection;
- hover;
- low-density graph;
- edge inspector.

## 12.6 Visual distinction

Node types should differ by at least two channels among:

- shape;
- border;
- size;
- label style.

Do not use color alone.

## 12.7 Layout modes

Initial support:

```text
force-directed
radial ego
hierarchical evidence chain
```

The default should depend on graph preset.

Example:

- Thread relationships → radial/force.
- Evidence chain → hierarchical.
- Entity network → force.

## 12.8 Graph presets

Required:

```text
Thread relationships
Entity network
Event–Entity network
Evidence chain
Full scoped graph
```

## 12.9 Progressive expansion

Required interactions:

```text
focus node
expand neighbors
collapse branch
pin node
hide node
open detail
filter to relation type
```

## 12.10 Hairball constraints

Suggested defaults:

```text
initial max nodes: 80
initial max edges: 160
neighbor expansion: 20
warning threshold: 500 nodes
```

Beyond the threshold, require explicit user expansion.

## 12.11 Graph inspector

Selecting a node or edge opens a contextual inspector.

Node:

```text
type
title
summary
activity
relations
canonical link
```

Edge:

```text
relation type
direction
confidence
time validity
evidence refs
```

---

# 13. Map Visualization

Map is a primary spatial projection.

## 13.1 Purpose

Map answers:

> Where are the historically relevant developments occurring?

## 13.2 Map modes

Required:

```text
Events
Threads
Entities
```

Default:

```text
Events
```

## 13.3 Event Map

Markers represent Event occurrence locations.

At low zoom:

- cluster by region/country;
- show event intensity/count.

At high zoom:

- individual normalized locations;
- event markers;
- local clusters.

## 13.4 Thread Map

A Thread Map should visualize the geography of the selected Thread.

This may include:

- Event occurrence locations;
- relevant routes;
- jurisdictions;
- region transitions;
- geographic concentration.

Do not map Source publisher location unless it is historically relevant.

## 13.5 Entity Map

Entity Map may show:

- Events involving the Entity;
- jurisdictions;
- operational geography;
- geographic history where supported.

It must not conflate:

```text
headquarters
nationality
event location
jurisdiction
operating region
```

## 13.6 Geographic precision

Each location should carry:

```text
exact
city
region
country
approximate
unknown
```

Approximate data must be visually distinguishable.

Examples:

- uncertainty circle;
- lighter marker;
- region polygon instead of point.

## 13.7 Map + Timeline linkage

Selecting a map location should support:

```text
Filter Timeline to this location
Show Events here
Show Threads here
Show Entities here
```

Selecting a Timeline Event should highlight its location on the Map when available.

This is a required linked interaction.

---

# 14. Entities Visualization

Entity Directory should not be only a sortable table/list.

Each Entity item may include:

- activity sparkline;
- Thread participation count;
- recent Event density;
- last-seen marker;
- entity type marker.

## 14.1 Entity Detail

Recommended layout:

```text
Entity identity
Current involvement
Activity timeline
Threads
Related Entities
Map
Graph
Open Questions
```

## 14.2 Entity activity chart

A sparkline or small time-series chart is recommended.

This answers:

> Is this Entity becoming more or less active in the current historical corpus?

---

# 15. Contextual Charts

Charts are allowed as local explanatory devices.

They are not the core dashboard.

## 15.1 Good chart examples

Thread:

```text
Event activity over time
Source coverage over time
Claim-state transitions
```

Entity:

```text
Event activity over time
Thread participation over time
```

Location:

```text
Event volume over time
```

## 15.2 Bad chart examples

Avoid default homepage panels such as:

```text
Total Sources
Total Entities
Status pie chart
Events by category
```

when they do not answer a specific research question.

## 15.3 Chart requirements

Every chart must define:

```text
measure
time/window
aggregation
scope
```

The user should know what is being counted.

---

# 16. Linked Views and Cross-Filtering

This is a hard v0.7.1 requirement.

The dashboard must behave like one analytical system, not five disconnected screens.

## 16.1 Shared scope

Global scope may include:

```json
{
  "date_range": "30d",
  "thread_ids": [],
  "entity_ids": [],
  "location_ids": [],
  "statuses": ["active", "watching"],
  "priorities": [],
  "claim_states": [],
  "search": ""
}
```

## 16.2 Linked selection

Selections should propagate where relevant.

Examples:

```text
Timeline Event selected
→ highlight Map location
→ highlight Graph Event node

Map location selected
→ filter/highlight Timeline Events
→ highlight Graph Location node

Graph Entity selected
→ highlight Entity in Thread context
→ optionally filter Timeline
```

## 16.3 Brushing vs filtering

Distinguish:

```text
highlight = temporary visual emphasis
filter    = changes corpus scope
```

Clicking should not unexpectedly destroy the user's scope.

## 16.4 Scope indicator

The current scope must always be visible.

Example:

```text
30d · Active/Watching · NVIDIA · US export controls
```

Provide one-click:

```text
Clear scope
```

---

# 17. Search as Visual Navigation

Global search covers:

```text
Threads
Events
Entities
Questions
Claims
Sources
Locations
```

Search results should include object type markers.

Opening a search result should navigate to the object in its natural visualization:

```text
Thread   → Thread Detail
Event    → Timeline / owning Thread Event
Entity   → Entity Detail
Location → Map
Claim    → Event/Thread evidence view
Question → owning Thread/Entity
```

Search should not always dump the user into a textual page.

---

# 18. Read Model Additions for Visualization

v0.7.1 requires additional precomputed fields where feasible.

The projector should calculate visual-friendly summaries so the plugin does not derive them ad hoc.

## 18.1 Thread visualization fields

Suggested:

```json
{
  "activity_series": [
    {"date": "2026-09-22", "event_count": 1},
    {"date": "2026-09-23", "event_count": 0}
  ],
  "recent_change_types": [
    "new_event",
    "claim_corrected"
  ],
  "open_question_count": 2,
  "new_event_count_window": 3,
  "last_meaningful_change_at": "...",
  "source_coverage_summary": {
    "independent_source_count": 5,
    "coverage_state": "good"
  }
}
```

## 18.2 Entity visualization fields

Suggested:

```json
{
  "activity_series": [],
  "thread_count": 8,
  "event_count": 37,
  "last_seen_at": "...",
  "top_thread_ids": []
}
```

## 18.3 Timeline summary fields

Suggested:

```json
{
  "significance": "normal",
  "has_open_question": true,
  "has_corrected_claim": false,
  "claim_state_summary": {
    "supported": 3,
    "contested": 1
  }
}
```

## 18.4 Geographic fields

Suggested:

```json
{
  "lat": 12.58,
  "lon": 43.33,
  "geo_precision": "region",
  "geo_source": "canonical_normalizer"
}
```

## 18.5 Graph fields

Suggested:

```json
{
  "node_type": "entity",
  "importance": 0.72,
  "activity": 0.63,
  "relation_count": 14
}
```

`importance` must have a documented derivation if used.

Do not create opaque "AI importance" scores solely for visual sizing.

---

# 19. Read Model Architecture

The v0.7 architecture remains.

```text
Canonical World Historian data
        ↓
Deterministic projector
        ↓
Versioned dashboard read model
        ↓
Obsidian ItemView
```

The dashboard remains a read model, not a second truth store.

## 19.1 Suggested generated structure

```text
.world-historian/
└── dashboard/
    ├── manifest.json
    ├── threads.json
    ├── entities.json
    ├── locations.json
    ├── graph-index.*
    ├── timeline-index.*
    ├── activity-series.*
    ├── threads/
    │   └── <thread-id>.json
    ├── entities/
    │   └── <entity-id>.json
    └── locations/
        └── <location-id>.json
```

Exact storage format may evolve.

For large indexes, SQLite or another bounded local index is acceptable if it better supports:

- graph slices;
- time windows;
- spatial queries;
- search;
- incremental updates.

The rebuildability requirement remains unchanged.

---

# 20. Projector Requirements

Existing v0.7 requirements remain:

```text
deterministic output
atomic publication
incremental rebuild
schema validation
stable IDs
no canonical mutation
```

v0.7.1 adds:

### PRJ-VIS-001

Precompute bounded visual summary data where this materially reduces UI work.

### PRJ-VIS-002

Activity series must have explicit aggregation windows.

### PRJ-VIS-003

Geographic normalization must include precision/provenance.

### PRJ-VIS-004

Graph relations must be typed and queryable by scope.

### PRJ-VIS-005

No opaque visualization score may be generated without documented semantics.

---

# 21. Obsidian UI Architecture

Preferred stack remains:

```text
Obsidian ItemView
+ Svelte
+ TypeScript
+ Obsidian theme variables
```

## 21.1 Revised component tree

```text
WorldHistorianApp
├── AppShell
│   ├── TopNav
│   ├── GlobalSearch
│   ├── ScopeBar
│   └── ObservatoryStrip
├── ThreadsView
│   ├── SavedViewSidebar
│   ├── ThreadsInMotion
│   │   └── ThreadMotionCard
│   └── VisualInspector
│       ├── CurrentStatePreview
│       ├── ProjectionSwitcher
│       ├── MiniTimeline
│       ├── MiniGraph
│       ├── MiniMap
│       └── QuestionPreview
├── ThreadDetailView
│   ├── ThreadHeader
│   ├── CurrentState
│   ├── ActivitySummary
│   ├── ThreadProjectionTabs
│   ├── EventTimeline
│   ├── ThreadMap
│   └── ThreadGraph
├── TimelineView
│   ├── TimelineRail
│   ├── TimelineEvent
│   └── EventInspector
├── EntitiesView
│   ├── EntityDirectory
│   └── EntityActivityCard
├── EntityDetailView
│   ├── EntityActivity
│   ├── EntityMap
│   └── EntityGraph
├── MapView
│   ├── MapCanvas
│   ├── MapLegend
│   └── LocationInspector
├── GraphView
│   ├── GraphCanvas
│   ├── GraphControls
│   └── GraphInspector
└── Common
    ├── Sparkline
    ├── ActivityHistogram
    ├── SemanticBadge
    ├── EntityChip
    ├── ScopePill
    ├── EmptyState
    └── ErrorState
```

---

# 22. Home Screen Acceptance Layout

A conforming wide-screen implementation should resemble this information hierarchy:

```text
WORLD HISTORIAN
Threads   Timeline   Entities   Map   Graph

Search...               Scope: 30d · Active/Watching

Needs Attention     Events · 7d      Changed Threads     Questions
8                   31               6                   27
▁▂▂▅▃▇             ▁▃▅▂▆▇          +2                 3 answerable

Saved Views       Threads in Motion               Visual Inspector
──────────        ─────────────────               ────────────────
Attention         Thread A     ▁▂▃▇              Current State
Active            change summary                 Time | Graph | Map
Watching          ● ●  ↺  ○○                    [visual projection]
Dormant
Resolved          Thread B     ▁▁▅█              Open Questions
                  ...
```

This is a semantic layout requirement, not a pixel-perfect wireframe.

---

# 23. Visual Anti-Patterns

The following implementations should be treated as design failures even if functionally complete.

## 23.1 Full-width textual Thread rows

Failure pattern:

```text
title
long summary sentence...
timestamp · event count · question count
attention text
entity chips
```

repeated across the entire viewport with no meaningful visual encoding.

## 23.2 Visualization only behind top-level tabs

Graph and Map existing only as separate navigation destinations is insufficient.

The selected Thread/Entity must expose local visual projections.

## 23.3 KPI dashboard syndrome

Avoid:

```text
12 large number cards
4 pie charts
3 unrelated bar charts
```

without a historical research question.

## 23.4 Graph hairball

A graph showing hundreds/thousands of nodes immediately is a failure.

## 23.5 Map pin carpet

Hundreds of overlapping markers without clustering or scope is a failure.

## 23.6 Decorative sparkline syndrome

A sparkline must encode a real, defined measure.

Do not add random tiny charts merely to make rows look visual.

## 23.7 Prose hidden inside visualization

Visualizations must complement, not obscure, the historical evidence.

The user must still be able to inspect provenance and canonical content.

---

# 24. Interaction and Motion

Motion should preserve mental context.

Allowed:

- Thread selection animates inspector update subtly;
- Graph focus transitions;
- Map pan/zoom;
- Timeline expansion;
- projection switching.

Avoid:

- decorative counters;
- pulsing nodes;
- continuous graph physics when idle;
- automatic carousel behavior.

Graph physics should settle/freeze after layout stabilizes.

Respect reduced-motion settings.

---

# 25. Accessibility

Visual-first must remain accessible.

Requirements:

- color is never the only state encoding;
- Graph and Map selections have textual inspector equivalents;
- charts expose text summaries;
- keyboard navigation works;
- focus states are clear;
- semantic labels are available to assistive technology;
- map-only information is reproducible in a list/inspector;
- graph-only relations are inspectable as text.

---

# 26. Performance Requirements

Target scale remains:

```text
Threads:        1,000
Events:        100,000
Claims:        500,000
Entities:       50,000
Relations:      1,000,000
```

v0.7.1 adds visualization-specific constraints.

## PERF-VIS-001

Thread Browser must not render large SVG/canvas visualizations per row.

Use compact lightweight sparklines.

## PERF-VIS-002

Mini Graph and Mini Map load only for the selected object.

## PERF-VIS-003

Global Map uses clustering.

## PERF-VIS-004

Global Graph fetches bounded slices.

## PERF-VIS-005

Timeline virtualization must preserve the visual rail and selection state.

## PERF-VIS-006

Switching Time/Graph/Map in the inspector should feel immediate against cached read-model data.

---

# 27. Testing Strategy

Existing schema/projector/navigation tests remain.

v0.7.1 adds visual behavior tests.

## 27.1 Thread Motion Card

Test:

- activity series renders;
- zero activity renders valid baseline;
- corrected Claim marker renders;
- open question marker renders;
- no meaningless NaN/empty sparkline;
- attention reason visible.

## 27.2 Visual Inspector

Test:

- Thread selection updates inspector;
- projection switch preserves Thread;
- open questions update;
- full-detail navigation preserves context.

## 27.3 Linked projections

Test:

```text
Timeline Event → Map highlight
Timeline Event → Graph highlight
Map Location → Timeline filter
Graph Entity → Entity context
```

## 27.4 Timeline

Test:

- explicit temporal rail;
- uncertain time;
- Event expansion;
- clustered long-range behavior.

## 27.5 Graph

Test:

- typed nodes;
- typed edges;
- ego graph default;
- bounded expansion;
- max-node warning;
- inspector content.

## 27.6 Map

Test:

- clustering;
- location precision;
- approximate geography;
- location inspector;
- filter linkage.

---

# 28. Acceptance Criteria v0.7.1

The v0.7 acceptance criteria remain unless overridden below.

## AC-VIS-001 — Home is visibly an observatory

On desktop, the first screen includes:

- observatory strip;
- Threads in Motion;
- visual inspector.

A full-width textual list alone does not pass.

## AC-VIS-002 — Thread rows encode movement visually

Every visible Thread item contains at least one real visual change encoding.

## AC-VIS-003 — Thread selection drives visualization

Selecting a Thread immediately updates a Time/Graph/Map projection in the inspector.

## AC-VIS-004 — Timeline is graphical

Timeline uses explicit temporal structure, not only date-labelled list rows.

## AC-VIS-005 — Map is linked

Map selection can influence Timeline/Thread scope, and Timeline selection can highlight geographic context.

## AC-VIS-006 — Graph is typed and bounded

Graph node/edge types are visually/semantically distinguishable and no corpus-wide hairball is loaded by default.

## AC-VIS-007 — Entity activity is visible

Entity Detail includes at least one temporal activity visualization.

## AC-VIS-008 — Visualizations preserve provenance

Every visual object can be inspected back to its historical object and canonical source reference where applicable.

## AC-VIS-009 — Visualizations have defined semantics

No chart, sparkline, size, intensity, or score may be displayed without a defined underlying measure.

## AC-VIS-010 — Shared scope is preserved

Timeline, Map, and Graph reflect the same active Thread/Entity/date scope unless the user explicitly changes it.

---

# 29. Implementation Sequence v0.7.1

The implementation should prioritize visual correction before adding more backend features.

## Phase 0 — Refactor current Threads screen

Replace:

```text
full-width dense Thread list
```

with:

```text
observatory strip
Threads in Motion
visual inspector
```

Add:

- activity sparkline;
- attention/change markers;
- visual inspector;
- Time/Graph/Map local projection switcher.

This phase should happen first because it corrects the product direction.

## Phase 1 — Visual Timeline

Implement:

- explicit timeline rail;
- Event markers;
- Event significance/state;
- expansion;
- range/density behavior;
- inspector linkage.

## Phase 2 — Thread-local Graph and Map

Before polishing global Graph/Map, make these useful for the selected Thread.

Implement:

```text
Thread ego graph
Thread event map
projection switcher
linked selection
```

## Phase 3 — Global Map and Graph

Implement:

```text
global scoped Map
global scoped Graph
clustering
bounded graph slices
full inspectors
shared scope
```

## Phase 4 — Entity visualizations

Implement:

```text
activity sparkline
Entity timeline
Entity Map
Entity Graph
```

## Phase 5 — Contextual charts and polish

Only after core projections work:

```text
source coverage chart
claim-state trend
activity histograms
responsive refinement
keyboard refinement
visual diagnostics
```

---

# 30. Explicitly Deferred

Still deferred:

```text
AI chat
natural-language command interface
automatic historical interpretation from UI
dedicated BI analytics center
generic Vault graph
generic Vault map
collaborative annotations
cloud-first architecture
decorative 3D globe
always-running animated graph
```

---

# 31. Definition of Done

v0.7.1 is complete when the Dashboard no longer requires the user to read dense text rows to understand what is changing.

A successful implementation should allow the user to:

- glance at the home screen and see which Threads are moving;
- select a Thread and immediately see its temporal, relational, or geographic structure;
- move from Timeline to Map to Graph while preserving scope;
- identify unresolved questions and corrected claims visually;
- use prose for interpretation and evidence, not as the only interface.

The final design principle is:

> **World Historian should render history as structure in motion: narrative in Threads, change in Time, distribution in Space, and causality/association in Relations.**

The dashboard is not merely a browser over historical notes.

It is the visual instrument through which the historian corpus becomes observable.
