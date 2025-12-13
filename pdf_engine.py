import os
import json
import sqlite3
import jinja2
import sys

# --- CONFIG ---
DB_FILE = 'jobs.db'
TEMPLATE_FILE = 'template.html'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def sanitize_filename(text):
    return "".join(c for c in text if c.isalnum() or c in " -_").strip()[:50]

def get_job_data(job_id):
    """Fetches path AND metadata from DB"""
    conn = get_db()
    row = conn.execute("SELECT title, company FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    
    if not row: return None, None, None, None
    
    safe_title = sanitize_filename(row['title'])
    safe_company = sanitize_filename(row['company'])
    path = f"targets/{safe_title}_{safe_company}_{job_id}"
    
    return path, f"{safe_title}_{safe_company}_{job_id}", row['title'], row['company']

def generate_pdf(job_id):
    print(f"[*] PDF ENGINE: Engaging for Job ID {job_id}...")
    
    # 0. Check Dependencies
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        return {"status": "error", "message": "CRITICAL: 'weasyprint' not installed."}

    # 1. Locate Artifacts & DB Metadata
    t_dir, dir_name, real_title, real_company = get_job_data(job_id)
    
    if not t_dir or not os.path.exists(t_dir):
        return {"status": "error", "message": "Target directory not found."}
        
    json_path = os.path.join(t_dir, "resume.json")
    pdf_path = os.path.join(t_dir, "resume.pdf")
    
    if not os.path.exists(json_path):
        return {"status": "error", "message": "resume.json artifact missing. Run AI Strike first."}
        
    # 2. Load JSON Data
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"JSON Corrupt: {str(e)}"}

    # 3. Load Template
    if not os.path.exists(TEMPLATE_FILE):
        return {"status": "error", "message": "template.html missing."}
        
    template_loader = jinja2.FileSystemLoader(searchpath="./")
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template(TEMPLATE_FILE)

    # 4. DATA INJECTION (THE FIX)
    # We FORCE the real title from the database, ignoring the AI or Fallback.
    data['job_title'] = real_title.upper() if real_title else "PROFESSIONAL TARGET"

    # 5. Render HTML
    try:
        html_string = template.render(**data)
    except Exception as e:
         return {"status": "error", "message": f"Jinja2 Render Error: {str(e)}"}

    # 6. Write PDF
    try:
        HTML(string=html_string, base_url='.').write_pdf(pdf_path)
        print(f"[*] PDF GENERATED: {pdf_path}")
        return {"status": "success", "path": f"/done/{dir_name}/resume.pdf"}
        
    except Exception as e:
        print(f"[!] WeasyPrint Error: {e}")
        return {"status": "error", "message": f"PDF Generation Failed: {str(e)}"}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(generate_pdf(sys.argv[1]))
    else:
        print("Usage: python pdf_engine.py <job_id>")
