from fastapi import FastAPI, BackgroundTasks, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import database
import scraper
import models
import time

app = FastAPI(title="NEPSE Live Market API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
async def startup_event():
    database.init_db()
    # Force an immediate scrape of ALL data
    asyncio.create_task(asyncio.to_thread(scraper.fetch_live_data))
    asyncio.create_task(asyncio.to_thread(scraper.fetch_sector_data))
    asyncio.create_task(background_scraper())

async def background_scraper():
    while True:
        try:
            await asyncio.to_thread(scraper.fetch_live_data)
            # Refresh sectors every 1 minute for better responsiveness
            if int(time.time()) % 60 < 10:
                await asyncio.to_thread(scraper.fetch_sector_data)
            
            # Aggregate and sync to Firebase for real-time frontend
            dashboard_data = {
                "summary": database.get_latest_market_summary(),
                "prices": database.get_live_prices(),
                "sectors": database.get_sectors(),
                "gainers": database.get_top_gainers(),
                "losers": database.get_top_losers()
            }
            await asyncio.to_thread(database.sync_to_firebase, dashboard_data)
        except Exception as e:
            print(f"Error fetching data: {e}")
        await asyncio.sleep(5)  # Refresh every 5 seconds

# API Endpoints
@app.get("/api/market-summary", response_model=models.MarketSummary)
async def get_market_summary():
    data = database.get_latest_market_summary()
    if not data:
        raise HTTPException(status_code=404, detail="Market summary not found")
    return data

@app.get("/api/live-prices", response_model=list[models.CompanyPrice])
async def get_live_prices():
    return database.get_live_prices()

@app.get("/api/top-gainers", response_model=list[models.GainerLoser])
async def get_top_gainers():
    return database.get_top_gainers()

@app.get("/api/top-losers", response_model=list[models.GainerLoser])
async def get_top_losers():
    return database.get_top_losers()

@app.get("/api/dashboard-summary")
async def get_dashboard_summary():
    summary = database.get_latest_market_summary()
    prices = database.get_live_prices()
    sectors = database.get_sectors()
    gainers = database.get_top_gainers()
    losers = database.get_top_losers()
    
    return {
        "summary": summary,
        "prices": prices,
        "sectors": sectors,
        "gainers": gainers,
        "losers": losers
    }

@app.get("/api/company/{symbol}", response_model=models.CompanyPrice)
async def get_company(symbol: str):
    data = database.get_company_by_symbol(symbol)
    if not data:
        raise HTTPException(status_code=404, detail="Company not found")
    return data

@app.get("/api/generate-key")
async def generate_key():
    key = database.generate_api_key()
    return {"api_key": key}

@app.get("/api/external/market-data")
async def external_market_data(
    api_key: str = None, 
    x_api_key: str = Header(None, alias="X-API-KEY"),
    authorization: str = Header(None)
):
    # Try query param first, then X-API-KEY, then Bearer token
    final_key = api_key
    if not final_key and x_api_key:
        final_key = x_api_key
    if not final_key and authorization and authorization.startswith("Bearer "):
        final_key = authorization.split(" ")[1]
        
    if not final_key:
        raise HTTPException(status_code=401, detail="API key is required")
        
    is_valid = database.validate_api_key(final_key)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid API key")
        
    summary = database.get_market_summary()
    prices = database.get_live_prices()
    sectors = database.get_sectors()
    
    return {
        "status": "success",
        "timestamp": int(time.time()),
        "market_summary": summary,
        "sectors": sectors,
        "live_prices": prices
    }

@app.get("/api/fundamentals/{symbol}")
async def get_fundamentals(symbol: str):
    data = database.get_fundamentals(symbol)
    if not data:
        # Try to fetch it live if not in DB
        data = await asyncio.to_thread(scraper.fetch_company_fundamentals, symbol)
    if not data:
        # Return a skeleton so the frontend modal still opens
        from datetime import datetime
        data = {
            "symbol": symbol.upper(),
            "name": symbol.upper(),
            "sector": "N/A",
            "listed_date": "N/A",
            "market_cap": "N/A",
            "paid_up_capital": "N/A",
            "high_low_52": "N/A",
            "eps_ttm": 0.0,
            "eps_reported": "N/A",
            "pe_ratio": 0.0,
            "pb_ratio": 0.0,
            "roe": "N/A",
            "book_value": 0.0,
            "share_registrar": "N/A",
            "website": "N/A",
            "email": "N/A",
            "contact": "N/A",
            "head_office": "N/A",
            "mgmt_head": "N/A",
            "promoter_holding": "N/A",
            "public_holding": "N/A",
            "business_model": "Data unavailable for this symbol.",
            "management_quality": "N/A",
            "industry_strength": "N/A",
            "future_growth": "N/A",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    return data

@app.get("/api/external/market-data")
def get_external_market_data(api_key: str):
    if not database.validate_api_key(api_key):
        return {"error": "Invalid API Key"}
    
    summary = database.get_latest_market_summary()
    prices = database.get_live_prices()
    return {
        "summary": summary,
        "prices": prices[:20]
    }

@app.get("/api/history/{symbol}")
async def get_history(symbol: str):
    try:
        data = database.get_history(symbol)
        if not data:
            data = await asyncio.to_thread(scraper.fetch_historical_data, symbol)
        return data if data else []
    except Exception as e:
        print(f"History error for {symbol}: {e}")
        return []

@app.get("/api/sectors", response_model=list[models.SectorData])
async def get_sectors():
    data = database.get_sectors()
    if not data:
        data = await asyncio.to_thread(scraper.fetch_sector_data)
    return data

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")
