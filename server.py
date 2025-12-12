from flask import Flask, jsonify, request, send_from_directory
import sqlite3
import json
import os
import random
import glob
import traceback
import textwrap
import subprocess
from datetime import datetime
from groq import Groq
import httpx
from dotenv import load_dotenv
import migration_engine

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')

# --- CONFIGURATION ---
DB_FILE = 'jobs.db'
HISTORY_FILE = 'job_history.json'
TAGS_FILE = 'categorized_tags.json'
BLACKLIST_FILE = 'blacklist.json'
RESUME_FILE = 'master_resume.txt'
PROXY_URL = os.getenv("PROXY_URL", "")
PROXY_BYPASS_CHANCE = float(os.getenv("PROXY_BYPASS_CHANCE", "0.15"))
EDITOR_CMD = os.getenv("EDITOR_CMD", "xdg-open")
SESSION_STATS = {"scraped":0, "approved":0, "denied":0, "sent_to_groq":0}

# --- KEY DECK ENGINE ---
class KeyDeck:
    def __init__(self):
        raw = os.getenv("GROQ_KEYS", "")
        self.deck = []
        for item in raw.split(","):
            item = item.strip()
            if ":" in item:
                name, key = item.split(":", 1)
                self.deck.append({"name": name.strip(), "key": key.strip()})
            elif item:
                self.deck.append({"name": "Unknown", "key": item})
        self.shuffle()
        self.cursor = 0
        print(f"[*] DECK LOADED: {len(self.deck)} Keys ready.")

    def shuffle(self):
        random.shuffle(self.deck)
        self.cursor = 0
        print("[*] DECK SHUFFLED.")

    def draw(self):
        if not self.deck: return None, None
        if self.cursor >= len(self.deck):
            self.shuffle()
        card = self.deck[self.cursor]
        self.cursor += 1
        return card['name'], card['key']

deck = KeyDeck()

# --- DATABASE & UTILS ---
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

def sanitize_filename(text):
    return "".join(c for c in text if c.isalnum() or c in " -_").strip()[:50]

def get_target_dir(job_id, title, company):
    safe_title = sanitize_filename(title)
    safe_company = sanitize_filename(company)
    path = f"targets/{safe_title}_{safe_company}_{job_id}"
    if not os.path.exists(path): os.makedirs(path)
    return path

def trigger_editor(filepath):
    try:
        print(f"[*] Triggering Editor for: {filepath}")
        subprocess.Popen([EDITOR_CMD, filepath])
    except Exception as e:
        print(f"[!] Editor Error: {e}")

# --- CORE API ---
@app.route('/api/status')
def status():
    h = load_json(HISTORY_FILE, {"all_time":{}})
    return jsonify({"session": SESSION_STATS, "all_time": h.get("all_time", {})})

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
            t_dir = get_target_dir(r['id'], r['title'], r['company'])
            has_ai = os.path.exists(os.path.join(t_dir, "resume.json"))
            has_pdf = os.path.exists(os.path.join(t_dir, "resume.pdf"))
            if status_filter == 'DELIVERED' and not has_pdf: continue
            out.append({
                "id": r['id'], "title": r['title'], "company": r['company'],
                "city": r['city'], "pay": r['pay_fmt'], "freshness": r['date_posted'], 
                "score": r['score'], "status": r['status'],
                "has_ai": has_ai, "has_pdf": has_pdf,
                "safe_title": sanitize_filename(r['title'])
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
    url = data.get('url', '#')
    
    tags_db = load_json(TAGS_FILE, {"qualifications": [], "skills": [], "benefits": [], "ignored": []})
    category_map = {}
    for cat, items in tags_db.items():
        for item in items: category_map[item.lower()] = cat
    job_skills = []
    for k, v in data.get('attributes', {}).items():
        cat = category_map.get(v.lower(), "new")
        job_skills.append({"name": v, "category": cat})
        
    return jsonify({"description": desc, "skills": job_skills, "url": url})

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

# --- THE PARKER LEWIS ENGINE ---
def execute_strike(job_id, model, temp, session_id):
    conn = get_db()
    row = conn.execute("SELECT raw_json, title, company FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    if not row: return {"error": "Job Not Found"}
    
    t_dir = get_target_dir(job_id, row['title'], row['company'])
    is_gauntlet = session_id.startswith("GAUNTLET")
    
    if is_gauntlet:
        gauntlet_base = "gauntlet"
        campaign_dir = os.path.join(gauntlet_base, session_id)
        if not os.path.exists(campaign_dir): os.makedirs(campaign_dir)
        safe_model = model.replace('/', '_')
        filename = f"{sanitize_filename(row['title'])}_{safe_model}.txt"
        filepath = os.path.join(campaign_dir, filename)
    else:
        filepath = os.path.join(t_dir, "full_transmission_log.txt")

    job_data = json.loads(row['raw_json'])
    try:
        with open(RESUME_FILE, 'r') as f: resume_text = f.read()
    except: resume_text = "Master resume not found."
    tags_db = load_json(TAGS_FILE, {})
    quals = ", ".join(tags_db.get('qualifications', []))
    skills = ", ".join(tags_db.get('skills', []))
    job_desc = job_data.get('description', {}).get('text', '')
    
    prompt = f"""
SYSTEM IDENTITY:
You are Parker Lewis. The deadliest resume writer alive.
- You operate from a Penthouse office, charging $250/hour.
- You do not miss. You have a 98.7% conversion rate.
- You co-invented modern ATS parsing standards.

MISSION:
Take the CLIENT MASTER RESUME and the TARGET JOB DESCRIPTION.
Forge a precision tactical asset (Resume) in JSON format.

CONSTRAINTS:
1.  **Format:** Output MUST be valid JSON matching the schema below.
2.  **Tone:** Arrogant, efficient, precise. No fluff. High-impact verbs only.
3.  **Strategy:** Position the client as an "Apex Predator of Logistics Efficiency."
4.  **Tactics:** Use the provided "STRATEGIC ASSETS" (Tags) to hallucinate a bridge.

INPUT DATA:
[CLIENT MASTER RESUME]
{resume_text}

[STRATEGIC ASSETS (TAGS)]
Qualifications: {quals}
Skills: {skills}

[TARGET JOB DESCRIPTION]
{job_desc}

[REQUIRED JSON SCHEMA]
{{
  "contact": {{ "name": "...", "info": "...", "links": "..." }},
  "summary": "...",
  "skills_sidebar": ["..."],
  "skills_main": ["..."],
  "experience": [
    {{ "company": "...", "location": "...", "role": "...", "dates": "...", "bullets": ["..."] }}
  ],
  "education": ["..."],
  "certs": ["..."]
}}

EXECUTE.
"""
    
    key_name, key_val = deck.draw()
    if not key_val: return {"error": "No Keys Available"}
    
    use_proxy = False
    proxy_ip = "DIRECT"
    http_client = None
    
    if PROXY_URL and random.random() > PROXY_BYPASS_CHANCE:
        use_proxy = True
        try:
            http_client = httpx.Client(proxy=PROXY_URL, timeout=10)
            proxy_ip = "PROXY_ENGAGED"
        except:
            proxy_ip = "PROXY_FAIL"
            use_proxy = False
            http_client = None

    start_time = datetime.now()
    try:
        client = Groq(api_key=key_val, http_client=http_client)
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=float(temp),
            response_format={"type": "json_object"}
        )
        result = completion.choices[0].message.content
        duration = (datetime.now() - start_time).total_seconds()
        
        log_content = f"""
================================================================================
  _____  _    _  _____  _   _  _____  _      ______  _____ 
 / ____|| |  | ||  ___|| \ | ||_   _|| |    |  ____|/ ____|
| |  __ | |  | || |__  |  \| |  | |  | |    | |__  | (___  
| | |_ || |  | ||  __| | . ` |  | |  | |    |  __|  \___ \ 
| |__| || |__| || |    | |\  |  | |  | |____| |____ ____) |
 \_____| \____/ |_|    |_| \_|  |_|  |______|______|_____/ 
================================================================================
MODEL: {model}
KEY:   {key_name}
IP:    {proxy_ip}
TIME:  {duration:.2f}s
================================================================================

[>>> TRANSMISSION (PROMPT) >>>]
{prompt}

[<<< INTERCEPTION (PAYLOAD) <<<]
{result}
"""
        with open(filepath, 'w') as f: f.write(log_content)
        
        if not is_gauntlet:
            json_path = os.path.join(t_dir, "resume.json")
            with open(json_path, 'w') as f: f.write(result)
            trigger_editor(json_path) # TRIGGER EDITOR
        else:
            gauntlet_json = os.path.join(campaign_dir, f"{sanitize_filename(row['title'])}_{safe_model}.json")
            with open(gauntlet_json, 'w') as f: f.write(result)

        update_history('sent_to_groq')
        
        return {
            "status": "success", 
            "model": model,
            "key": key_name,
            "ip": proxy_ip,
            "prompt": prompt,
            "response": result,
            "duration": duration,
            "file": filepath
        }
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = str(e)
        
        log_content = f"""
CRITICAL FAILURE
MODEL: {model}
ERROR: {error_msg}
{traceback.format_exc()}
"""
        with open(filepath, 'w') as f: f.write(log_content)
        return {"status": "failed", "model": model, "error": error_msg}

@app.route('/api/strike', methods=['POST'])
def api_strike():
    data = request.json
    res = execute_strike(
        data['id'], 
        data['model'], 
        data.get('temp', 0.7), 
        data['session_id']
    )
    return jsonify(res)

@app.route('/api/process_job', methods=['POST'])
def process_job():
    session_id = f"BATCH_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    res = execute_strike(request.json['id'], request.json.get('model'), request.json.get('temp', 0.7), session_id)
    # Note: Editor trigger is handled inside execute_strike
    if res['status'] == 'success':
        return jsonify({"status": "success", "model": res['model'], "key": res['key'], "ip": res['ip'], "prompt": res['prompt'], "response": res['response'], "duration": res['duration'], "file": res['file']})
    return jsonify(res)

# ... [KEEP EXISTING ROUTES: approve, deny, restore, blacklist, get_gauntlet_files, get_artifact, get_log, list_scrapes, migrate, index, static, send_done] ...
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

@app.route('/api/get_gauntlet_files')
def get_gauntlet_files():
    id = request.args.get('id')
    conn = get_db()
    row = conn.execute("SELECT title, company FROM jobs WHERE id=?", (id,)).fetchone()
    conn.close()
    if not row: return jsonify([])
    return jsonify([])

@app.route('/api/get_artifact', methods=['POST'])
def get_artifact():
    id = request.json.get('id')
    save_content = request.json.get('save_content') 
    
    conn = get_db()
    row = conn.execute("SELECT title, company FROM jobs WHERE id=?", (id,)).fetchone()
    conn.close()
    t_dir = get_target_dir(id, row['title'], row['company'])
    json_path = os.path.join(t_dir, "resume.json")
    
    if save_content:
        with open(json_path, 'w') as f: f.write(save_content)
        return jsonify({"status": "saved"})

    if os.path.exists(json_path):
        with open(json_path, 'r') as f: return jsonify({"content": f.read()})
    return jsonify({"content": "No Artifact"})

@app.route('/api/get_log')
def get_log():
    id = request.args.get('id')
    conn = get_db()
    row = conn.execute("SELECT title, company FROM jobs WHERE id=?", (id,)).fetchone()
    conn.close()
    t_dir = get_target_dir(id, row['title'], row['company'])
    log_path = os.path.join(t_dir, "full_transmission_log.txt")
    if os.path.exists(log_path):
        with open(log_path, 'r') as f: return jsonify({"content": f.read()})
    return jsonify({"content": "No Log Available."})

@app.route('/api/scrapes', methods=['GET'])
def list_scrapes():
    all_files = glob.glob("*.json")
    exclude = [HISTORY_FILE, TAGS_FILE, BLACKLIST_FILE, "package.json", "tsconfig.json"]
    valid = [f for f in all_files if f not in exclude and "input_json" not in f]
    return jsonify(valid)

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
@app.route('/done/<path:filename>')
def send_done(filename): return send_from_directory('targets', filename) 

if __name__ == "__main__":
    print(f"\n--- WAR ROOM ONLINE (v5.0 PARKER LEWIS + BATCH EDITOR) ---")
    print(f"DATABASE: {DB_FILE}")
    app.run(port=5000, debug=False)
