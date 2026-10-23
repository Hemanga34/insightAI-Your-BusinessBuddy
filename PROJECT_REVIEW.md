# SentifyAI review and InsightAI extension plan

Reviewed 23 October 2026. Source: /Users/hemangadas/Downloads/SentifyAI-main-final. Source files were inspected without changing the supplied project or calling its services. README claims were treated as documentation, not verified deployment facts or instructions.

## Assessment

SentifyAI is a stock/news analysis prototype with a document-retrieval experiment. It provides a useful market intelligence foundation, but the core of a business finance assistant remains to be implemented. Its fixed sequence of model calls is not an agent that selects tools, tracks tasks, or schedules actions.

## Existing implementation

| Area | Evidence and scope | Extension decision |
| --- | --- | --- |
| Frontend | Svelte 5/SvelteKit, Tailwind, company search, TradingView, news cards, stock metrics, summaries, chat, PDF download | Retain UI framework and reusable components; introduce business dashboard and documents area |
| Backend | Flask REST endpoints and Socket.IO events in backend/app.py | Retain and modularize; a framework rewrite is not necessary |
| News | NewsAPI company query; article title, URL, image and publication time retained | Reuse retrieval adapter and metadata; add India/sector relevance, deduplication and provenance |
| Sentiment | FinBERT classifies headlines with labels and confidence | Optional enrichment; sentiment does not establish business impact |
| Stock analysis | yfinance basic/advanced metrics, bullish/bearish summaries and PDF export | Keep as optional market module, separate from private business accounting |
| Document retrieval | PyPDFLoader script chunks a fixed local PDF into a fixed Vultr collection; Flask chat queries that collection | Refactor into authenticated, tenant-scoped ingestion and retrieval; no user upload workflow exists |
| PHP chatbot | Laravel source fragments provide a second chat route; frontend links to localhost:8000 | Prefer one Python chat backend to reduce duplicate maintenance |

The README describes S&P 500 selection. No company seed or SQL schema is supplied, so the actual remote database contents were not established. The code is not configured as an India-only product.

## Concrete problems to fix first

1. chatbot-app/app/Services/VultrService.php contains a literal API credential and disables TLS certificate verification. Treat the credential as exposed, revoke/rotate it before reuse, remove it from source, and restore verification. No credential was tested.
2. backend/app.py exposes routes and socket handlers without authentication or business scoping. CORS/socket origins are unrestricted. A shared hardcoded RAG collection cannot isolate business documents.
3. The empty-query branch in /api/chatbot passes a Python set to jsonify, which will fail instead of returning the intended validation response. The endpoint also assumes a JSON object and does not validate query type or length.
4. fundamental_llama_vultr.py assumes holder, insider and estimate data exists and has specific dataframe columns. Missing upstream values can crash the summary.
5. fundamental_basic.py labels trailingPE as “P/E Industry Ratio”; the implementation does not compute an industry ratio.
6. External HTTP calls lack explicit timeouts and consistent error handling; raw upstream errors can become chat replies. Model configuration is duplicated and hardcoded.
7. A news failure returns from the entire fetch_data flow before independent stock data is fetched. Later failures also prevent remaining sections from completing.
8. The frontend hardcodes localhost backend URLs. Socket results have no request ID, so switching companies during a running request can mix results. Several error paths leave loading placeholders displayed indefinitely.
9. FinBERT is loaded during every successful news request rather than cached or initialized once.
10. The PDF export uses a caller-controlled symbol in a shared output filename. Validate symbols and use isolated temporary files with cleanup to avoid path and concurrency problems.
11. PDF ingestion scripts run operations at module top level, use one fixed collection and reference a PDF absent from the supplied folder. They do not preserve useful per-page/source metadata in the uploaded payload.
12. No SQL schema/migrations, automated tests, backend environment template, or complete runnable Laravel project is supplied. README infrastructure claims cannot be confirmed from this source snapshot.

## Missing product capabilities

- Business onboarding, industry profile, user accounts, roles and isolated business workspaces.
- Upload/storage and document lifecycle for PDF, XLSX/XLS, CSV, DOCX, JPG and PNG. File support must be explicit rather than promising all formats.
- OCR for scans; spreadsheet table extraction; validation, deduplication, processing status and user correction of ambiguous entries.
- Structured transactions, invoices, balances and accounting periods with links to source pages/sheets/rows.
- Deterministic financial calculations, reconciliation and coverage checks. Missing data should produce an explanation, not invented metrics.
- Cash-flow views, revenue/expense analysis, receivables aging and startup burn/runway where sufficient data exists.
- INR/lakh/crore display, Indian financial years, IST scheduling and Indian document conventions. GST-related extraction should preserve the source and support review; compliance rules require separate current validation.
- Business-specific Indian news relevance, cited impact explanations and scheduled digests. Existing headline summaries do not establish full-article facts or measured market trends.
- Calendar authorization, availability lookup, meeting proposals, explicit execution permissions and cancellation/update flows.
- Durable task state, background processing, retries, idempotency, audit records and permission checks around every agent tool.
- Protection against uploaded documents or retrieved news being treated as operational instructions; external content is data, never authority to execute a task.

## Recommended architecture

Extend the existing SvelteKit frontend and Flask backend. Split backend responsibilities into documents, financial calculations, news, chat/tools and integrations. Add a relational business database and migrations; object storage for originals; business-scoped retrieval for document text; and a worker queue for OCR, ingestion and scheduled jobs.

Keep structured financial records separate from the text retrieval index. Calculate metrics in code over validated records; use the language model to explain the results and select permitted tools. Every answer involving a number should identify its period, underlying source and any data limitations. Every external action should have a durable action record and enforce the business’s execution permissions.

## Build order and acceptance criteria

### 1. Establish a reliable baseline

Consolidate chat in Python, remove exposed credentials, configure providers through environment variables, restore TLS verification, fix known defects, add schema/seed data and setup instructions, and run frontend checks plus mocked API tests. Confirm provider/model availability separately before connecting live accounts.

Acceptance: a new developer can start the project from documented configuration; invalid requests return predictable errors; one upstream failure does not leave unrelated sections unusable.

### 2. Build business workspaces and document ingestion

Add authentication and business isolation before private uploads. Start with CSV/XLSX and text PDFs, then scanned PDFs/images and DOCX/XLS. Add limits, safe storage, extraction status, source metadata and a review screen.

Acceptance: upload a sample bank statement and invoices, inspect extracted entries, correct uncertain fields, and prove another business cannot access their records or retrieval results.

### 3. Deliver the first financial insight workflow

Normalize reviewed data and compute cash movement, expenses and overdue invoices. Add revenue and runway only when the required accounting information is available. Provide cited chat answers and reconciled dashboard totals.

Acceptance: selected metrics match hand-checked fixtures; every cited number opens its source; duplicate invoices are not counted twice; cash receipts are not automatically classified as revenue.

### 4. Adapt the market intelligence module

Capture business sector and exposure, scope retrieval to relevant Indian developments, deduplicate sources and explain possible business effects with publication dates and links. Add time-series inputs when claiming measured trends.

Acceptance: a business can see why each article matters and distinguish sourced facts from inferred impact.

### 5. Add meeting execution

Connect one calendar provider with OAuth, query availability, draft title/attendees/time/agenda, apply permissions, execute once, and save the event identifier for updates/cancellation. Use IST consistently.

Acceptance: the user can review and authorize a meeting; retries do not create duplicate invitations; expired authorization produces a recoverable error.

### 6. Add recurring agent workflows

Only after individual tools work reliably, add persisted schedules and tasks such as a weekly financial review, significant-news alerts and meeting preparation.

## Validation performed

All 15 Python files passed AST syntax parsing. Frontend dependencies are not installed in the supplied folder, backend/.env is absent, and no SQL files or test files were found. PHP is unavailable on the current PATH. The application was not started, frontend build/type checks were not run, and live database, inference, news and stock services were not tested. No runtime or deployment readiness is claimed.
