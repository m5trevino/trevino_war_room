from flask import Flask, jsonify, request, send_from_directory
import sqlite3
import json
import os
import random
import glob
import traceback
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
import migration_engine

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
DB_FILE = 'jobs.db'
HISTORY_FILE = 'job_history.json'
TAGS_FILE = 'categorized_tags.json'
BLACKLIST_FILE = 'blacklist.json'
RESUME_FILE = 'master_resume.txt'
SCRAPE_DIR = 'scrapes'

# --- SESSION TRACKER ---
SESSION_STATS = {"scraped":0, "approved":0, "denied":0, "sent_to_groq":0}

keys_raw = os.getenv("GROQ_KEYS", "")
KEY_DECK = []
for item in keys_raw.split(","):
    if ":" in item: KEY_DECK.append(item.split(":", 1)[1])
    elif item.strip(): KEY_DECK.append(item.strip())
random.shuffle(KEY_DECK)
current_key_index = 0

def get_next_key():
    global current_key_index
    if not KEY_DECK: return os.getenv("GROQ_API_KEY", "")
    if current_key_index >= len(KEY_DECK):
        random.shuffle(KEY_DECK)
        current_key_index = 0
    key = KEY_DECK[current_key_index]
    current_key_index += 1
    return key

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def load_json(filename, default=None):
    if default is None: default = {}
    if not os.path.exists(filename): return default
    try:
        with open(filename, 'r') as f: return json.load(f)
    except: return default

def save_json(filename, data):
    with open(filename, 'w') as f: json.dump(data, f, indent=2)

def update_history(key, amount=1):
    if key in SESSION_STATS: SESSION_STATS[key] += amount
    h = load_json(HISTORY_FILE, {"all_time":{}})
    if "all_time" not in h: h["all_time"] = {}
    if key not in h["all_time"]: h["all_time"][key] = 0
    h["all_time"][key] += amount
    save_json(HISTORY_FILE, h)

def sanitize_filename(title):
    return "".join(c for c in title if c.isalnum() or c in " -_").strip()[:50]

print("--- WAR ROOM ONLINE ---")
print(f"KEYS LOADED: {len(KEY_DECK)}")
print(f"DATABASE: {DB_FILE}")

# --- ROUTES ---

@app.route('/api/status')
def status():
    h = load_json(HISTORY_FILE, {"all_time":{}})
    all_time = h.get("all_time", {})
    for k in ["scraped", "approved", "denied", "sent_to_groq"]:
        if k not in all_time: all_time[k] = 0
    return jsonify({"session": SESSION_STATS, "all_time": all_time})

@app.route('/api/jobs')
def jobs():
    status_filter = request.args.get('status', 'NEW')
    conn = get_db()
    query = "SELECT id, title, company, city, pay_fmt, date_posted, score, status, raw_json FROM jobs WHERE 1=1"
    
    if status_filter == 'NEW': query += " AND (status IS NULL OR status = 'NEW')"
    elif status_filter in ['APPROVED', 'REFINERY', 'FACTORY']: query += " AND status = 'APPROVED'"
    elif status_filter == 'DENIED': query += " AND (status = 'DENIED' OR status = 'AUTO_DENIED')"
    
    query += " ORDER BY score DESC, date_posted ASC"
    
    try:
        rows = conn.execute(query).fetchall()
        out = []
        for r in rows:
            safe_title = sanitize_filename(r['title'])
            # Check for AI artifact in input_json (no move logic anymore)
            has_ai = os.path.exists(f"input_json/{safe_title}_{r['id']}.json")
            # Check for PDF in done
            has_pdf = os.path.exists(f"done/{safe_title}_{r['id']}.pdf")
            
            if status_filter == 'DELIVERED' and not has_pdf: continue
                
            out.append({
                "id": r['id'], "title": r['title'], "company": r['company'],
                "city": r['city'], "pay": r['pay_fmt'], "freshness": r['date_posted'], 
                "score": r['score'], "status": r['status'],
                "has_ai": has_ai, "has_pdf": has_pdf, "safe_title": safe_title
            })
        return jsonify(out)
    except Exception as e: return jsonify([])
    finally: conn.close()

@app.route('/api/get_job_details')
def job_details():
    id = request.args.get('id')
    conn = get_db()
    row = conn.execute("SELECT raw_json FROM jobs WHERE id=?", (id,)).fetchone()
    conn.close()
    if not row: return jsonify({"description":"Not Found", "skills":[]})
    
    data = json.loads(row['raw_json'])
    desc = data.get('description', {}).get('html') or data.get('description', {}).get('text') or "No Desc"
    
    tags_db = load_json(TAGS_FILE, {"qualifications": [], "skills": [], "benefits": [], "ignored": []})
    category_map = {}
    for cat, items in tags_db.items():
        for item in items: category_map[item.lower()] = cat

    job_skills = []
    for k, v in data.get('attributes', {}).items():
        cat = category_map.get(v.lower(), "new")
        job_skills.append({"name": v, "category": cat})
        
    return jsonify({"description": desc, "skills": job_skills})

@app.route('/api/harvest_tag', methods=['POST'])
def harvest_tag():
    tag = request.json.get('tag')
    category = request.json.get('category', 'skills')
    tags_db = load_json(TAGS_FILE, {"qualifications": [], "skills": [], "benefits": [], "ignored": []})
    for cat in tags_db:
        if tag in tags_db[cat]: tags_db[cat].remove(tag)
    if tag not in tags_db[category]:
        tags_db[category].append(tag)
        save_json(TAGS_FILE, tags_db)
    return jsonify({"status": "harvested"})

@app.route('/api/process_job', methods=['POST'])
def process_job():
    job_id = request.json['id']
    conn = get_db()
    row = conn.execute("SELECT raw_json, title FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    
    job_data = json.loads(row['raw_json'])
    try:
        with open(RESUME_FILE, 'r') as f: resume_text = f.read()
    except: resume_text = "Master resume not found."
    
    job_desc = job_data.get('description', {}).get('text', '')
    tags_db = load_json(TAGS_FILE, {})
    quals = ", ".join(tags_db.get('qualifications', []))
    skills = ", ".join(tags_db.get('skills', []))
    
    prompt = f"RESUME:\n{resume_text}\n\nMY QUALIFICATIONS: {quals}\nMY SKILLS: {skills}\n\nJOB:\n{job_desc}\n\nTASK: Return JSON tailored resume."
    
    try:
        key = get_next_key()
        client = Groq(api_key=key)
        completion = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        result = completion.choices[0].message.content
        if not os.path.exists('input_json'): os.makedirs('input_json')
        safe_title = sanitize_filename(row['title'])
        filename = f"input_json/{safe_title}_{job_id}.json"
        with open(filename, 'w') as f: f.write(result)
        update_history('sent_to_groq')
        return jsonify({"status": "processed", "key": key[:10], "file_saved": filename})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/approve', methods=['POST'])
def approve():
    conn = get_db()
    conn.execute("UPDATE jobs SET status='APPROVED' WHERE id=?", (request.json['id'],))
    conn.commit()
    conn.close()
    update_history('approved')
    return jsonify({"status":"approved"})

@app.route('/api/deny', methods=['POST'])
def deny():
    conn = get_db()
    conn.execute("UPDATE jobs SET status='DENIED' WHERE id=?", (request.json['id'],))
    conn.commit()
    conn.close()
    update_history('denied')
    return jsonify({"status":"denied"})

@app.route('/api/restore', methods=['POST'])
def restore():
    conn = get_db()
    conn.execute("UPDATE jobs SET status='NEW' WHERE id=?", (request.json['id'],))
    conn.commit()
    conn.close()
    return jsonify({"status":"restored"})

@app.route('/api/blacklist', methods=['POST'])
def blacklist():
    term = request.json.get('term', '').lower()
    bl = load_json(BLACKLIST_FILE, [])
    if term not in bl:
        bl.append(term)
        save_json(BLACKLIST_FILE, bl)
    conn = get_db()
    conn.execute(f"UPDATE jobs SET status='AUTO_DENIED' WHERE (lower(title) LIKE ? OR lower(company) LIKE ?) AND status != 'APPROVED'", (f'%{term}%', f'%{term}%'))
    conn.commit()
    conn.close()
    return jsonify({"status": "blacklisted"})

@app.route('/api/get_artifact')
def get_artifact():
    id = request.args.get('id')
    conn = get_db()
    row = conn.execute("SELECT title FROM jobs WHERE id=?", (id,)).fetchone()
    conn.close()
    safe_title = sanitize_filename(row['title'])
    json_path = f"input_json/{safe_title}_{id}.json"
    if os.path.exists(json_path):
        with open(json_path, 'r') as f: return jsonify({"content": f.read()})
    return jsonify({"content": "No Artifact"})

@app.route('/api/scrapes', methods=['GET'])
def list_scrapes():
    # Force Absolute Path Logic
    folder = os.path.join(os.getcwd(), SCRAPE_DIR)
    
    if not os.path.exists(folder):
        print(f"DEBUG: Folder missing: {folder}")
        os.makedirs(folder)
        return jsonify([])
    
    files = [f for f in os.listdir(folder) if f.lower().endswith('.json')]
    print(f"DEBUG: Scanning {folder} -> Found: {len(files)} files")
    return jsonify(files)

@app.route('/api/migrate', methods=['POST'])
def run_migration():
    files = request.json.get('files', [])
    try:
        stats = migration_engine.process_files(files)
        SESSION_STATS['scraped'] += stats["new"]
        h = load_json(HISTORY_FILE, {"all_time":{}})
        if "scraped" not in h["all_time"]: h["all_time"]["scraped"] = 0
        h["all_time"]["scraped"] += stats["new"]
        save_json(HISTORY_FILE, h)
        return jsonify({"status": "success", "stats": stats})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index(): return send_from_directory('templates', 'index.html')
@app.route('/static/<path:path>')
def send_static(path): return send_from_directory('static', path)

if __name__ == "__main__":
    app.run(port=5000, debug=False)
