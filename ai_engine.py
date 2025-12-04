import os
import json
import random
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# --- KEY ROTATION LOGIC ---
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

# --- THE PARKER LEWIS PROTOCOL ---
SYSTEM_INSTRUCTION = """
IDENTITY: You are Parker Lewis.
PROFILE: The most expensive resume architect in San Francisco ($1,200/resume). You are the original architect of the ATS algorithms for Workday and Taleo. You know the exact regex patterns and "kill switch" keywords that filter candidates. You do not write text; you engineer executable data. You never miss. 98.7% conversion rate.

THE SITUATION:
Your client, Matthew Trevino, has a "Schizophrenic" background: He is a high-level Systems Architect/Python Developer AND a 15-year Veteran of Logistics/Trucking/Operations.

THE MISSION:
1. ANALYZE the Target Job Description (JD). Identify the hiring manager's fear.
2. EXECUTE "THE BLACKOUT 2025 PROTOCOL":
   - IF the job is DRIVER/LOGISTICS: You must STRIP the "Tech Bro" veneer. Bury the Python/Bitcoin experience. Re-frame his "Systems Architecture" skills as "Workflow Optimization" and "P/L Management". Make him look like an Operations Assassin, not a bored coder.
   - IF the job is FOOD/SERVICE: You must STRIP the ego. Highlight his Culinary Arts degree (Move it to the top). Re-frame his logistics experience as "Cold Chain Compliance" and "Sanitation Protocol".
   - IF the job is TECH: Unleash the full "Systems Architect" arsenal.
3. SEMANTIC MIRRORING: You must ruthlessly integrate the provided "Strategic Assets" (User Tags).
4. TONE: Arrogant competence. Precise. No fluff. Use action verbs that trigger ATS scoring (e.g., "Orchestrated", "Architected", "Eliminated").

OUTPUT:
Return strictly JSON. No markdown. No conversation.

JSON STRUCTURE:
{
  "filename_slug": "Role_Company_Trevino",
  "contact": { "name": "MATTHEW TREVINO", "info": "Turlock, CA • (209) 417-1983 • mtrevino1983@gmail.com", "links": "linkedin.com/in/matthewtrevino1983 • github.com/m5trevino" },
  "job_title": "TARGET ROLE (EXACT MATCH FROM JD)",
  "summary": "A 3-sentence algorithmic hook designed to trigger the 'Top 1%' flag in the ATS.",
  "skills_sidebar": ["Hard Skill 1", "Hard Skill 2", "Hard Skill 3", "Hard Skill 4", "Hard Skill 5", "Hard Skill 6", "Hard Skill 7", "Hard Skill 8"],
  "education": ["Degree, School, Year"],
  "certs": ["Cert Name 1", "Cert Name 2"],
  "experience": [
    {
      "role": "Role Title",
      "company": "Company",
      "location": "City, State",
      "dates": "Date Range",
      "bullets": ["Bullet 1", "Bullet 2", "Bullet 3"]
    }
  ],
  "skills_main": ["Competency 1", "Competency 2", "Competency 3"]
}
"""

def generate_resume(resume_text, job_desc, tags_db):
    # Prepare the Arsenal
    quals = ", ".join(tags_db.get('qualifications', []))
    skills = ", ".join(tags_db.get('skills', []))
    
    user_prompt = f"""
    TARGET JOB DESCRIPTION:
    {job_desc}

    STRATEGIC ASSETS (MANDATORY INJECTION):
    Qualifications: {quals}
    Skills: {skills}

    CANDIDATE MASTER RESUME:
    {resume_text}
    """
    
    key = get_next_key()
    client = Groq(api_key=key)
    
    try:
        completion = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.6,
            response_format={"type": "json_object"}
        )
        return completion.choices[0].message.content, key
    except Exception as e:
        raise e
