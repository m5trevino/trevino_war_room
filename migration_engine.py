import sqlite3
import json
import os
from datetime import datetime, timezone
import dateutil.parser

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

def process_files(file_list):
    print(f"--- STARTING MIGRATION ON {len(file_list)} FILES ---")
    
    conn = sqlite3.connect(DB_FILE, timeout=30)
    c = conn.cursor()
    
    # Ensure table exists
    c.execute('''CREATE TABLE IF NOT EXISTS jobs
                 (id TEXT PRIMARY KEY, title TEXT, company TEXT, city TEXT, 
                  state TEXT, date_posted INTEGER, annual_pay INTEGER, 
                  pay_fmt TEXT, score INTEGER, raw_json TEXT, status TEXT)''')
    
    # Load Blacklist
    blacklist = []
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, 'r') as f: 
            blacklist = [x.lower() for x in json.load(f)]

    stats = {"new": 0, "skipped": 0, "blacklisted": 0, "files": 0}

    for filename in file_list:
        if not os.path.exists(filename): continue
        print(f"Processing {filename}...")
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = json.load(f)
                jobs = []
                if isinstance(content, list): jobs = content
                elif isinstance(content, dict):
                    if 'jobs' in content: jobs = content['jobs']
                    elif 'results' in content: jobs = content['results']
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue

        stats["files"] += 1
        
        for job in jobs:
            # Generate ID
            jid = job.get('key')
            if not jid: jid = f"job_{stats['new']}_{int(datetime.now().timestamp())}"
            
            # Check existing
            c.execute("SELECT status FROM jobs WHERE id=?", (jid,))
            row = c.fetchone()
            if row:
                stats["skipped"] += 1
                continue

            # Check Blacklist (SAFE EMPLOYER HANDLING)
            title = safe_str(job.get('title')).lower()
            
            # Safe access for nested dictionary that might be None
            emp_data = job.get('employer') or {}
            if isinstance(emp_data, dict):
                employer = emp_data.get('name', '')
            else:
                employer = str(emp_data)
                
            employer = safe_str(employer).lower()
            
            status = "NEW"
            for term in blacklist:
                if term in title or term in employer:
                    status = "AUTO_DENIED"
                    stats["blacklisted"] += 1
                    break

            # Process fields
            freshness = calc_freshness(job)
            pay_val, pay_fmt = normalize_pay(job)
            loc = job.get('location') or {}
            
            c.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                jid,
                job.get('title', 'Unknown'),
                employer.title(), # Store title cased
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

    conn.commit()
    conn.close()
    return stats
