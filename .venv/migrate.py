import sqlite3
import json
import os
from datetime import datetime, timezone
import dateutil.parser

# --- CONFIG ---
JSON_FILE = "indeed.json"
DB_FILE = "jobs.db"
BLACKLIST_FILE = "blacklist.json"

def calc_freshness(job):
    try:
        raw = job.get('datePublished')
        if not raw: return 999
        dt = dateutil.parser.isoparse(raw)
        now = datetime.now(timezone.utc)
        return (now - dt).days
    except: return 999

def safe_str(val):
    return str(val) if val is not None else ""

def normalize_pay(job):
    try:
        bs = job.get('baseSalary', {})
        if not bs: return 0, "-"
        min_p = bs.get('min')
        if not min_p: return 0, "-"
        unit = bs.get('unitOfWork', 'YEAR')
        val = float(min_p)
        annual = 0
        if unit == 'HOUR': annual = val * 2080
        elif unit == 'MONTH': annual = val * 12
        elif unit == 'WEEK': annual = val * 52
        else: annual = val
        return int(annual), f"${int(annual/1000)}k" if annual > 10000 else f"${int(val)}/hr"
    except: return 0, "-"

def main():
    print("--- STARTING SAFE MIGRATION ---")
    
    # 1. Create DB if not exists, but DO NOT DELETE IT
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Create table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS jobs
                 (id TEXT PRIMARY KEY, title TEXT, company TEXT, city TEXT, 
                  state TEXT, date_posted INTEGER, annual_pay INTEGER, 
                  pay_fmt TEXT, score INTEGER, raw_json TEXT, status TEXT)''')
    
    # Load Blacklist
    blacklist = []
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, 'r') as f: 
            blacklist = [x.lower() for x in json.load(f)]

    print(f"Loading {JSON_FILE}...")
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            jobs = data if isinstance(data, list) else data.get('jobs', [])
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return

    count = 0
    skipped = 0
    blacklisted = 0
    
    for job in jobs:
        # Generate ID
        jid = job.get('key')
        if not jid: jid = f"job_{count}_{int(datetime.now().timestamp())}"
        
        # Check if job exists
        c.execute("SELECT status FROM jobs WHERE id=?", (jid,))
        row = c.fetchone()
        if row:
            # Job exists, skip it to preserve status
            skipped += 1
            continue

        # Check Blacklist
        title = safe_str(job.get('title')).lower()
        employer = job.get('employer', {}).get('name', '').lower()
        status = "NEW"
        
        for term in blacklist:
            if term in title or term in employer:
                status = "AUTO_DENIED"
                blacklisted += 1
                break

        # Process fields
        freshness = calc_freshness(job)
        pay_val, pay_fmt = normalize_pay(job)
        loc = job.get('location') or {}
        
        # Insert new job
        c.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            jid,
            job.get('title', 'Unknown'),
            job.get('employer', {}).get('name', 'Unknown'),
            safe_str(loc.get('city')),
            safe_str(loc.get('admin1Code')),
            freshness,
            pay_val,
            pay_fmt,
            50, # Default score, will be recalc'd by server
            json.dumps(job),
            status
        ))
        count += 1

    conn.commit()
    conn.close()
    print(f"DONE: {count} new imported. {skipped} existing skipped. {blacklisted} auto-blacklisted.")

if __name__ == "__main__":
    main()
