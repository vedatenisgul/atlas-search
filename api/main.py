from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api.routes import router
from contextlib import asynccontextmanager
from storage.exporter import import_legacy_data_to_trie

@asynccontextmanager
async def lifespan(app: FastAPI):
    import_legacy_data_to_trie()
    
    # Auto-close any orphaned jobs from previous sessions
    from storage.nosql import db
    import time as _time
    with db.lock:
        orphaned_jobs = list(db.data.get("jobs", {}).items())
        for job_id, meta in orphaned_jobs:
            history_record = {
                "job_id": job_id,
                "seed_url": meta.get("seed_url", ""),
                "max_depth": meta.get("max_depth", 3),
                "queue_capacity": meta.get("queue_capacity", 10000),
                "max_urls": meta.get("max_urls", 1000),
                "state": meta.get("state", "Closed"),
                "visited_count": meta.get("visited_count", 0),
                "created_at": meta.get("created_at", _time.time()),
                "ended_at": meta.get("ended_at", _time.time())
            }
            db.data.setdefault("job_history", []).append(history_record)
            del db.data["jobs"][job_id]
    db.save()
    
    yield

app = FastAPI(title="Atlas Web Crawler & Search", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(router)
