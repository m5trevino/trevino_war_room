import sqlite3
import os
import json

DB_FILE = 'jobs.db'

def unstick():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get all jobs
    jobs = c.execute("SELECT id, title, company FROM jobs").fetchall()
    count = 0
    
    for job in jobs:
        # Reconstruct path
        safe_title = "".join(x for x in job['title'] if x.isalnum() or x in " -_").strip()[:50]
        safe_company = "".join(x for x in job['company'] if x.isalnum() or x in " -_").strip()[:50]
        path = f"targets/{safe_title}_{safe_company}_{job['id']}/resume.json"
        
        # If resume.json exists, FORCE status to DELIVERED
        if os.path.exists(path):
            c.execute("UPDATE jobs SET status='DELIVERED' WHERE id=?", (job['id'],))
            count += 1
            print(f"MOVED TO ARMORY: {job['title']}")

    conn.commit()
    conn.close()
    print(f"--- RECOVERY COMPLETE: {count} jobs moved to Armory ---")

if __name__ == "__main__":
    unstick()
