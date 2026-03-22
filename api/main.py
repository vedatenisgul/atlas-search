from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api.routes import router

app = FastAPI(title="Atlas Web Crawler & Search")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(router)
