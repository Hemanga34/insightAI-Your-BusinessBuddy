# Architecture decisions

## Application shape

Use one FastAPI application and Celery worker processes. SvelteKit serves the web app and forwards `/api` requests to FastAPI. This keeps the browser on one origin and puts document processing in workers when Celery mode is enabled. The existing SentifyAI Flask algorithms can move into small service modules later; its credential-bearing PHP source is not copied.

Frontend stays with the SvelteKit/TypeScript foundation already used in SentifyAI. This initial screen uses scoped CSS rather than adding a component system or Tailwind dependency before it is needed.

## Data and access

PostgreSQL is the deployment database; SQLite is available for local development and tests. Alembic owns schema changes. Every document lookup uses the authenticated user's business ID, never a client-selected business ID. In this milestone, registration creates one user and one business; team memberships and role management are future work. Database RLS is not yet configured: isolation is currently enforced in application queries and tested.

Original files use generated object keys under business IDs, not caller-controlled filesystem paths. Local storage supports development; an S3 adapter supports private buckets. Configure cloud IAM/bucket access and credentials through the environment, never source. Storage deletion exists internally for upload rollback; user-facing deletion/retention is future work.

Text is extracted with page/sheet/row/paragraph locations and displayed as escaped text. It is not an accounting ledger. Spreadsheets preserve formula expressions without executing them; neither extraction nor the browser treats them as commands. Upload names/extensions and basic signatures are checked, but these checks do not replace malware scanning or sandboxed parsing.

## Processing

Documents move from queued → processing → extracted, needs_attention or failed. Extracted means text is ready to inspect, not that financial values are validated. Celery mode dispatches by document ID; the worker fetches storage metadata from the database. Retry is explicit. Worker hard crashes can leave a document marked processing; durable recovery/outbox handling is still needed before production.

Limits: 20 MB upload, 100 MB expanded Office archive, 200 PDF pages, 5,000 spreadsheet/CSV rows and 300,000 extracted characters. Over-limit extraction returns an attention state rather than silently displaying a partial result as complete. PNG/JPEG and scan-only pages return an OCR requirement; no OCR engine or AI extraction service is invoked.

## Future financial and agent layer

1. Introduce reviewed structured records using SQL numeric columns and Python Decimal. Store currency, accounting periods and source references. Distinguish cash receipts from revenue and transfers from income.
2. Compute metrics with deterministic tools, reconcile balances and record data coverage. The model explains results and never supplies authoritative totals from text alone.
3. Add business-scoped chunks and pgvector after structured review works. The PostgreSQL Docker image includes pgvector, but extension activation, tables and indexing are deferred until retrieval is implemented.
4. Add a hosted-model adapter selected using an Indian document evaluation set. Model choice, processing region and costs remain open decisions.
5. Add LangGraph persisted workflows for tool selection and review/resume. Celery executes background work; LangGraph manages an agent's state. No graph, model calls or chat endpoint are implemented in this milestone.
6. Reintroduce SentifyAI news logic behind a service adapter, with timeouts, source attribution and Indian sector relevance. Google Calendar OAuth and idempotent approved actions follow.

Retrieved articles and uploaded documents are untrusted data. Future model prompts and tool permissions must ensure they cannot authorize actions, alter business scope or override the owner's instructions.
