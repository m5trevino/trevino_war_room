import sqlite3
import json
import os
import hashlib
from datetime import datetime, timezone
import dateutil.parser

DB_FILE = "jobs.db"
BLACKLIST_FILE = "blacklist.json"
SCRAPE_DIR = "scrapes"

def calc_freshness(job):
    try:
        raw = job.get('datePublished')
        if not raw: return 0
        dt = dateutil.parser.isoparse(raw)
        now = datetime.now(timezone.utc)
        return (now - dt).days
    except: return 0

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

def process_files(file_list):
    print(f"--- MIGRATION STARTED: {len(file_list)} FILES ---")
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. ENSURE SCHEMA EXISTS
    c.execute('''CREATE TABLE IF NOT EXISTS jobs
                 (id TEXT PRIMARY KEY, title TEXT, company TEXT, city TEXT, 
                  state TEXT, date_posted INTEGER, annual_pay INTEGER, 
                  pay_fmt TEXT, score INTEGER, raw_json TEXT, status TEXT)''')
    
    # 2. SELF-HEAL: Check for missing columns in existing DB
    c.execute("PRAGMA table_info(jobs)")
    existing_cols = [row[1] for row in c.fetchall()]
    required_cols = ["date_posted", "annual_pay", "pay_fmt", "score", "raw_json", "status"]
    
    for col in required_cols:
        if col not in existing_cols:
            print(f"Repairing DB: Adding missing column '{col}'...")
            try:
                c.execute(f"ALTER TABLE jobs ADD COLUMN {col} TEXT")
                if col == "score": c.execute("UPDATE jobs SET score=50")
                if col == "status": c.execute("UPDATE jobs SET status='NEW'")
            except Exception as e:
                print(f"Failed to add column {col}: {e}")

    # Load Blacklist
    blacklist = []
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, 'r') as f: 
                blacklist = [x.lower() for x in json.load(f)]
        except: pass

    stats = {"new": 0, "skipped": 0, "blacklisted": 0, "files": 0}

    for filename in file_list:
        # PATH CORRECTION: Look in the scrapes folder
        full_path = os.path.join(os.getcwd(), SCRAPE_DIR, filename)
        
        if not os.path.exists(full_path): 
            print(f"File not found: {full_path}")
            continue
            
        print(f"Processing {filename}...")
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                jobs = content if isinstance(content, list) else content.get('jobs', [])
        except Exception as e:
            print(f"CRITICAL: Could not read {filename}: {e}")
            continue

        stats["files"] += 1
        
        for job in jobs:
            # ID Logic
            jid = job.get('key')
            if not jid: 
                raw_id = job.get('url') or (job.get('title', '') + job.get('company', ''))
                jid = hashlib.md5(raw_id.encode()).hexdigest()
            
            # Check Exists
            c.execute("SELECT id FROM jobs WHERE id=?", (jid,))
            if c.fetchone():
                stats["skipped"] += 1
                continue

            # Check Blacklist
            title = safe_str(job.get('title')).lower()
            employer = safe_str(job.get('employer', {}).get('name', '')).lower()
            status = "NEW"
            
            for term in blacklist:
                if term in title or term in employer:
                    status = "AUTO_DENIED"
                    stats["blacklisted"] += 1
                    break

            # Data Prep
            freshness = calc_freshness(job)
            pay_val, pay_fmt = normalize_pay(job)
            loc = job.get('location') or {}
            
            try:
                c.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                    jid,
                    safe_str(job.get('title')),
                    safe_str(job.get('employer', {}).get('name')),
                    safe_str(loc.get('city')),
                    safe_str(loc.get('admin1Code')),
                    freshness,
                    pay_val,
                    pay_fmt,
                    50, 
                    json.dumps(job),
                    status
                ))
                if status == "NEW": stats["new"] += 1
            except Exception as e:
                print(f"Error inserting job {jid}: {e}")

    conn.commit()
    conn.close()
    print(f"--- MIGRATION COMPLETE. NEW JOBS: {stats['new']} ---")
    return stats
