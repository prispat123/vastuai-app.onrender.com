# VastuAI Platform 3.1 — Stable Shell and Shared Project Store

This release replaces the fragile `runpy`-based workspace wrapper with one
native Streamlit application.

## What works in v3.1

- One root `.env`
- One data repository
- One SQLite project database
- Native Professional and Builder workspace selection
- Create Project
- Open Project
- Edit Project
- Delete Project
- Persistent project folders
- Stable navigation
- Central session state
- SQLite WAL and busy timeout
- Project health checks
- Versioned schema foundation

## Deliberately deferred

The existing Professional and Builder analysis workflows are not wrapped or
executed in this release. They will be migrated page by page after the shared
shell and project persistence are validated.

This prevents the import collisions, environment duplication, database path
errors and session-state problems seen in the wrapper builds.

## `.env`

Copy `.env.example` to `.env`:

```env
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-5
OPENAI_VISION_MODEL=gpt-4.1-mini
VASTUAI_DATA_DIR=C:/VastuAI_Data
```

The API key is optional for v3.1 because this sprint does not call AI models.

## Run

```powershell
pip install -r requirements.txt
python -m streamlit run app.py
```

Open:

```text
http://localhost:8501
```

## Data location

By default:

```text
C:\VastuAI_Data
├── vastuai_platform.db
├── Projects
├── Uploads
├── SharedCache
├── Reports
├── Exports
└── Logs
```

Future application upgrades will not remove this data folder.

## v3.1.1 navigation fix

The internal `pages` Python package was renamed to `ui_pages`. Streamlit reserves
`pages/` for automatic multipage navigation; keeping internal modules there caused
the left-side Home, Projects and Project Details entries to open modules directly
instead of using the platform session-state router.

v3.1.1 provides one controlled sidebar with working Home, Projects and Project
Details navigation. Project Details remains disabled until a project is opened.


## v3.1.2 navigation behaviour

- Selecting a project immediately sets it as the active project.
- Project Details becomes enabled after selection; Open Project is not required.
- A persistent context bar shows workspace, project, status and platform version.
- The sidebar includes workspace-aware project navigation.
- Professional sections: Overview, Property Details, Layout Review, Vastu Analysis,
  Numerology, Report and Settings.
- Builder sections: Overview, Documents, Apartments, Review Layouts,
  Vastu Analysis, Reports and Settings.


## v3.2 Shared Services

Added one platform-wide implementation of:

- Rotating application logging
- File and project storage
- Shared JSON cache namespaces
- OpenAI client and model configuration
- Runtime and database diagnostics
- Platform Services screen
- Shared cache management

Professional and Builder will consume these services as their proven workflows
are migrated into the native platform.


## v3.3 Native Professional Workspace

The proven VastuAI Professional workflow is now migrated into the unified
platform as a native Python package.

Included:

- Manual property assessment
- Floor-plan upload and visual extraction
- North-orientation review
- Vastu analysis and weighted scoring
- Numerology
- Recommendations and explanations
- Results
- Project-scoped saved portfolio
- Property comparison
- Portfolio dashboard
- PDF, CSV, JSON and bundle exports
- Shared OpenAI client, cache, logging and platform database

Professional analyses are isolated by the selected platform project. Builder
migration remains intentionally deferred to the next phase.


## v3.3.1 navigation state fix

The Professional workspace launch button now updates the sidebar
`project_section` radio through a Streamlit callback. This prevents the
`cannot be modified after the widget ... is instantiated` exception.


## v3.3.2 OpenAI configuration refresh fix

The shared OpenAI service no longer depends on a frozen configuration object
created during module import. It reloads the platform-root `.env` before every
configuration check and before creating the OpenAI client.

The Platform Services screen now displays the exact `.env` path, whether the
file exists, whether the key was detected, and the active model names.


## v3.3.3 Professional navigation and typography fix

- Compare Properties and Dashboard now use a Streamlit callback to update the
  active Professional page.
- The Professional workflow radio no longer mutates related state after widget
  instantiation.
- Overall Score, Vastu, Numerology, confidence and other metric cards use
  smaller labels and values.
- The platform Workspace, Project, Status and Version bar is now a compact
  context strip instead of four oversized metric cards.
- Sidebar and alert typography has also been reduced.


## v3.4.1 Project Intelligence Foundation

The former Builder workspace is now a focused Vastu Project Intelligence
workspace.

Included:

- Vastu-relevant project details only
- Project Intelligence dashboard
- Document Repository
- Categories: Brochure, Master Layout, Floor Plans, Images and Other
- Upload, preview, rename and delete document workflows
- Layout Library
- Tower, flat/layout ID, layout type, floor and drawing
- Analysis status workflow
- Search and filtering
- Project timeline and audit events
- Shared database and project-scoped storage
- No pricing, CRM, sales, customer or availability fields

AI brochure parsing, layout extraction, North detection and room extraction are
deliberately deferred to Sprint 3.4.2.


## v3.4.2 Document Intelligence and Guided Navigation

Navigation:
- Project Details is always enabled after choosing a workspace.
- With no project selected, it routes to Projects with a clear instruction.
- New Project Intelligence projects open directly in Project Details.
- A lifecycle indicator shows Project → Documents → Layouts → Analysis → Reports.

Document intelligence:
- PDF and image page rendering
- Page inventory
- AI page classification
- Floor-plan identification
- North detection with confidence
- Entrance and room-direction extraction
- Extracted JSON persisted under the project
- Manual page classification and North review
- Create Layout from an approved/extracted page
- Project timeline events for rendering and extraction

This sprint does not yet batch-process every page automatically. Batch queues,
duplicate-layout recognition and bulk approval are planned for 3.4.3.


## v3.4.3 Batch Document Intelligence
- Whole-document AI scanning
- Automatic page classification and layout shortlist
- Thumbnail checkbox gallery with Select All/Clear All
- Batch layout creation and duplicate detection
- Review queue for low-confidence or missing-North pages
- Separate Documents and Document Intelligence screens


## v3.4.4 Project Analysis Dashboard

- Batch Vastu analysis of extracted layouts
- Shared Professional Vastu rules reused without numerology
- VSS-1.0 analysis-version marker
- Persisted layout findings, strengths, cautions and recommendations
- Project Vastu score
- Analysis-confidence aggregation
- Tower ranking
- Layout-type ranking
- Apartment/layout ranking
- Common issue frequency
- Recommendation priority areas
- Executive recommendations
- Project Intelligence JSON export
- Layout-level result review
- Analysis snapshots and project timeline events

This release uses the existing validated Professional Vastu engine. The
structured Knowledge Engine will be integrated after the Project Intelligence
workflow is completed.

## v3.5.1 Shared Professional Engine Integration

Every selected Project Intelligence layout now runs through the exact Professional floor-plan extraction, Vastu analysis, recommendation and individual PDF report pipeline. Visual duplicate suppression is removed because different North or entrance orientation requires separate analysis. Project-only logic is limited to batch orchestration and tower/building aggregation.


## v3.5.2 Simplified Document Intelligence

Document Intelligence now does only four things:

1. Extract document pages
2. Display page images
3. Let the user select layout pages
4. Create layout records and continue to Analysis

No North detection, room extraction, Vastu analysis, page classification, or
duplicate detection occurs on the Document Intelligence screen.

The Analysis screen then runs the complete Professional pipeline separately
for every selected layout and shows North, entrance, rooms, directions,
scores, recommendations, and the individual Professional report.

The Streamlit multiselect error is fixed by validating all saved and default
layout IDs against the current options.


## v3.5.3 Result-path safety fix

Fixed a Windows permission error on the Analysis screen. An empty database
result path was previously converted to `Path('.')`, causing the application
to attempt to read the project directory as a JSON file.

The Analysis screen now:

- Treats an empty result path as `None`
- Verifies that the path exists
- Verifies that the path is a regular file
- Handles permission, operating-system and invalid-JSON errors safely
- Shows a clear instruction to rerun analysis instead of crashing


# VastuAI Platform 4.0 — Analysis Complete

This milestone completes the Project Intelligence workflow through individual
layout analysis and individual Professional reports.

Implemented:

1. Create and edit a project
2. Delete a project safely using exact-name confirmation
3. Upload brochures, floor plans and images
4. Extract PDF pages into images
5. Visually select layout pages
6. Create independent layout records
7. Edit tower, flat number, floor and layout type
8. Select one or many layouts for analysis
9. Run the existing Professional engine once for every selected layout
10. Save North detection, entrance, rooms and room directions
11. Save Vastu findings, scoring and recommendations
12. Generate and download an individual Professional PDF report per layout
13. Preserve completed analysis even when manual-review warnings exist

Tower-wise, building-wise and project-level reports are intentionally deferred
to the next milestone.


## v4.2.1 Room-direction derivation fix

- Removed the contradictory requirement for a printed North arrow after the user confirms an image edge as North.
- A confirmed Top/Right/Bottom/Left orientation is now authoritative.
- Confirming North forces a fresh Professional vision extraction rather than reusing a cached Unknown result.
- Visible room directions are derived from the confirmed North orientation.
- Manual-North room confidence filtering is less aggressive, while low-confidence values remain reviewable.


## v4.2.2 Individual report on Analysis & Review

After recalculation and finalisation, the same Analysis & Review page now
shows the complete individual-flat result and provides the downloadable
Professional PDF report.

Displayed sections:
- Overall score
- Vastu score
- Confidence
- Grade
- Confirmed North orientation
- Final reviewed room directions
- Strengths
- Needs attention
- Recommendations
- Download Individual Professional Report


## v4.3.1 Clean Knowledge Engine rebuild

Rebuilt the Knowledge Engine integration from the stable 4.2.2 base.

Architecture:
- `knowledge_engine/` contains repository and evaluation logic.
- `project_intelligence/knowledge_service.py` persists project profiles
  and layout assessments.
- `ui_pages/knowledge_components.py` contains all Knowledge UI rendering.
- `ui_pages/project_intelligence.py` only calls the dedicated helpers.

This prevents Knowledge report code from executing at module import time and
eliminates the `stored is not defined` startup error.

Included:
- 81 structured rules
- Four profiles
- Reusable recommendations
- Explainable individual-flat findings
- Searchable Knowledge Base
- Automatic evaluation after reviewed recalculation


## v4.4.0 Local Knowledge Objects

The Knowledge Engine now uses a dual-source architecture:

- JSON is the editable, version-controlled master.
- SQLite is the validated local runtime database.

New local tables:
- knowledge_meta
- knowledge_profiles
- knowledge_rules
- knowledge_recommendations
- knowledge_rule_recommendations
- knowledge_rule_links
- knowledge_import_runs

Capabilities:
- Automatic first-run Knowledge import
- Manual validate-and-refresh action
- Version and source-hash tracking
- Active/inactive Knowledge Objects
- Recommendation relationships
- Related-rule links
- Import history
- Local backup/export as JSON
- SQLite-backed search and evaluation
- Fully offline rule evaluation

No OpenAI or external API call is required for Knowledge lookup, rule
evaluation, recommendations, dashboard aggregation or local report data.


## v4.4.1 Knowledge database initialization fix

Fixed startup against databases created by earlier VastuAI versions.

- Removed all Knowledge database access during Python/Streamlit module import.
- Knowledge repositories and engines are now created lazily.
- Knowledge status and import operations apply the additive database DDL first.
- Existing projects, documents, layouts, analyses and reports are preserved.
- The JSON Knowledge master is seeded only after the required SQLite tables exist.


## v4.5.0 PDF Reports and Exports

Added deterministic, offline exports based on finalised reviewed results and
local Knowledge Objects.

PDF reports:
- Enhanced individual-flat PDF
- Tower PDF
- Building PDF
- Dashboard PDF

Data exports:
- Excel workbook with project summary, layouts, tower ranking, common issues,
  Knowledge rules and Knowledge findings
- CSV exports for layouts, towers, common issues and Knowledge rules

The original Professional PDF remains available on the Analysis & Review page.
GPT is not required for any report or export in this release.


## v4.5.1 North confirmation and room derivation fix

Fixed the Confirm North and Derive Room Directions action.

Cause:
- The Professional vision prompt contained `__NORTH_INSTRUCTION__`.
- The code attempted to replace the unrelated text `north_instruction`.
- The user-confirmed Top/Right/Bottom/Left orientation was therefore never
  included in the vision request.

Corrections:
- Correctly inject the authoritative manual-North instruction.
- Force a fresh Detailed extraction after confirmation.
- Do not require a printed North arrow after manual confirmation.
- Store manual North confidence as 100%.
- Validate that the selected image is a floor plan.
- Verify that the review-state database row was updated.
- Display the number of derived room directions.
- Show a clear error or manual-review warning instead of appearing to do
  nothing.


## v4.5.2 Report review-schema compatibility fix

Fixed individual, tower, building and dashboard PDF generation against the
current `layout_review_state` schema.

The runtime table uses:
- `derived_json`
- `reviewed_json`

The report query incorrectly requested:
- `derived_directions_json`
- `reviewed_directions_json`

The report layer now inspects the SQLite schema and supports both naming
variants through safe SQL aliases. No project, layout, review, analysis or
Knowledge data is modified.


## v4.5.3 Report schema and lazy-generation fix

Removed all legacy review-column names from the report engine. Analysis,
individual reports, tower reports, building reports, dashboard reports and
exports now use the actual production columns:

- `derived_json`
- `reviewed_json`

The report engine validates the review table before querying.

PDF and Excel files are no longer generated automatically whenever Streamlit
renders a page. The user first clicks Generate, and any generation error is
shown in the UI instead of crashing Analysis or Dashboard & Reports.


## v4.6.0 GPT Intelligence

GPT is an optional explanation and query layer over verified local data.

Available modes:
- Individual-flat explanation
- Why this score?
- Tower executive summary
- Building executive summary
- Project Q&A
- GPT settings
- Generation history and audit trail

Grounding:
- Every request uses a deterministic JSON snapshot built from reviewed
  directions, stored Professional results, project aggregation and local
  Knowledge Objects.
- GPT cannot alter scores, directions, rules or recommendations.
- Missing information must be reported as unavailable.
- Each generation stores the model, source hash, source snapshot, prompt,
  result, status and timestamp.
- OpenAI response storage is disabled with `store=False`.

Offline behaviour:
- Core analysis, Knowledge evaluation, dashboard, PDF reports and exports
  continue working when GPT is disabled or OPENAI_API_KEY is unavailable.

Environment:
- OPENAI_API_KEY is required only for GPT features.
- OPENAI_MODEL defaults to `gpt-5` when not specified.


## v4.6.1 Focused GPT Q&A

GPT Intelligence now contains Q&A, compact Settings, and History only. Structured individual-flat, tower, building and dashboard detail remains in the deterministic report screens. GPT is used for comparisons, explanations, shortlisting and project-wide questions. New installations default to low reasoning effort for faster responses.

Future Numerology is explicitly limited to individual properties and intended users. It does not independently assess towers, buildings or projects, and its score must not be averaged with the Vastu score.


## v4.6.2 Knowledge-Aware GPT

GPT Q&A now receives verified observations, stored Knowledge, deterministically applicable Knowledge, and a room-by-room comparison matrix. Older finalised layouts without Knowledge assessments are backfilled locally without changing their Professional scores. GPT only explains these deterministic inputs.


## v4.7.0 Professional Numerology Foundation

Added a separate, local Professional Numerology domain for individual
properties and intended users.

Inputs:
- intended user name;
- date of birth;
- individual property number or identifier;
- optional property name.

Deterministic calculations:
- Birth Number;
- Life Path Number;
- Property Number.

Local Knowledge:
- versioned Numerology Knowledge Objects;
- number interpretations;
- transparent exact-alignment objects;
- SQLite runtime storage;
- JSON master import and refresh.

Outputs:
- independent Numerology score and grade;
- number interpretations;
- alignment findings;
- individual Numerology PDF.

Boundaries:
- no tower Numerology;
- no building/project Numerology;
- no Vastu/Numerology averaging or direct score comparison;
- no compatibility engine in this release.

The starter rule set is intentionally limited and versioned. It provides the
architecture for continuous expert expansion toward a more exhaustive
Numerology Knowledge Engine.


## v4.7.1 Property Details and Knowledge-ID integration

- Professional Numerology now reads owner, date of birth, property number and property name from the existing saved Property Details record.
- Duplicate Numerology input fields were removed.
- Numerology assessments are attached to an individual saved Professional property analysis.
- A shared individual-assessment snapshot supplies both Vastu and Numerology sections.
- The Professional individual PDF displays Vastu `VK-...` and Numerology `NUM-...` Knowledge IDs.
- Vastu and Numerology scores remain independent and are not averaged or directly compared.
- Project Intelligence tower/building reports are unchanged.


## v4.7.2 Overall Professional Score and Knowledge Coverage

Professional buyer assessments now retain an Overall Professional Score.

When both disciplines are available:
- Professional Vastu weight: 50%
- Professional Numerology weight: 50%

The composite is a transparent mathematical platform index. The underlying
Vastu and Numerology assessments remain visible and independently
interpretable.

Additional changes:
- deterministic executive summary wording;
- Numerology narrative bands always match the calculated grade;
- every directional field evaluated by the Professional Vastu engine has a
  versioned VK Knowledge Object;
- Children's bedroom and Guest bedroom no longer show blank Knowledge IDs;
- extended Knowledge coverage added for Dining, Underground Water, Overhead
  Water and Parking;
- internal Professional Knowledge Coverage dashboard;
- Project Intelligence tower/building workflows remain unchanged.


## v4.7.3 Legacy Numerology Record Compatibility

Fixed existing Professional records showing Numerology as Not assessed.

Historical records stored Numerology only as a 0–10 `score`. Current screens
use `score_100`. Records are now normalized when loaded:

- legacy 6.4/10 becomes 64/100;
- missing grades are reconstructed from deterministic score bands;
- the displayed Overall Professional Score is recalculated with the current
  equal 50% Vastu / 50% Numerology weighting;
- current records remain unchanged;
- source database JSON is not rewritten.

The compatibility adapter is applied at history-load and PDF boundaries.


## v4.7.4 Knowledge Refresh and Report Navigation Fix

- Existing SQLite Knowledge databases are now compared with the bundled JSON
  source hash, Knowledge version and active rule count.
- Older 81-rule databases automatically refresh to the current 130-rule
  library, including Children's Bedroom and Guest Bedroom VK objects.
- The left-side Professional Report section now opens a direct saved-report
  page with PDF, ZIP and data exports.
- Project Intelligence report navigation remains unchanged.


## v4.8.1 Property Decision Profiles

Added:
- immutable Property Decision Profiles (PDPs);
- Decision IDs such as PDP-2026-000001;
- automatic PDP creation after saving a Professional assessment;
- standardized decision card;
- PDP JSON download and audit data;
- Professional AI Consultant for one saved property;
- VK/NUM grounded explanations and consultation history.

This is the foundation for My Shortlist, Portfolio Consultant and Buying Advisor.


## v4.8.2 PDP Automatic Persistence and Backfill

Fixed Decision Profiles remaining empty even though Professional assessments
were automatically saved.

- PDP creation now lives in the Professional persistence service, not the UI.
- New assessments and their PDP are inserted in the same database transaction.
- Reassessing an existing saved property creates a new immutable PDP version.
- Opening Decision Profiles automatically backfills historical saved assessments
  that do not yet have a PDP.
- No separate Save Assessment or Create PDP button is required.


## v4.8.3 Canonical PDP

PDP now uses the same canonical assessment snapshot as Professional reporting, self-enriches older incomplete PDPs, fixes JSON export, and presents an executive decision card with VK/NUM Knowledge IDs, confidence, recommendations and provenance.


## v4.9.0 Buyer Workspace & Shortlist

- First-class Buyer entity.
- Automatic PDP → Buyer linkage.
- Historical PDP Buyer synchronization.
- Cross-project Buyer Workspace.
- Add to Shortlist from PDP.
- Add/remove/reorder shortlist items.
- Optional buyer contact details.
- Shortlist uses immutable PDP values; no assessment is recalculated.

This is the deterministic foundation for Portfolio Consultant and Buying
Advisor.

## v5.8.1 — Render cloud deployment

For cloud/PWA deployment using `app.vastuai.in`, see `RENDER_DEPLOYMENT_GUIDE.md` and `render.yaml`.
