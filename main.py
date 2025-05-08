from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional
import asyncio

# Import your scraper modules
from scrapers import sydney_tools

app = FastAPI()

class ScrapeResult(BaseModel):
    title: Optional[str]
    price: Optional[str]
    images: Optional[list]
    url: Optional[str]

@app.get("/")
def home():
    return {"message": "Scraper API is running!"}

@app.get("/scrape/sydney", response_model=ScrapeResult)
async def scrape_sydney(sku: str = Query(...)):
    return await asyncio.to_thread(sydney_tools.scrape_model, sku)
