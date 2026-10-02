# AgroChain design research

Research run: 2026-10-02. This is the initial reference inventory and design rationale. It does not establish that every listed screen, gated flow or recording was directly inspected. The follow-up [visual-experience research](VISUAL_EXPERIENCE_RESEARCH.md) records access limits, evidence quality, implementation status and the user's clarified goal: a beautiful, engaging visual product rather than a presentation-first interface.

The product has authentication, session, farm CRUD and authorization APIs; its backend does not currently expose shipment or sensor data. Logistics and integrity stories in the redesigned frontend are marked as local demonstration scenarios unless an actual API response is explicitly shown. In the tables below, “Adapted/Yes” records an intended design principle or a related local implementation, not proof that the source interaction was fully observed or reproduced. The follow-up report takes precedence for source-verification and completion status.

## Three concepts considered

### A — Field Signal Atlas (selected synthesis)

- **Mood:** cartographic, tactile and calm; mineral paper, graphite ink, crop green, frost blue and amber.
- **Layout:** broad, asymmetrical spatial canvas with a small navigation dock, a contextual right inspector and a narrow data rail. Farm Atlas and Trace Command Center use different map compositions.
- **Type and density:** humanist sans for reading, serif display numerals for chapter labels, monospaced strings for UUIDs and hashes. Low-to-medium density, with detail disclosed on selection.
- **Visualization and motion:** schematic route SVG, coordinate field, telemetry trace, event chain; route packets and inspector transitions explain state changes.
- **Strengths:** makes place, movement, telemetry and provenance legible together; translates well to the available farm-coordinate API.
- **Risks:** map-like layouts can imply geographic precision that fixture data does not have. All schematic/demo geometry is labeled; actual farm coordinates are shown as values and plotted from API records.
- **Desktop:** wide map canvas and persistent inspector.
- **Mobile:** stacked route strip, full-width map, bottom-sheet inspector and bottom navigation.

### B — Chain Forensics Console

- **Mood:** restrained graphite instrument panel with cool white type and signal amber; deliberately not neon/cyberpunk.
- **Layout:** three-column workspace: request/event stream, central topology graph, evidence inspector. Navigation is a compact command palette and utility rail.
- **Type and density:** mono-forward, compact and high-density; tabular data and request traces dominate.
- **Visualization and motion:** node graph, hash links, request packets, diff playback and explicit stop points.
- **Strengths:** best for technical explanation of hashing, RBAC and RLS; precise and demonstrable.
- **Risks:** weak farm identity and warmth; high density can overwhelm growers and mobile users.
- **Desktop:** persistent three-column trace workstation.
- **Mobile:** one event at a time with collapsible trace layers; graph becomes a vertical sequence.

### C — Field Notes / Harvest Ledger

- **Mood:** editorial field journal with warm paper, large serif numerals, crop annotations and restrained map marks.
- **Layout:** chapter-led scroll canvas, full-bleed section headers, side notes, selected detail panels that unfold in place.
- **Type and density:** expressive serif headlines and generous whitespace; data appears in annotated notes rather than dashboards.
- **Visualization and motion:** scroll-linked chapter progression, crop-to-route narrative, low-motion reveals.
- **Strengths:** distinctive and accessible for a guided presentation; strong narrative framing for traceability.
- **Risks:** less efficient for repeated CRUD and role checks; scroll choreography can obscure task location.
- **Desktop:** wide editorial spreads with anchored margin notes.
- **Mobile:** single-column story with sticky chapter index and no horizontal canvas.

### Selected direction

Use **Field Signal Atlas** as the base, with **Chain Forensics Console** evidence behavior for Integrity and Security. This preserves an approachable agricultural identity while making the route, real farm records, access path and cryptographic mechanics visually inspectable. The app uses Vietnamese copy, labels local fixtures, and keeps actual API results distinct from explanatory diagrams.

## Visual references

| # | Source and page | What is interesting | AgroChain feature | Technique; expected performance cost | Accessibility risk | Use |
|---:|---|---|---|---|---|---|
| 1 | [Mobbin — Mobile Map screens](https://mobbin.com/explore/mobile/screens/map) | Map and bottom-sheet patterns keep location context while revealing details. | Farm Atlas and mobile route inspection. | SVG markers + CSS sheet; low. | Pin color or hover-only details; provide labels and focus selection. | Adapted |
| 2 | [Mobbin — Web Inventory Management Dashboard](https://mobbin.com/explore/web/screens/inventory-management-dashboard) | Operational lists expose reordering, editing and creation as recognizable actions. | Farm list/create/edit actions. | Semantic table/list and API-backed form; low. | Dense columns and tiny controls; reflow to rows/cards with full labels. | Adapted |
| 3 | [SaaSFrame — Atlas Dashboard](https://www.saasframe.io/examples/atlas-dashboard) | Dashboard hierarchy moves from location/context to actionable evidence. | Trace Command Center composition. | CSS grid around one spatial canvas; low. | Unlabeled visual summaries; pair each with readable text. | Adapted |
| 4 | [SaaSFrame — June People Table](https://www.saasframe.io/examples/june-dashboard) | Compact navigation and clear row hierarchy make dense lists scannable. | Farm Atlas List view. | Native table, sticky header; low. | Sticky/scrolling table on phones; provide a separate compact layout. | Adapted |
| 5 | [SaaSFrame — Unkey Roles](https://www.saasframe.io/examples/unkey-roles) | Role, permissions and assignment metadata are explicit in the same scan line. | RBAC matrix. | Semantic role-permission table; low. | State encoded by checkmarks only; pair icon, text and color. | Adapted |
| 6 | [SaaSFrame — Forest Admin Security](https://www.saasframe.io/examples/forest-admin-security-page) | Security controls are grouped around the object they protect. | Security X-Ray and session context. | Layered request diagram + access summary; low. | Technical language; add plain-language layer captions. | Adapted |
| 7 | [SaaSFrame — Plausible Analytics](https://www.saasframe.io/examples/plausible-analytics-dashboard) | A restrained chart-first surface gives one dataset room to explain itself. | Cold Chain Journey temperature trace. | Lightweight inline SVG; low. | Chart values may be visually inaccessible; supply a text summary and stage values. | Adapted |
| 8 | [SaaSFrame — Visitors Analytics Dashboard](https://www.saasframe.io/examples/visitors-analytics-dashboard) | Small trends work when labels and the main number stay dominant. | Session/API status and farm area summaries. | CSS number and SVG sparkline; low. | Avoid color-only trend; include direction words. | Selectively |
| 9 | [SaaSFrame — Frame Dashboard](https://www.saasframe.io/examples/frame-dashboard) | A focused header creates a clear start point without a large KPI wall. | Page headers and current shipment context. | Typography and spacing, no runtime effect; none. | Small secondary labels; maintain minimum text size. | Adapted |
| 10 | [Refero — The Outsiders Dashboard](https://refero.design/screens/28e8e3b2-e7f9-4e5c-828c-97ecdd21c456) | Events, stats and timeline coexist without flattening chronology. | Cold Chain Journey event timeline. | SVG path plus event list; low. | Timeline can require dragging; keyboard-operable range input and buttons. | Adapted |
| 11 | [Refero — Touch Time Dashboard](https://refero.design/screens/0295f7b3-4687-4b50-914c-4ff257365f72) | Location, time and summary data can share one context. | Stage/time inspector. | Selected stage panel; low. | Date/time abbreviations; spell out units and timezone. | Adapted |
| 12 | [Page Flows — Crisp login flow](https://pageflows.com/post/desktop-web/logging-in/crisp/) | Login flow should confirm progress and then land users in product context. | Secure Gateway verification sequence. | Immediate submit state and session success; low. | Keep real form visible and labels persistent; no animation-only completion. | Adapted |
| 13 | [Page Flows — Dashboard design patterns](https://pageflows.com/resources/dashboard-design/) | Good dashboards connect every summary to an action or detail. | Command Center and Atlas navigation. | Context links from visual stages; low. | Avoid hidden hover actions; mirror with buttons/focus. | Adapted |
| 14 | [Page Flows — DoorDash browsing flow](https://pageflows.com/ios/products/door-dash/) | Mobile task flows use compact progressive steps. | Mobile guided demo and stage selection. | Bottom navigation + stacked stages; low. | Preserve back/exit and visible current step. | Adapted |
| 15 | [Dribbble — Maestro logistics command center](https://dribbble.com/shots/27024330-Maestro-Smart-Logistics-Command-Center-Dashboard) | Map-led logistics views can make fleet and shipment status the visual anchor. | Trace Command Center. | Original route SVG and stage controls; low. | Concept art can overstate live-data freshness; label scenario fixtures. | Adapted |
| 16 | [Dribbble — FreightFlow logistics dashboard](https://dribbble.com/shots/27147396-FreightFlow-Modern-Logistics-Dashboard-UI) | Structured calm can carry dense logistics data without neon. | Cold-chain journey and route metadata. | Asymmetric grid and status typography; low. | Status needs text and shape as well as hue. | Adapted |
| 17 | [Dribbble — Supply Chain Command Center](https://dribbble.com/shots/26521082-Supply-Chain-Command-Center-Dashboard) | A command-center framing emphasizes operational sequence over generic totals. | Product journey path. | Node-link diagram; low. | Graph needs a linear text alternative. | Adapted |
| 18 | [Dribbble — Cold Chain Monitoring Dashboard](https://dribbble.com/shots/22720546-Cold-Chain-monitoring-Dashboard-UI) | Temperature, humidity and location belong on the same timeline. | Telemetry inspector. | SVG chart and explicit units; low. | Distinguish temperature excursion from hash integrity in words. | Adapted |
| 19 | [Behance — Tanee Greenhouse Monitoring](https://www.behance.net/gallery/243573473/Tanee-Greenhouse-Monitoring-Dashboard) | Farm mapping and environmental measures give a believable smart-farm story. | Farm Atlas and local demo telemetry. | Coordinate map and isolated metric detail; low. | Demo/fixture state must not read as live telemetry. | Adapted |
| 20 | [Behance — Cold Chain Management Dashboard](https://www.behance.net/gallery/185185679/Cold-Chain-Management-Dashboard-UI-Design) | Cold-chain monitoring pairs operational status with shipment context. | Cold Chain Journey. | Stage-linked mini-chart; low. | Avoid tiny dense readings; provide selected-event detail. | Adapted |
| 21 | [Behance — Smart Farm Management Dashboard case study](https://www.behance.net/gallery/220010457/Smart-Farm-Management-Dashboard-Case-Study) | Field-level view is a useful counterpoint to organization-level metrics. | Farm Atlas identity and compare mode. | Plot scale and UUID inspector; low. | Plot symbols must be focusable and named. | Adapted |
| 22 | [Awwwards — Interactive Map / Tavalo](https://www.awwwards.com/inspiration/interactive-map-tavalo) | Map navigation is a meaningful primary interaction when it carries content. | Selectable farm and route nodes. | SVG landmarks and keyboard buttons; low. | Map-only interaction excludes keyboard users; add list controls. | Adapted |
| 23 | [Awwwards — Kaze interactive map navigation](https://www.awwwards.com/inspiration/desktop-kaze) | Spatial navigation can guide attention with progressive reveals. | Guided product path. | One-time path highlight; low. | Motion preference and static active path fallback. | Selectively |
| 24 | [Awwwards — Sample Data GIF interface](https://www.awwwards.com/inspiration/sample-data-gif-creations-google-data-gif-maker) | A small animated demonstration can explain a transformation better than prose. | Hash recomputation and request flow. | Finite SVG/CSS sequence; low. | Never rely on motion alone; retain before/after text. | Adapted |
| 25 | [SiteInspire — Web & Interactive Design](https://www.siteinspire.com/websites/category/web-and-interactive-design) | Unusual layout proportions help a technical product feel authored. | Editorial page composition. | CSS grid asymmetry; none. | Avoid clipped/overlapping content at zoom and narrow widths. | Adapted |
| 26 | [SiteInspire — Technology websites](https://www.siteinspire.com/websites/category/technology) | Technical identity can use strong typography and whitespace without dashboard clichés. | Gateway and forensic headers. | Type scale and canvas composition; none. | Maintain contrast and avoid thin display text. | Adapted |
| 27 | [Land-book — Datagrid template](https://land-book.com/websites/72233-datagrid-webflow-html-website-template) | Type-led, grid-aware layouts give data products a strong outer frame. | Atlas and Forensics structural rhythm. | CSS grid; none. | Grid must collapse rather than force sideways scroll. | Adapted |
| 28 | [Land-book — ClearFlow](https://land-book.com/websites/91332-clearflow) | Quiet light/dark contrast and generous margins can feel precise. | Light theme surfaces. | Color tokens and spacing; none. | Check both themes for contrast. | Adapted |
| 29 | [Godly — User Interface Gallery](https://godly.website/website/644-user-interface-gallery) | Curated UI pages are strongest when one visual idea dominates. | One dominant visualization per view. | Large canvas, limited supporting surfaces; low. | Do not bury controls inside expressive decoration. | Adapted |
| 30 | [Lapa Ninja — Isometric websites inspiration](https://medium.com/lapa-ninja/lapa-inspiration-3-isometric-websites-design-234d1704fb05) | Isometric scenes tell place stories but can sacrifice precision. | Route map illustration only. | Flat SVG alternative instead of 3D; low. | Do not suggest geographic accuracy; label schematic. | Selectively |

## Interaction and motion references

| # | Reference and observed interaction | Domain meaning, trigger and information value | Implementation technique; cost | Accessibility risk and fallback | Use |
|---:|---|---|---|---|---|
| 1 | [Mobbin Map screens](https://mobbin.com/explore/mobile/screens/map) — map selection with detail sheet | Selecting a pin reveals that farm's GPS and UUID without losing spatial context. | Button markers + CSS inspector; low. | Hover-only labels; use focus and `aria-pressed` selection. | Yes |
| 2 | [60fps — Family dynamic tray expand/contract](https://60fps.design/shots/family-dynamic-tray-expand-contract-interaction) — sheet morph | Opening a stage inspector keeps the selected object visually continuous. | CSS transform/opacity panel transition, 240 ms; low. | Motion discomfort; static panel open/close under reduced motion. | Yes, simplified |
| 3 | [60fps — Recollect Pro sheet-to-page](https://60fps.design/shots/recollect-pro-bottom-sheet-to-page-interaction) — bottom sheet to page | Mobile detail expands into a focused reading surface. | CSS layout state change, no FLIP dependency; medium. | Gesture-only expansion; click/tap button and Escape provide same action. | Yes, mobile sheet |
| 4 | [60fps — Amie drag-to-calendar morph](https://60fps.design/shots/amie-drag-to-calendar-morph) — drag morph | Drag expresses movement between contexts. | Native range input, no custom physics; low. | Drag can exclude keyboard/touch precision; provide increment buttons and keyboard arrows. | Selectively |
| 5 | [60fps — Notion AI sheet action trail](https://60fps.design/shots/notion-ai-sheet-intro-action-trail-transition) — progressive reveal | A short sequence makes a multi-step task legible. | Staggered opacity/translate with finite sequence; low. | Stagger delays reading; reduced-motion shows all steps immediately. | Yes, login/guided demo |
| 6 | [Codrops — Animated Map Path for Interactive Storytelling](https://tympanus.net/codrops/2015/12/16/animated-map-path-for-interactive-storytelling/) — route draw | Route progression is a path with a start and destination. | SVG `stroke-dashoffset`; low. | Animation may hide route; static route is always present, active segment also labeled. | Yes |
| 7 | [Codrops — Animate SVG shapes on scroll](https://tympanus.net/codrops/2022/06/08/how-to-animate-svg-shapes-on-scroll/) — path reveal | A single line can focus an evidence chain. | CSS/SVG path reveal, finite; low. | Scroll-bound progress may be confusing; controls set state directly. | Selectively |
| 8 | [MDN — `stroke-dashoffset`](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/stroke-dashoffset) — SVG line drawing | Dashed offset can reveal a route/verification link. | CSS keyframe or attribute transition; low. | Motion-only status; add textual `Verified`, `Mismatch`, or `Blocked` labels. | Yes |
| 9 | [Magic UI — Animated Beam](https://magicui.design/docs/components/animated-beam) — traveling beam | A packet moving through the chain communicates the direction of propagation. | Small SVG path + finite keyframe; low. | Continuous shimmer distracts; play once after an explicit action, stop under reduced motion. | Yes, adapted |
| 10 | [Aceternity — Tracing Beam](https://ui.aceternity.com/components/tracing-beam) — evidence beam | Links can show which downstream event loses ancestry. | SVG path class toggled on tamper; low. | Red-only failure state; text and broken-link icon accompany color. | Yes, adapted |
| 11 | [Aceternity — Card Spotlight](https://ui.aceternity.com/components/card-spotlight) — pointer spotlight | Pointer-local highlight can expose a selected region. | CSS radial gradient on one selected inspector only; medium. | Pointer-only and contrast drift; no spotlight on touch/focus, detail remains visible. | No (too decorative) |
| 12 | [Design Spells](https://designspells.com/) — curated interaction details | Small transitions are strongest when a state change has meaning. | Reuse timing tokens and transform/opacity; low. | Excess delight can slow task flow; no timing gates on API actions. | Yes, principle only |
| 13 | [Motion Primitives — Disclosure](https://motion-primitives.com/docs/disclosure) — progressive disclosure | Expanding canonical JSON reveals evidence on demand. | Native `<details>` or CSS height-free opacity; low. | Hidden details can be undiscoverable; summary says what opens. | Yes, native disclosure |
| 14 | [React Bits](https://reactbits.dev/) — animated React component catalog | Useful source of interaction shapes, but not a reason to add a framework. | Rebuild needed subset with SVG/CSS; low. | Decorative animation can distract; reduced-motion variant. | Selectively |
| 15 | [Animata — animated menu list](https://animata.design/docs/list/menu-animation) — staged list entrance | A current tab can open with an orderly brief reveal. | CSS transition on existing elements; low. | Delayed focus/reading; no staged entrance on reduced motion. | Selectively |
| 16 | [Uiverse — animated buttons](https://uiverse.io/ui/animated-buttons) — press/hover feedback | A tap should confirm instantly. | CSS `transform` and color, 120–160 ms; low. | Hover-only response; explicit `:focus-visible` and active state. | Yes, restrained |
| 17 | [60fps UI animation glossary](https://60fps.design/glossary) — scrub, slider, map, sheet patterns | A scrubber should control a specific moment, not decorate a chart. | Native range input updates selected event; low. | Custom slider semantics; retain native input and numeric labels. | Yes |
| 18 | [Motion for React — gestures](https://motion.dev/docs/react-gestures) — hover/tap/pan/focus | Gesture patterns should have input equivalents. | Native pointer/keyboard handlers; no new motion package. | Gestures can be undiscoverable; always provide button/range alternatives. | Principle only |
| 19 | [Page Flows — Crisp login](https://pageflows.com/post/desktop-web/logging-in/crisp/) — login step feedback | The user should know whether submit is in progress and where the session lands. | Button state plus visible sequence; API response remains immediate. | Live region can over-announce; one polite status string. | Yes |
| 20 | [60fps — UI animation inspiration](https://60fps.design/) — state-feedback archive | Status changes should answer “what happened?” in one beat. | 120–180 ms state transition and text update; low. | Motion/color alone; readable label and reduced-motion fallback. | Yes |

## Effects planned for the implementation

| Effect | Domain meaning and trigger | Information value | Cost / performance | Accessibility fallback |
|---|---|---|---|---|
| SVG route path and one-shot packet | User selects a stage or starts the guided trace; packet means data moved to that step in the demo scenario. | Connects farm, transport and warehouse stages. | Low; SVG `animateMotion` on one small circle, keyed to the selected stage. | Static full route with ordered stage buttons and text; packet is removed under reduced motion. |
| GPS lock ring | User focuses or selects an API-backed farm marker; the ring means the stored coordinate is selected for inspection. | Connects the map marker to the exact coordinate/UUID inspector. | Low; one finite CSS ring on the selected marker. | Marker label and coordinate readout remain; reduced-motion preference removes the ring. |
| Coordinate crosshair | User selects a real farm marker or list row. | Makes the stored latitude/longitude visible and tied to stable UUID. | Low; CSS translate/opacity. | Focusable named marker and coordinate text. |
| Time scrubber | User presses arrows, clicks a stage or moves native range control. | Synchronizes stage, telemetry point, event and hash selection. | Low; one SVG cursor moves. | Native keyboard-operable range plus stage buttons. |
| Thermal trace | User selects a journey moment or toggles a local excursion scenario. | Separates physical temperature from cryptographic integrity. | Low; fixed demo-sized SVG. | Table of readings and explicit excursion status. |
| Hash verification beam | User starts/replays verification or edits the local demo field. | Shows the changed digest and downstream broken ancestry. | Low; one finite CSS/SVG sequence. | Before/after diff and statuses remain visible with no animation. |
| Request X-Ray packet | User presses “Test GET /api/v1/farms/”. | Shows the actual request result: permitted request passes RLS; 403 stops at RBAC. | Low; React state follows the API response; no artificial wait. | Ordered semantic layer list and exact HTTP status. |
| Farm inspector panel | User selects a map marker/row or opens create/edit. | Shows or edits one API-backed farm while retaining atlas context. | Low-medium; transform/opacity; no layout measurement. | Focus moves to panel heading/first field; Escape closes; fields remain in DOM order. |
| Guided spotlight | User starts a chapter or presses next. | Directs attention to a domain object and explains the sequence. | Medium; fixed overlay and chapter state; no blur filter. | Dialog focus trap, Escape exit, visible captions and static chapter index. |
| Command palette | User clicks the control or presses Ctrl/Cmd+K. | Offers direct access to the six views and major actions. | Low; small modal, no continuous effect. | Native dialog semantics, arrow/key selection and Escape. |

## Research synthesis and constraints

- Product references were useful for scan order, tables, login and permission matrices; map and supply-chain concepts came from Mobbin, Refero, Behance, Dribbble and Awwwards.
- Visual galleries were treated as references for composition and visual hierarchy, not as production UI kits. No complete design or component library is copied.
- The React project uses Vite, TypeScript and custom CSS. Tailwind/shadcn code examples are reverse-engineered into local CSS/SVG; no UI framework or animation dependency is added.
- Every map, route, telemetry and hash-chain fixture is named as a demonstration scenario. Actual farms and authorization results come from existing API calls.
