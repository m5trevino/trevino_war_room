from flask import Flask, jsonify, request, send_from_directory
import sqlite3
import json
import os
import random
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

# 1. IGNITION: Load Environment Variables
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
DB_FILE = 'jobs.db'
HISTORY_FILE = 'job_history.json'
SKILLS_FILE = 'my_skills.json'
BLACKLIST_FILE = 'blacklist.json'
RESUME_FILE = 'master_resume.txt'

# 2. DECK OF CARDS: Logic to parse keys correctly
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

# --- UTILS ---
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def load_json(filename, default=[]):
    if not os.path.exists(filename): return default
    with open(filename, 'r') as f: return json.load(f)

def save_json(filename, data):
    with open(filename, 'w') as f: json.dump(data, f, indent=2)

def update_history(key, amount=1):
    h = load_json(HISTORY_FILE, {"session":{}, "all_time":{}})
    # Ensure keys exist
    for k in ["scraped","approved","denied","sent_to_groq","pdfs_created"]:
        if k not in h["session"]: h["session"][k] = 0
        if k not in h["all_time"]: h["all_time"][k] = 0
    
    h["session"][key] += amount
    h["all_time"][key] += amount
    save_json(HISTORY_FILE, h)

# --- ROUTES ---

@app.route('/api/status')
def status():
    return jsonify(load_json(HISTORY_FILE))

@app.route('/api/jobs')
def jobs():
    # TAB LOGIC: Filter by status
    # NEW = Incoming
    # APPROVED = Staging
    # DENIED = Graveyard (includes AUTO_DENIED)
    status_filter = request.args.get('status', 'NEW')
    
    conn = get_db()
    query = """
        SELECT id, title, company, city, pay_fmt, date_posted, score, raw_json 
        FROM jobs 
        WHERE 1=1
    """
    
    if status_filter == 'NEW':
        query += " AND (status IS NULL OR status = 'NEW')"
    elif status_filter == 'APPROVED':
        query += " AND status = 'APPROVED'"
    elif status_filter == 'DENIED':
        query += " AND (status = 'DENIED' OR status = 'AUTO_DENIED')"
    
    query += " ORDER BY score DESC, date_posted ASC"
    
    try:
        rows = conn.execute(query).fetchall()
        # Recalculate score based on skills if needed (omitted for speed, uses DB score)
        out = []
        for r in rows:
            out.append({
                "id": r['id'],
                "title": r['title'],
                "company": r['company'],
                "city": r['city'],
                "pay": r['pay_fmt'],
                "freshness": r['date_posted'],
                "score": r['score']
            })
        return jsonify(out)
    except Exception as e:
        print(e)
        return jsonify([])
    finally:
        conn.close()

@app.route('/api/get_job_details')
def job_details():
    id = request.args.get('id')
    conn = get_db()
    row = conn.execute("SELECT raw_json FROM jobs WHERE id=?", (id,)).fetchone()
    conn.close()
    if not row: return jsonify({"description":"Not Found", "skills":[]})
    
    data = json.loads(row['raw_json'])
    
    # Extract Description
    desc = data.get('description', {}).get('html', '')
    if not desc: desc = data.get('description', {}).get('text', 'No Desc')
    
    # Extract Skills & Check if we have them
    my_skills = load_json(SKILLS_FILE, [])
    my_skills_lower = [s.lower() for s in my_skills]
    
    job_skills = []
    attrs = data.get('attributes', {})
    for k, v in attrs.items():
        is_claimed = v.lower() in my_skills_lower
        job_skills.append({"name": v, "claimed": is_claimed})
        
    return jsonify({"description": desc, "skills": job_skills})

@app.route('/api/approve', methods=['POST'])
def approve():
    # MOVES TO STAGING (APPROVED TAB)
    job_id = request.json['id']
    conn = get_db()
    conn.execute("UPDATE jobs SET status='APPROVED' WHERE id=?", (job_id,))
    conn.commit()
    conn.close()
    update_history('approved')
    return jsonify({"status":"approved"})

@app.route('/api/deny', methods=['POST'])
def deny():
    # MOVES TO GRAVEYARD (DENIED TAB)
    job_id = request.json['id']
    conn = get_db()
    conn.execute("UPDATE jobs SET status='DENIED' WHERE id=?", (job_id,))
    conn.commit()
    conn.close()
    update_history('denied')
    return jsonify({"status":"denied"})

@app.route('/api/blacklist', methods=['POST'])
def blacklist():
    # ADDS TO BLACKLIST AND AUTO-DENIES
    term = request.json.get('term', '').lower()
    if not term: return jsonify({"error": "No term"})
    
    # Update Blacklist File
    bl = load_json(BLACKLIST_FILE, [])
    if term not in bl:
        bl.append(term)
        save_json(BLACKLIST_FILE, bl)
    
    # Update DB to auto-deny matches
    conn = get_db()
    conn.execute(f"UPDATE jobs SET status='AUTO_DENIED' WHERE (lower(title) LIKE ? OR lower(company) LIKE ?) AND status != 'APPROVED'", (f'%{term}%', f'%{term}%'))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "blacklisted", "term": term})

@app.route('/api/harvest_tag', methods=['POST'])
def harvest_tag():
    # ADDS SKILL TO MY_SKILLS.JSON
    tag = request.json.get('tag')
    skills = load_json(SKILLS_FILE, [])
    if tag not in skills:
        skills.append(tag)
        save_json(SKILLS_FILE, skills)
        return jsonify({"status": "harvested"})
    return jsonify({"status": "exists"})

@app.route('/api/process_job', methods=['POST'])
def process_job():
    # THIS IS THE GROQ CALL
    job_id = request.json['id']
    conn = get_db()
    row = conn.execute("SELECT raw_json, title FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    
    if not row: return jsonify({"error": "Job not found"}), 404
    
    job_data = json.loads(row['raw_json'])
    
    # Load Master Resume
    try:
        with open(RESUME_FILE, 'r') as f: resume_text = f.read()
    except: return jsonify({"error": "No master resume found"}), 500
    
    # Prep Prompt
    job_desc = job_data.get('description', {}).get('text', '')
    prompt = f"""
    ROLE: Elite Resume Architect.
    TASK: Tailor the Master Resume for this specific Job.
    
    MASTER RESUME:
    {resume_text}
    
    JOB DESCRIPTION:
    {job_desc}
    
    OUTPUT: Return ONLY a JSON object with the tailored resume data.
    """
    
    # Fire Deck of Cards
    try:
        key = get_next_key()
        if not key: return jsonify({"error": "No Keys in Deck"}), 500
        
        client = Groq(api_key=key)
        completion = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        result = completion.choices[0].message.content
        
        # Save Result
        if not os.path.exists('input_json'): os.makedirs('input_json')
        sanitized_title = "".join(c for c in row['title'] if c.isalnum() or c in " -_").strip()[:50]
        filename = f"input_json/{sanitized_title}_{job_id}.json"
        
        with open(filename, 'w') as f: f.write(result)
        
        update_history('sent_to_groq')
        return jsonify({"status": "processed", "key": key[:5]})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index(): return send_from_directory('templates', 'index.html')
@app.route('/static/<path:path>')
def send_static(path): return send_from_directory('static', path)

if __name__ == "__main__":
    app.run(port=5000, debug=False)
