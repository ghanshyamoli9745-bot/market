import time
from datetime import datetime
import database
import requests
from bs4 import BeautifulSoup
import traceback

def get_current_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

_company_name_cache = {}
_last_name_fetch = 0

def fetch_company_names():
    global _company_name_cache, _last_name_fetch
    now = time.time()
    if _company_name_cache and (now - _last_name_fetch < 3600):
        return _company_name_cache

    try:
        url = 'https://merolagani.com/LatestMarket.aspx'
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        table = soup.find('table', {'class': 'table table-hover live-trading sortable'})
        if not table: return _company_name_cache
        
        mapping = {}
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) >= 1:
                a = cols[0].find('a')
                if a:
                    symbol = a.text.strip()
                    name = a.get('title', symbol)
                    if '(' in name and symbol in name:
                        name = name.split('(', 1)[1].rsplit(')', 1)[0]
                    mapping[symbol] = name
        
        _company_name_cache = mapping
        _last_name_fetch = now
        return mapping
    except Exception as e:
        print(f"Error fetching company names: {e}")
        return _company_name_cache or {}

def fetch_live_data():
    timestamp = get_current_timestamp()
    name_mapping = fetch_company_names()
    try:
        url = 'https://www.sharesansar.com/live-trading'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        table = soup.find('table', {'id': 'headFixed'})
        if not table:
            return

        tbody = table.find('tbody')
        if not tbody:
            return

        rows = tbody.find_all('tr')
        prices_list = []
        
        for i, row in enumerate(rows):
            cols = row.find_all('td')
            if len(cols) >= 10:
                symbol = cols[1].text.strip()
                name = name_mapping.get(symbol, symbol)
                try:
                    price = float(cols[2].text.strip().replace(',', ''))
                    point_change = float(cols[3].text.strip().replace(',', ''))
                    percent_change = float(cols[4].text.strip().replace(',', ''))
                    volume = int(float(cols[8].text.strip().replace(',', '')))
                except ValueError:
                    continue

                prices_list.append({
                    "symbol": symbol,
                    "name": name,
                    "price": price,
                    "change": point_change,
                    "percent_change": percent_change,
                    "volume": volume,
                    "timestamp": timestamp
                })
        
        if not prices_list:
            return

        market_summary_data = {
            "index_value": 0.0,
            "change": 0.0,
            "percent_change": 0.0,
            "total_turnover": 0.0,
            "total_trades": 0,
            "total_scripts": len(prices_list),
            "market_status": "Unknown",
            "timestamp": timestamp
        }

        try:
            h4 = soup.find('h4', string=lambda text: text and "NEPSE Index" in text)
            if h4:
                summary_parent = h4.parent
                spans = summary_parent.find_all('span')
                if len(spans) >= 2:
                    market_summary_data['index_value'] = float(spans[0].text.strip().replace(',', ''))
                    change_text = spans[1].text.strip()
                    if '(' in change_text:
                        parts = change_text.split('(')
                        market_summary_data['change'] = float(parts[0].strip().replace(',', ''))
                        market_summary_data['percent_change'] = float(parts[1].replace('%', '').replace(')', '').strip())
                    else:
                        market_summary_data['percent_change'] = float(change_text.replace('%', '').strip())

                for p in summary_parent.find_all('p'):
                    val = p.text.strip().replace(',', '')
                    try:
                        fval = float(val)
                        if fval > 1000000:
                            market_summary_data['total_turnover'] = fval
                    except ValueError:
                        continue
            
            status_btn = soup.find('button', string=lambda text: text and "Market" in text)
            if status_btn:
                status_text = status_btn.text.strip()
                if "Closed" in status_text:
                    market_summary_data['market_status'] = "CLOSED"
                elif "Open" in status_text:
                    market_summary_data['market_status'] = "OPEN"
                else:
                    market_summary_data['market_status'] = status_text.upper()

        except Exception as e:
            print(f"Warning: Could not extract full market summary: {e}")

        prices_list.sort(key=lambda x: x["percent_change"], reverse=True)
        gainers = [{"symbol": p["symbol"], "price": p["price"], "percent_change": p["percent_change"], "timestamp": timestamp} for p in prices_list[:10]]
        losers_list = sorted(prices_list, key=lambda x: x["percent_change"])
        losers = [{"symbol": p["symbol"], "price": p["price"], "percent_change": p["percent_change"], "timestamp": timestamp} for p in losers_list[:10]]

        database.save_market_summary(market_summary_data)
        database.save_prices(prices_list)
        database.save_gainers_losers(gainers, losers)
        
        print(f"[{timestamp}] Live data fetched. Index: {market_summary_data['index_value']}")
    except Exception as e:
        print(f"Error fetching live data: {e}")

def fetch_company_fundamentals(symbol):
    timestamp = get_current_timestamp()
    try:
        url = f"https://merolagani.com/CompanyDetail.aspx?symbol={symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        data = {
            "symbol": symbol.upper(),
            "name": symbol.upper(),
            "sector": "Unknown",
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
            "business_model": "Product/Service sales and market expansion.",
            "management_quality": "Professional board of directors.",
            "industry_strength": "Competitive market dynamics.",
            "future_growth": "Depends on market share and innovation.",
            "timestamp": timestamp
        }
        
        table = soup.find('table', {'class': 'table table-striped table-hover table-zeromargin'})
        if table:
            for row in table.find_all('tr'):
                cols = row.find_all(['th', 'td'])
                if len(cols) >= 2:
                    label = cols[0].text.strip()
                    val = cols[1].text.strip().replace(',', '')
                    if "Sector" in label: data["sector"] = val
                    elif "Shares Outstanding" in label: data["paid_up_capital"] = val
                    elif "Market Capitalization" in label: data["market_cap"] = val
                    elif "52 Weeks High - Low" in label: data["high_low_52"] = val
                    elif "EPS" in label: 
                        try: data["eps_ttm"] = float(val.split('\n')[0].strip())
                        except: pass
                    elif "P/E Ratio" in label: 
                        try: data["pe_ratio"] = float(val)
                        except: pass
                    elif "Book Value" in label: 
                        try: data["book_value"] = float(val)
                        except: pass

        # Quantitative metrics based on sector
        sector = data["sector"].lower()
        if "bank" in sector:
            data["business_model"] = "Lending, interest income, and financial services."
            data["management_quality"] = "Strong, regulated by Central Bank."
            data["industry_strength"] = "Core of the economy, high barriers."
            data["future_growth"] = "Steady growth tied to national economy."
        elif "hydropower" in sector:
            data["business_model"] = "Electricity generation and sale to national grid."
            data["management_quality"] = "Variable, project-based."
            data["industry_strength"] = "Growing demand for clean energy."
            data["future_growth"] = "High potential with new projects."

        database.save_fundamentals(data)
        return data
    except Exception as e:
        print(f"Error fetching fundamentals: {e}")
        return None

def fetch_historical_data(symbol):
    try:
        url = f"https://chukul.com/api/data/historydata/?symbol={symbol}&resolution=1D"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=15)
        
        if res.status_code == 200:
            data = res.json()
            history_list = []
            for item in data:
                history_list.append({
                    "time": item['date'],
                    "open": float(item.get('open', 0)),
                    "high": float(item.get('high', 0)),
                    "low": float(item.get('low', 0)),
                    "close": float(item.get('close', 0)),
                    "volume": float(item.get('volume', 0))
                })
                
            # LightweightCharts requires data strictly sorted from oldest to newest
            history_list.sort(key=lambda x: x["time"])
            
            database.save_history(symbol, history_list)
            return history_list
        return []
    except Exception as e:
        print(f"Error fetching history for {symbol}: {e}")
        return []

def fetch_sector_data():
    timestamp = get_current_timestamp()
    try:
        # Use the market page which has a more reliable static table for sub-indices
        url = "https://www.sharesansar.com/market"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        sectors = []
        tables = soup.find_all('table')
        
        target_table = None
        for table in tables:
            # Look for a table that has sub-indices
            if 'Banking SubIndex' in table.text or 'HydroPower Index' in table.text:
                target_table = table
                break
        
        if target_table:
            rows = target_table.find_all('tr')
            for row in rows[1:]: # Skip header
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 7:
                    try:
                        name = cols[0].text.strip().replace(' SubIndex', '').replace(' Index', '')
                        # Correct columns based on debug: 0:Name, 4:Close, 5:Point, 6:%Change
                        index_val = float(cols[4].text.strip().replace(',', ''))
                        change = float(cols[5].text.strip().replace(',', ''))
                        percent_change = float(cols[6].text.strip().replace('%', '').replace(',', ''))
                        
                        sectors.append({
                            "sector": name,
                            "index_value": index_val,
                            "change": change,
                            "percent_change": percent_change,
                            "timestamp": timestamp
                        })
                    except (ValueError, IndexError):
                        continue
        
        if sectors:
            database.save_sectors(sectors)
            print(f"[{timestamp}] Scraped {len(sectors)} sectors successfully.")
        else:
            print(f"[{timestamp}] Warning: No sectors found in table.")
            
        return sectors
    except Exception as e:
        print(f"Error fetching sectors: {e}")
        return []

if __name__ == "__main__":
    database.init_db()
    fetch_live_data()
    fetch_sector_data()
