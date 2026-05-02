from fastapi import FastAPI, BackgroundTasks, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import database
import scraper
import models
import time
from typing import Optional

app = FastAPI(title="NEPSE PRO API V1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    database.init_db()
    asyncio.create_task(asyncio.to_thread(scraper.fetch_live_data))
    asyncio.create_task(asyncio.to_thread(scraper.fetch_sector_data))
    asyncio.create_task(background_scraper())

async def background_scraper():
    while True:
        try:
            await asyncio.to_thread(scraper.fetch_live_data)
            if int(time.time()) % 60 < 10:
                await asyncio.to_thread(scraper.fetch_sector_data)
            dashboard_data = {
                "summary": database.get_latest_market_summary(),
                "prices": database.get_live_prices(),
                "sectors": database.get_sectors(),
                "gainers": database.get_top_gainers(),
                "losers": database.get_top_losers()
            }
            await asyncio.to_thread(database.sync_to_firebase, dashboard_data)
        except Exception as e: print(f"Error: {e}")
        await asyncio.sleep(5)

# --- INTERNAL DASHBOARD ENDPOINTS ---
@app.get("/api/dashboard-summary")
async def get_dashboard_summary():
    return {
        "summary": database.get_latest_market_summary(),
        "prices": database.get_live_prices(),
        "sectors": database.get_sectors(),
        "gainers": database.get_top_gainers(),
        "losers": database.get_top_losers()
    }

# --- SYNC & AUTH ---
@app.get("/api/auth/sync")
async def sync_key(email: str):
    data = database.get_key_by_email(email)
    if not data:
        # If no key for this email, generate a default 'all' key
        key = database.generate_api_key(email=email, scope="all")
        return {"api_key": key, "scope": "all"}
    return data

@app.get("/api/auth/generate")
async def generate_key(email: str, scope: str = "all"):
    key = database.generate_api_key(email=email, scope=scope)
    return {"api_key": key, "scope": scope}

# --- PUBLIC V1 API ENDPOINTS (Universal Access) ---

def verify_key(api_key: Optional[str], x_api_key: Optional[str], scope: str):
    key = api_key or x_api_key
    if not key: raise HTTPException(status_code=401, detail="API key required")
    if not database.validate_api_key(key, scope):
        raise HTTPException(status_code=403, detail=f"Invalid key or insufficient scope for: {scope}")
    return True

@app.get("/api/v1/market")
async def v1_market(api_key: Optional[str] = None, x_api_key: Optional[str] = Header(None, alias="X-API-KEY")):
    verify_key(api_key, x_api_key, "market")
    return {
        "status": "success",
        "timestamp": int(time.time()),
        "summary": database.get_latest_market_summary(),
        "prices": database.get_live_prices()
    }

@app.get("/api/v1/sectors")
async def v1_sectors(api_key: Optional[str] = None, x_api_key: Optional[str] = Header(None, alias="X-API-KEY")):
    verify_key(api_key, x_api_key, "sector")
    return {
        "status": "success",
        "timestamp": int(time.time()),
        "sectors": database.get_sectors()
    }

# Legacy support
@app.get("/api/external/market-data")
async def external_market_data(api_key: str):
    if not database.validate_api_key(api_key): raise HTTPException(status_code=403)
    return {"prices": database.get_live_prices()}

@app.get("/api/fundamentals/{symbol}")
async def get_fundamentals(symbol: str):
    data = database.get_fundamentals(symbol)
    if not data: data = await asyncio.to_thread(scraper.fetch_company_fundamentals, symbol)
    return data

@app.get("/api/history/{symbol}")
async def get_history(symbol: str):
    data = database.get_history(symbol)
    if not data: data = await asyncio.to_thread(scraper.fetch_historical_data, symbol)
    return data

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root(): return FileResponse("static/index.html")
