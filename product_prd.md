# Product Requirements Document (PRD)
**Project:** Atlas Web Crawler & Real-Time Search Engine
**Core Stack:** Python (FastAPI), HTML/CSS/JS (Vanilla), NoSQL Key-Value Store
**Design System:** Apple-Style Minimalist UI

## 1. Executive Summary
The objective of this project is to build a highly concurrent web crawler and a real-time search engine named **Atlas**. The backend will be powered by **FastAPI**. The frontend must feature an **Apple-style aesthetic** (clean, minimalist, glassmorphism) and be structured into **separate pages connected by a persistent top Navigation Bar (Navbar)**. 

The system must be built for production-level scale from day one, incorporating NoSQL databases, Trie data structures for search, dynamic worker scaling, and comprehensive observability metrics.

---

## 2. Technical Architecture & Constraints
* **Backend:** FastAPI (Python 3.7+) for high performance and native async support.
* **Frontend:** HTML5, CSS3, Vanilla JavaScript (No Single Page Applications - must use separate HTML pages linked by a Navbar).
* **Storage (NoSQL required):** Any suitable NoSQL key-value store (e.g., MongoDB, Redis, or local equivalents) must be used instead of raw flat files. 
* **Concurrency & Workers:** The system must support dynamic horizontal scaling of jobs/workers.
* **System Design (Phase 2 Directive):** The exact directory and file structure is purposefully omitted from this PRD. As part of **Phase 2**, the AI system architect must map out the optimal system architecture, database schemas, and repository structure before writing any core logic.

---

## 3. User Interface (UI) & User Experience (UX)

### 3.1. Design Language (Apple-Style)
The UI must feel premium, fluid, and native:
* **Typography:** Sleek sans-serif fonts (e.g., system-ui, SF Pro).
* **Colors & Surfaces:** Ample whitespace, soft grays, translucent materials (Glassmorphism), and subtle drop shadows.
* **Components:** Rounded corners, smooth hover transitions, and minimalist inputs.
* **Centralized Configs:** UI elements should reflect centralized configuration rules (e.g., rate limit warnings).

### 3.2. Page Layouts (Navbar Linked)
1. **Crawler Dashboard:** Form card to initialize a crawler.
2. **Status & Observability:** Real-time telemetry for both Crawlers and Search infrastructure.
3. **Search Interface:** Google-like search bar with paginated results.

---

## 4. Core Capabilities

### 4.1. The Indexer (Multi-Threaded Crawler)
* **Dynamic Thread Spawning:** The crawler must not be limited to a static thread pool. It should dynamically spawn new worker threads based on queue limits, tightly constrained by real-time CPU and Memory usage limits.
* **Distributed Logic:** Worker logic must be structured so it can theoretically run across distributed nodes/regions for security and compliance.
* **Politeness & Revisiting (TTL):** Implement a time-to-live (TTL) mechanism. A visited page is not blocked permanently; it can be revisited after a configurable delay (e.g., 5 seconds) to capture updates.
* **Security:** Hide all crawling activity signatures from the outside world (e.g., rotating User-Agents, headers).
* **Data Storage:** Crawler data (queue, logs) and the `visited_urls` registry must be stored in the NoSQL DB. Prepare the `visited_urls` data structure to be exportable via a daily batch process (e.g., to BigQuery) for future analytics.

### 4.2. Search Engine & Data Structures
* **Trie Data Structure (Critical):** Words must be stored using a Trie (Prefix Tree) system. 
  * The Trie must be scalable, sharding based on chunks of words or selected roots.
  * Must utilize memory caching aggressively for the most relevant words, associated URLs, origin, and depth information to ensure maximum read speed.
* **Advanced Relevancy:** Search optimization must include:
  * PageRank-style heuristics.
  * Word relevance weighting and sentence context understanding.
  * **Fuzzy matching** to handle misspellings and typos gracefully.
* **Availability:** Search must consume the crawler's output seamlessly with graceful failures. It must prioritize speed and availability above all.

---

## 5. Monitoring, Observability & Security

The system must include dedicated tracking for three separate domains:

### 5.1. Search Metrics
* **Success Metrics:** Daily/Monthly Active Users (DAU/MAU), Click-Through Rate (CTR), Bounce Ratio.
* **Performance Metrics:** Availability uptime, Speed/TTFB (Time to deliver the initial results screen to the user).

### 5.2. Crawler Metrics
* **Success Metrics:** Daily/Hourly number of unique pages crawled, delay/latency in capturing page updates, queue depth of pages needing to be crawled.
* **Infrastructure Metrics:** Number of active worker nodes/threads currently in use.

### 5.3. Admin & Security Overrides
* **Admin Metrics:** Cost calculation for system parts, total nodes active, and NoSQL database size.
* **Security & Throttling:** Strict rate limiting and throttling for search usages to avoid DDoS attacks and block malicious users.
* **Compliance:** All data storage schemas must be designed with data compliance and privacy standards in mind.

---

## 6. API Endpoints (FastAPI Contract)
* `POST /crawler/create`: Initializes crawler with dynamic constraints.
* `GET /metrics`: Aggregated observability metrics for both search and crawler.
* `POST /crawler/pause/{id}`, `POST /crawler/resume/{id}`, `POST /crawler/stop/{id}`: State controls.
* `GET /search`: Query parameters (`query`, `limit`, `offset`, fuzzy flags).
