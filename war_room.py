import os
import json
import time
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

# --- CONFIGURATION ---
INPUT_DIR = "input_json"
OUTPUT_DIR = "done"
TEMPLATE_FILE = "template.html"

def setup_directories():
    if not os.path.exists(INPUT_DIR): os.makedirs(INPUT_DIR)
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

def render_resume(data, output_filename):
    # Setup Jinja2
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(TEMPLATE_FILE)
    
    # Render HTML
    html_out = template.render(data)
    
    # Define Output Path
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    pdf_path = os.path.join(OUTPUT_DIR, output_filename)
    
    # Generate PDF
    HTML(string=html_out).write_pdf(pdf_path)
    return pdf_path

# --- SERVER HOOK ---
def convert_to_pdf(json_path, pdf_filename):
    """
    Called by server.py to immediately generate a PDF.
    """
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Inject standard filename if missing
        if 'filename_slug' not in data:
            data['filename_slug'] = "resume"
            
        render_resume(data, pdf_filename)
        return True
    except Exception as e:
        print(f"PDF GENERATION ERROR: {e}")
        return False

# --- CLI MODE (Legacy/Batch) ---
if __name__ == "__main__":
    # Keep existing CLI logic if you run python war_room.py manually
    from rich.console import Console
    console = Console()
    setup_directories()
    console.print("[bold green]Running Manual Batch PDF Generation...[/]")
    
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.json')]
    for f in files:
        base = os.path.splitext(f)[0]
        json_p = os.path.join(INPUT_DIR, f)
        pdf_n = f"{base}.pdf"
        convert_to_pdf(json_p, pdf_n)
        console.print(f"[green]Generated: {pdf_n}[/]")
