from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from core.config import settings
from core.logging import configure_logging

from api import auth, posts

configure_logging()

app = FastAPI(title="OneRing - Backend (dev)")

# CORS (adjust origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])

@app.get("/healthz")
def health():
    return {"status": "ok", "env": settings.ENV}

@app.on_event("startup")
async def on_startup():
    logging.getLogger("onering").info("Starting OneRing backend...")

@app.on_event("shutdown")
async def on_shutdown():
    logging.getLogger("onering").info("Stopping OneRing backend...")
