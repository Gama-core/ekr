# /elastic-search/main.py
import logging
from fastapi import FastAPI
from app.endpoints import router as elasticsearch_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Elasticsearch Service",
    description="This service provides search and indexing capabilities by consuming data from the Database API.",
    version="1.0.0"
)

# MODIFIED: Removed the tags=["Elasticsearch"] argument
app.include_router(
    elasticsearch_router,
    prefix="/es"
)

@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "ok", "message": "Welcome to the Elasticsearch Service"}