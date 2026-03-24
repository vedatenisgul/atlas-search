from fastapi import APIRouter, Request, BackgroundTasks, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uuid
import time

from storage.nosql import db
from crawler.worker import CrawlerWorker
from search.engine import SearchEngine
from storage.trie import trie_db
from storage.exporter import export_all_to_legacy_format

router = APIRouter()
templates = Jinja2Templates(directory="templates")

workers = {} # job_id -> CrawlerWorker

class CrawlRequest(BaseModel):
    url: str
    max_depth: int = 3
    hit_rate: float = 2.0
    queue_capacity: int = 10000
    max_urls: int = 1000

# UI Page Routes
@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("crawler.html", {"request": request})

@router.get("/crawler", response_class=HTMLResponse)
async def ui_crawler(request: Request):
    return templates.TemplateResponse("crawler.html", {"request": request})

@router.get("/status", response_class=HTMLResponse)
async def ui_status(request: Request):
    return templates.TemplateResponse("status.html", {"request": request})

@router.get("/search", response_class=HTMLResponse)
async def ui_search(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})

# Internal API Routes
@router.post("/api/system/reset")
async def reset_system():
    # Stop all running background workers safely
    for job_id, worker in list(workers.items()):
        worker.stop()
    workers.clear()
    
    # Globally purge key-value persistent storage natively
    db.clear_all()
    
    # Reset structural node maps in Trie memory natively
    trie_db.reset()
    
    import os
    storage_dir = "data/storage"
    if os.path.exists(storage_dir):
        for filename in os.listdir(storage_dir):
            if filename.endswith(".data"):
                try:
                    os.remove(os.path.join(storage_dir, filename))
                except Exception:
                    pass
    
    return {"status": "success", "message": "System wide reset executed natively."}

@router.post("/api/crawler/create")
async def create_crawler(payload: CrawlRequest):
    job_id = str(uuid.uuid4())
    seen = db.data.setdefault("seen_urls", {})
    
    from crawler.worker import normalize_url
    norm_url = normalize_url(payload.url)
    
    import hashlib
    url_hash = hashlib.sha256(norm_url.encode('utf-8')).hexdigest()
    
    worker = CrawlerWorker(
        worker_id=job_id, 
        seed_url=norm_url, 
        max_depth=payload.max_depth,
        queue_capacity=payload.queue_capacity,
        max_urls=payload.max_urls,
        hit_rate=payload.hit_rate
    )
    
    with db.lock:
        if norm_url in db.data.setdefault("seen_urls", {}):
            del db.data["seen_urls"][norm_url]
            
        db.data.setdefault("jobs", {})[job_id] = {
            "job_id": job_id,
            "seed_url": norm_url,
            "state": "Running",
            "created_at": time.time()
        }
            
    db.enqueue(norm_url, 0, job_id, max_capacity=payload.queue_capacity, force=True)
    workers[job_id] = worker
    worker.start()
    
    return {"status": "success", "job_id": job_id, "message": "Crawler initialized"}

@router.get("/api/crawler/status/{job_id}")
async def crawler_status(job_id: str):
    # Retrieve job specific telemetry
    logs = [log for log in db.data.get("crawler_logs", []) if log["job_id"] == job_id]
    
    # Extract job specific queue items
    with db.lock:
        job_queue = [q for q in db.data["crawler_queue"] if q.get("origin_job_id") == job_id]
        
    queue_size = len(job_queue)
    top_live_urls = [q["url"] for q in job_queue[:10]]
    
    w = workers.get(job_id)
    current_processing = w.current_url if w else None
    
    total_visited = 0
    if w:
        total_visited = w.total_visited
    else:
        with db.lock:
            meta = db.data.get("jobs", {}).get(job_id)
            if not meta:
                for h in db.data.get("job_history", []):
                    if h.get("job_id") == job_id:
                        meta = h
                        break
            total_visited = meta.get("visited_count", 0) if meta else 0
    
    res = {
        "job_id": job_id,
        "logs": logs[-50:], 
        "queue_size": queue_size,
        "total_visited": total_visited,
        "top_live_urls": top_live_urls,
        "current_url": current_processing,
        "seed_url": w.seed_url if w else None,
        "is_running": w is not None and w.running and not getattr(w, "paused", False),
        "state": w.job_state if w else "Stopped"
    }

    if w:
        cap = getattr(w, "queue_capacity", 10000)
        hit = getattr(w, "hit_rate", 2.0)
        u = (queue_size / cap) * 100 if cap > 0 else 0
        bp = "Healthy" if u < 75 else "Back-pressure Active" if u < 99 else "Critical (Queue Full)"
        res["queue_utilization"] = round(u, 1)
        res["backpressure_status"] = bp
        res["throttling_status"] = f"Active ({hit} req/s)"
        res["target_hit_rate"] = hit
        
        created = getattr(w, "created_at", time.time())
        end_ref = getattr(w, "ended_at", None) if not w.running else None
        uptime = int((end_ref or time.time()) - created)
        res["uptime_seconds"] = uptime
        res["actual_hit_rate"] = round(w.total_visited / uptime, 2) if uptime > 0 else 0.0
    return res

@router.get("/api/crawler/list")
async def list_crawlers():
    with db.lock:
        jobs_data = db.data.get("jobs", {})
        
    active_jobs = []
    for job_id, meta in list(jobs_data.items()):
        meta = meta.copy()
        w = workers.get(job_id)
        if w:
            state = getattr(w, "job_state", meta["state"])
            if state == "Running" and getattr(w, "paused", False):
                state = "Paused"
            meta["state"] = state
        active_jobs.append(meta)
        
    return {"active_jobs": active_jobs}

@router.get("/api/metrics")
async def global_metrics():
    queue_size = db.queue_size()
    total_visited = len(db.data.get("visited_urls", {}))
    logs = db.data.get("crawler_logs", [])
    
    jobs_list = []
    with db.lock:
        jobs_data = db.data.get("jobs", {})
    for job_id, meta in list(jobs_data.items()):
        m_copy = meta.copy()
        w = workers.get(job_id)
        if w:
            st = getattr(w, "job_state", m_copy.get("state"))
            if st == "Running" and getattr(w, "paused", False):
                st = "Paused"
            m_copy["state"] = st
            if not m_copy.get("seed_url"):
                m_copy["seed_url"] = getattr(w, "seed_url", "")
                
        # Robustly ensure a Seed URL is propagated to the frontend
        if not m_copy.get("seed_url"):
            m_copy["seed_url"] = m_copy.get("origin", "Unable to resolve seed origin")
            
        if w:
            q_size = db.queue_size(job_id=job_id)
            cap = getattr(w, "queue_capacity", 10000)
            hit = getattr(w, "hit_rate", 2.0)
            u = (q_size / cap) * 100 if cap > 0 else 0
            
            if m_copy.get("state") not in ["Completed", "Error", "Stopped"]:
                bp = "Healthy" if u < 75 else "Back-pressure Active" if u < 99 else "Critical (Queue Full)"
                m_copy["queue_utilization"] = round(u, 1)
                m_copy["backpressure_status"] = bp
                m_copy["throttling_status"] = f"Active ({hit} req/s)"
            
        jobs_list.append(m_copy)
        
    active_workers = sum(1 for w in workers.values() if w.running and not getattr(w, "paused", False))
    return {
        "queue_size": queue_size,
        "total_visited": total_visited,
        "active_workers": active_workers,
        "jobs": jobs_list,
        "logs": logs[-20:]
    }

@router.post("/api/crawler/pause/{job_id}")
async def pause_crawler(job_id: str):
    if job_id in workers:
        workers[job_id].paused = True
        return {"status": "paused"}
    raise HTTPException(status_code=404, detail="Job not found")

@router.post("/api/crawler/resume/{job_id}")
async def resume_crawler(job_id: str):
    if job_id in workers:
        workers[job_id].paused = False
        return {"status": "resumed"}
    raise HTTPException(status_code=404, detail="Job not found")

@router.post("/api/crawler/stop/{job_id}")
async def stop_crawler(job_id: str):
    if job_id in workers:
        w = workers[job_id]
        if not hasattr(w, "ended_at"):
            w.ended_at = time.time()
        w.stop()
        w.job_state = "Stopped"
        # Persist in workers dictionary to render "Stopped" natively securely until explicit dismiss occurs!
        return {"status": "stopped"}
    raise HTTPException(status_code=404, detail="Job not found")

@router.post("/api/crawler/export")
async def export_crawler_data():
    """Extracts trie_db metadata and dumps exactly to alphabetical files inside data/storage/"""
    result = export_all_to_legacy_format()
    return result

@router.delete("/api/crawler/delete/{job_id}")
async def delete_crawler(job_id: str):
    if job_id in workers:
        w = workers[job_id]
        w.stop()
        
        history_record = {
            "job_id": job_id,
            "seed_url": w.seed_url,
            "max_depth": w.max_depth,
            "queue_capacity": w.queue_capacity,
            "max_urls": w.max_urls,
            "state": w.job_state if w.job_state in ["Completed", "Error", "Stopped"] else "Closed",
            "visited_count": w.total_visited,
            "created_at": db.data.get("jobs", {}).get(job_id, {}).get("created_at", getattr(w, "created_at", time.time())),
            "ended_at": getattr(w, "ended_at", time.time())
        }
        with db.lock:
            db.data.setdefault("job_history", []).append(history_record)
            if job_id in db.data.get("jobs", {}):
                del db.data["jobs"][job_id]
            
        del workers[job_id]
        
        with db.lock:
            db.data["crawler_queue"] = [q for q in db.data["crawler_queue"] if q.get("origin_job_id") != job_id]
            db.data["crawler_logs"] = [l for l in db.data["crawler_logs"] if l.get("job_id") != job_id]
            if job_id in db.data.get("seen_urls", {}):
                del db.data["seen_urls"][job_id]
        
                return {"status": "deleted"}

@router.get("/api/crawler/history")
async def crawler_history():
    history = []
    with db.lock:
        history.extend(db.data.get("job_history", []))
        jobs_data = db.data.get("jobs", {})
        
    for j_id, meta in list(jobs_data.items()):
        w = workers.get(j_id)
        st = getattr(w, "job_state", meta.get("state")) if w else meta.get("state")
        
        if st in ["Completed", "Error", "Stopped", "Already Indexed"]:
            history.append({
                "job_id": j_id,
                "seed_url": getattr(w, "seed_url", meta.get("seed_url", meta.get("origin", "Unknown Origin"))),
                "max_depth": getattr(w, "max_depth", "N/A") if w else "N/A",
                "queue_capacity": getattr(w, "queue_capacity", "N/A") if w else "N/A",
                "max_urls": getattr(w, "max_urls", "N/A") if w else "N/A",
                "state": st,
                "visited_count": getattr(w, "total_visited", 0) if w else 0,
                "created_at": meta.get("created_at", 0),
                "ended_at": getattr(w, "ended_at", meta.get("ended_at", 0))
            })
            
    history.reverse()
    return {"history": history}

@router.get("/api/search")
async def search_query(query: str, limit: int = 10, offset: int = 0):
    search_data = SearchEngine.query(query, limit=limit, offset=offset)
    
    results = []
    for val in search_data["items"]:
        origin_id = val[1]
        real_url = origin_id
        
        if origin_id in workers:
            real_url = workers[origin_id].seed_url
        else:
            with db.lock:
                for h in db.data.get("job_history", []):
                    if h.get("job_id") == origin_id:
                        real_url = h.get("seed_url")
                        break
                        
        with db.lock:
            meta_info = db.data.get("metadata", {}).get(val[0], {})
            
        title = meta_info.get("title", "")
        snippet = meta_info.get("snippet", "")
                        
        results.append({
            "url": val[0],
            "title": title,
            "snippet": snippet,
            "origin": real_url,
            "depth": val[2],
            "frequency": val[3],
            "relevance_score": val[4] if len(val) > 4 else 0
        })
        
    return {
        "query": query,
        "total_results": search_data["total"],
        "results": results
    }
