# Atlas Search Engine Architecture (v1.2)

Atlas is a highly parallelized, pure native Python web crawler and real-time search engine. It is driven by a FastAPI orchestrator and explicitly built without heavy external frameworks (no Scrapy, no SQLAlchemy, no Elasticsearch, no Redis). It leverages Python's built-in concurrency modules and custom memory structures to establish a highly capable, zero-dependency environment suitable for enterprise-grade indexing natively.

---

## 1. System Overview & Data Flow

The system orchestrates web crawling, data normalization, and search indexing simultaneously using strict concurrency models.

1. **Crawler Initialization:** A user or script initiates a job via the REST Endpoint (`POST /api/crawler/create`). Physical constraints like `max_urls`, `max_depth`, `hit_rate`, and `queue_capacity` are mapped exclusively to the isolated job memory tree.
2. **Queueing Strategy:** The initial seed URL is ingested into an `RLock()`-protected NoSQL priority queue schema. 
3. **Multi-Threaded Execution:** `CrawlerWorker` instances (structurally extending `threading.Thread`) are immediately spawned. The worker polls target URLs out of the thread-safe queue natively pulling HTML content utilizing custom timeouts and polite `hit_rate` delays.
4. **HTML Parsing & Traversal:** The `AtlasHTMLParser` module structurally intercepts HTML strings using Python's native `html.parser`. The parser explicitly escapes accessibility bloat (ignoring `<nav>`, `<footer>`, `<script>`, `<style>`) natively yielding the raw semantic snippet body tightly constrained to ~200 characters alongside precise page titles.
5. **Inverted Index Extraction:** Extracted word tokens map concurrently into the `AtlasTrie` memory structure, locking the specific character leaf dynamically. URL sources, depth maps, and snippets sync securely into an isolated `metadata` Key-Value store.
6. **Query & Dashboarding:** The Search API (`GET /api/search`) hits the Trie sequentially building the response payload intersecting index matches optimally for millisecond layout rendering.

---

## 2. In-Memory Subsystems (Zero-Dependency)

### `storage/nosql.py` (Key-Value Deduplication & Queuing)
A synchronized active dictionary structure wrapped securely inside `threading.RLock()`. It safely writes state blocks flushable to raw JSON matrices (`atlas_store.json`). 
- **`visited_urls`**: Employs an SHA256 hashed set validating Time-To-Live (TTL) restrictions natively, allowing URLs to be gracefully re-crawled after 1 hour (3600 seconds) politely.
- **`job_queue_counts` (O(1) Evaluation)**: Maintains instantaneous O(1) integer counters ensuring job memory limits are rigidly monitored natively without triggering Global Interpreter Lock (GIL) deadlocks over massive dataset loops.
- **`jobs` & `job_history`**: Maintains the lifecycle of `Running`, `Stopped`, and `Paused` instances, allowing frontend web-clients to strictly manipulate independent background workers safely across API boundaries.

### `storage/trie.py` (Inverted Index Prefix Tree)
A high-speed Trie graph structurally mapping deeply nested characters inherently avoiding flat-file or raw array searches.
- **Node Concept:** A lightweight character traversal map allocating `children` memory pointers terminating safely at an end node natively.
- **Relevance Mapping:** Individual tree layers isolate the specific word strings natively pinning URLs and their specific count frequencies exactly to the node leaf.
- **Concurrency:** Uses a global `RLock()` for inserts and queries ensuring absolute thread-safety from memory-fault corruptions during extreme `CrawlerWorker` ingestion overlap.
- **URL Deduplication Guard:** Before indexing a page, `index_text()` checks if that URL already exists in the Trie for the first word. If it does, re-indexing is skipped entirely — preventing frequency inflation across multiple crawl runs of the same URL.

### `storage/exporter.py` (Legacy ETL Flat-File Persistence)
Adds academic-grade persistence and cross-reboot search capability.
- **Export (`export_all_to_legacy_format`):** Traverses the entire Trie, partitions words alphabetically, and writes space-separated lines (`word url origin_url depth frequency`) into `data/storage/a.data` through `z.data` (plus `other.data`).
- **Import (`import_legacy_data_to_trie`):** On server startup, reads all `.data` files and reconstructs the Trie graph in memory — enabling search to work immediately after reboot.
- **Auto-Trigger:** The exporter fires automatically in the worker's `finally` block when a crawl job completes or is stopped.

---

## 3. Concurrency & Thread Handling Strategy

To prevent internal event loop timeouts, the architecture explicitly separates standard asynchronous web handling from heavily computational tasks.

1. **Uvicorn / FastAPI ASGI Loop**: Manages the API endpoints (`api/routes.py`). All UI polling for live telemetry and history is natively asynchronous.
2. **AnyIO Threadpool Execution**: All database or Trie extraction routes (e.g. `/api/crawler/create` or `/api/metrics`) are explicitly dispatched natively to Starlette's AnyIO background ThreadPoolExecutor. This guarantees that `threading.RLock()` contention inside the NoSQL datastore never starves or halts the main web server loop.
3. **Background Worker Pools**: Crawling threads execute standard blocking network fetches utilizing `urllib` iteratively smoothly. Background crawlers natively bypass SSL faults autonomously, respecting strict network `sys.timeout` thresholds dynamically.

---

## 4. Search Ranking & Turkish Locale

The search module (`search/engine.py` and `search/ranking.py`) executes sub-millisecond document retrievals by intersecting independent paths within the Trie namespace:

1. **Turkish Case-Folding**: Before tokenization, queries pass through a custom `str.translate()` map that correctly handles Turkish-specific characters: `I→ı`, `İ→i`, `Ü→ü`, `Ş→ş`, `Ö→ö`, `Ç→ç`, `Ğ→ğ`. The same map is applied during crawl-time indexing for consistency.
2. **Query Tokenization**: User strings are tokenized and sanitized, scrubbing standard punctuation.
3. **Relevancy Scoring**: Results are ranked using the formula `(term_frequency × 10) + 1000 − (depth × 5)`. Higher frequency and shallower depth produce higher scores.
4. **Contextual Hydration**: Raw ranked URLs are piped into `nosql.py`'s metadata dictionary extracting titles, snippets, and origin job IDs for frontend presentation.

---

## 5. Frontend Telemetry & Startup Lifecycle

The application leverages standard Vanilla JS, HTML, and CSS exclusively mimicking Apple's Human Interaction Guidelines (no Webpack, no React, no NPM).

- **6-Card Adaptive Dashboard**: When viewing a specific job, the status page displays 6 real-time cards — Status, Total Crawled, Pending Queue, Back-pressure Load, Effective Speed, and Active Uptime. In global mode, the job-specific cards (Back-pressure, Speed, Uptime) are automatically hidden.
- **Smooth Uptime Ticker**: Active Uptime interpolates client-side every 1 second between the 2-second API polling cycles. When a job finishes, uptime freezes at `ended_at - created_at`.
- **Effective Speed Snapshot**: `actual_hit_rate` is calculated as `total_visited / uptime`. After job completion, uptime stops growing so the speed value is permanently frozen at its final measurement.
- **Live Event Loops**: Uses JS `setInterval` blocks invoking isolated `/api/metrics` or `/api/crawler/status/{job_id}` endpoints for real-time dashboard updates.

### Startup Lifecycle (`api/main.py` lifespan)

1. **Trie Hydration**: `import_legacy_data_to_trie()` reads all `data/storage/*.data` files and reconstructs the in-memory Trie.
2. **Orphan Cleanup**: Any jobs left in `db.data["jobs"]` from the previous session are automatically moved to `job_history` — the Active Jobs panel starts clean with no zombie entries.
3. **Periodic Sync**: `NoSQLStore` runs a background thread flushing state to `atlas_store.json` every 5 seconds.
