import sqlite3
import json
from datetime import datetime

DB_NAME = "nepse.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Existing tables...
    cursor.execute('CREATE TABLE IF NOT EXISTS companies (symbol TEXT PRIMARY KEY, name TEXT)')
    cursor.execute('''CREATE TABLE IF NOT EXISTS prices (
        symbol TEXT PRIMARY KEY, name TEXT, price REAL, change REAL, 
        percent_change REAL, volume REAL, timestamp TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS market_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT, index_value REAL, change REAL, 
        percent_change REAL, total_turnover REAL, total_trades INTEGER, 
        total_scripts INTEGER, market_status TEXT, timestamp TEXT)''')
    cursor.execute('CREATE TABLE IF NOT EXISTS gainers (symbol TEXT PRIMARY KEY, price REAL, percent_change REAL, timestamp TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS losers (symbol TEXT PRIMARY KEY, price REAL, percent_change REAL, timestamp TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS sectors (sector TEXT PRIMARY KEY, index_value REAL, change REAL, percent_change REAL, timestamp TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS fundamentals (symbol TEXT PRIMARY KEY, name TEXT, sector TEXT, listed_date TEXT, market_cap TEXT, paid_up_capital TEXT, high_low_52 TEXT, eps_ttm REAL, eps_reported TEXT, pe_ratio REAL, pb_ratio REAL, roe TEXT, book_value REAL, share_registrar TEXT, website TEXT, email TEXT, contact TEXT, head_office TEXT, mgmt_head TEXT, promoter_holding TEXT, public_holding TEXT, business_model TEXT, management_quality TEXT, industry_strength TEXT, future_growth TEXT, timestamp TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS history (symbol TEXT, time INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL, PRIMARY KEY (symbol, time))')

    # UPDATED API KEYS TABLE
    # Adding 'email' for cross-device sync and 'scope' for permissions
    try:
        cursor.execute('ALTER TABLE api_keys ADD COLUMN email TEXT')
    except: pass
    try:
        cursor.execute('ALTER TABLE api_keys ADD COLUMN scope TEXT DEFAULT "all"')
    except: pass

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS api_keys (
        api_key TEXT PRIMARY KEY,
        email TEXT,
        scope TEXT DEFAULT "all",
        features TEXT,
        created_at TEXT,
        last_used TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

# --- DATA SAVING FUNCTIONS ---
def save_market_summary(data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO market_summary (index_value, change, percent_change, total_turnover, total_trades, total_scripts, market_status, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (data['index_value'], data['change'], data['percent_change'], data['total_turnover'], data['total_trades'], data['total_scripts'], data.get('market_status', 'Unknown'), data['timestamp']))
    conn.commit()
    conn.close()

def save_prices(prices_list):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for item in prices_list:
        cursor.execute('INSERT OR REPLACE INTO prices (symbol, name, price, change, percent_change, volume, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)', (item['symbol'], item.get('name', ''), item['price'], item['change'], item['percent_change'], item['volume'], item['timestamp']))
    conn.commit()
    conn.close()

def save_gainers_losers(gainers, losers):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM gainers')
    for item in gainers: cursor.execute('INSERT INTO gainers (symbol, price, percent_change, timestamp) VALUES (?, ?, ?, ?)', (item['symbol'], item['price'], item['percent_change'], item['timestamp']))
    cursor.execute('DELETE FROM losers')
    for item in losers: cursor.execute('INSERT INTO losers (symbol, price, percent_change, timestamp) VALUES (?, ?, ?, ?)', (item['symbol'], item['price'], item['percent_change'], item['timestamp']))
    conn.commit()
    conn.close()

def save_sectors(sectors_list):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for item in sectors_list:
        cursor.execute('INSERT OR REPLACE INTO sectors (sector, index_value, change, percent_change, timestamp) VALUES (?, ?, ?, ?, ?)', (item['sector'], item['index_value'], item['change'], item['percent_change'], item['timestamp']))
    conn.commit()
    conn.close()

def save_fundamentals(data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO fundamentals (symbol, name, sector, listed_date, market_cap, paid_up_capital, high_low_52, eps_ttm, eps_reported, pe_ratio, pb_ratio, roe, book_value, share_registrar, website, email, contact, head_office, mgmt_head, promoter_holding, public_holding, business_model, management_quality, industry_strength, future_growth, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (data['symbol'], data.get('name', ''), data['sector'], data['listed_date'], data['market_cap'], data['paid_up_capital'], data['high_low_52'], data['eps_ttm'], data['eps_reported'], data['pe_ratio'], data['pb_ratio'], data['roe'], data['book_value'], data['share_registrar'], data['website'], data['email'], data['contact'], data['head_office'], data['mgmt_head'], data['promoter_holding'], data['public_holding'], data['business_model'], data['management_quality'], data['industry_strength'], data['future_growth'], data['timestamp']))
    conn.commit()
    conn.close()

def save_history(symbol, history_list):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for item in history_list:
        cursor.execute('INSERT OR REPLACE INTO history (symbol, time, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)', (symbol, item['time'], item['open'], item['high'], item['low'], item['close'], item['volume']))
    conn.commit()
    conn.close()

# --- GETTERS ---
def get_latest_market_summary():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT index_value, change, percent_change, total_turnover, total_trades, total_scripts, market_status, timestamp FROM market_summary ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    return {"index_value": row[0], "change": row[1], "percent_change": row[2], "total_turnover": row[3], "total_trades": row[4], "total_scripts": row[5], "market_status": row[6], "timestamp": row[7]} if row else None

def get_live_prices():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT symbol, name, price, change, percent_change, volume, timestamp FROM prices ORDER BY volume DESC')
    rows = cursor.fetchall()
    conn.close()
    return [{"symbol": r[0], "name": r[1], "price": r[2], "change": r[3], "percent_change": r[4], "volume": r[5], "timestamp": r[6]} for r in rows]

def get_top_gainers():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT symbol, price, percent_change, timestamp FROM gainers ORDER BY percent_change DESC')
    rows = cursor.fetchall()
    conn.close()
    return [{"symbol": r[0], "price": r[1], "percent_change": r[2], "timestamp": r[3]} for r in rows]

def get_top_losers():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT symbol, price, percent_change, timestamp FROM losers ORDER BY percent_change ASC')
    rows = cursor.fetchall()
    conn.close()
    return [{"symbol": r[0], "price": r[1], "percent_change": r[2], "timestamp": r[3]} for r in rows]

def get_sectors():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT sector, index_value, change, percent_change, timestamp FROM sectors')
    rows = cursor.fetchall()
    conn.close()
    return [{"sector": r[0], "index_value": r[1], "change": r[2], "percent_change": r[3], "timestamp": r[4]} for r in rows]

def get_fundamentals(symbol):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM fundamentals WHERE symbol=?', (symbol.upper(),))
    row = cursor.fetchone()
    conn.close()
    return {"symbol": row[0], "name": row[1], "sector": row[2], "listed_date": row[3], "market_cap": row[4], "paid_up_capital": row[5], "high_low_52": row[6], "eps_ttm": row[7], "eps_reported": row[8], "pe_ratio": row[9], "pb_ratio": row[10], "roe": row[11], "book_value": row[12], "share_registrar": row[13], "website": row[14], "email": row[15], "contact": row[16], "head_office": row[17], "mgmt_head": row[18], "promoter_holding": row[19], "public_holding": row[20], "business_model": row[21], "management_quality": row[22], "industry_strength": row[23], "future_growth": row[24], "timestamp": row[25]} if row else None

def get_history(symbol):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT time, open, high, low, close, volume FROM history WHERE symbol=? ORDER BY time ASC', (symbol.upper(),))
    rows = cursor.fetchall()
    conn.close()
    return [{"time": r[0], "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]} for r in rows]

# --- UPDATED API KEY SYSTEM ---

def generate_api_key(email=None, scope="all"):
    import uuid
    new_key = str(uuid.uuid4())
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # If email is provided, we can either update existing key or add new one
    if email:
        cursor.execute('DELETE FROM api_keys WHERE email=?', (email.lower(),))
    
    cursor.execute('INSERT INTO api_keys (api_key, email, scope, created_at) VALUES (?, ?, ?, ?)', 
                   (new_key, email.lower() if email else None, scope, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return new_key

def get_key_by_email(email):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT api_key, scope FROM api_keys WHERE email=?', (email.lower(),))
    row = cursor.fetchone()
    conn.close()
    return {"api_key": row[0], "scope": row[1]} if row else None

def validate_api_key(key, required_scope=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT scope FROM api_keys WHERE api_key=?', (key,))
    row = cursor.fetchone()
    if row:
        actual_scope = row[0]
        # 'all' works for everything. Otherwise must match.
        if actual_scope == 'all' or actual_scope == required_scope or required_scope is None:
            cursor.execute('UPDATE api_keys SET last_used=? WHERE api_key=?', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), key))
            conn.commit()
            conn.close()
            return True
    conn.close()
    return False

def sync_to_firebase(data):
    import requests
    FIREBASE_URL = "https://stock-market-e710b-default-rtdb.firebaseio.com/dashboard.json"
    try:
        requests.put(FIREBASE_URL, json=data, timeout=10)
    except: pass
