import os
import json
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

OUTPUT_DIR = "done"
TEMPLATE_FILE = "template.html"

def render(json_path):
    """
    Converts a JSON Resume Artifact into a PDF.
    """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 1. Load the Data
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        return False, f"JSON Load Error: {str(e)}"

    # 2. Setup Jinja Environment
    env = Environment(loader=FileSystemLoader('.'))
    try:
        template = env.get_template(TEMPLATE_FILE)
    except Exception as e:
        return False, f"Template Error: {str(e)}"

    # 3. Render HTML
    html_out = template.render(data)

    # 4. Construct Filename (Matching the JSON filename logic)
    # We expect json_path to be something like 'input_json/JobTitle_ID.json'
    base_name = os.path.splitext(os.path.basename(json_path))[0]
    pdf_filename = f"{base_name}.pdf"
    pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)

    # 5. Generate PDF
    try:
        HTML(string=html_out).write_pdf(pdf_path)
        return True, pdf_filename
    except Exception as e:
        return False, f"PDF Gen Error: {str(e)}"

if __name__ == "__main__":
    print("PDF Engine Standalone Mode. Import this module to use.")
