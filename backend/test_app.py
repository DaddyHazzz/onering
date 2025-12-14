from fastapi import FastAPI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/test")
def test():
    logger.info("Test endpoint called")
    return {"ok": True}

@app.on_event("startup")
async def startup():
    logger.info("App started")

@app.on_event("shutdown")
async def shutdown():
    logger.info("App shutting down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=9000)
