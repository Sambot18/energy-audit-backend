from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import fitz
import os
import json
import io
import google.generativeai as genai
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)
CORS(app)

# ---------------- GEMINI ----------------
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

# ---------------- PDF TEXT ----------------
def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    return "".join(page.get_text() for page in doc)

# ---------------- AI ANALYSIS ----------------
def analyze_report(text, lang="en"):
    prompt = f"""
Summarize this energy audit report for non-experts in {lang}.
Return ONLY valid JSON:

{{
  "summary": "simple summary",
  "attention": [
    {{"area":"HVAC","issue":"problem","priority":"High"}}
  ],
  "graph": {{
    "Lighting": number,
    "HVAC": number,
    "Insulation": number,
    "Equipment": number
  }}
}}

Report:
{text}
"""
    res = model.generate_content(prompt).text
    res = res.replace("```json", "").replace("```", "")
    return json.loads(res)

# ---------------- PROCESS API ----------------
@app.route("/process", methods=["POST"])
def process_pdf():
    file = request.files.get("file")
    lang = request.form.get("lang", "en")

    if not file or not file.filename.endswith(".pdf"):
        return jsonify({"error": "PDF required"}), 400

    text = extract_text_from_pdf(file)
    data = analyze_report(text, "Hindi" if lang == "hi" else "English")
    return jsonify(data)

# ---------------- DOWNLOAD REPORT PDF ----------------
@app.route("/download", methods=["POST"])
def download_report():
    data = request.json

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Energy Audit Summary Report")
    y -= 30

    c.setFont("Helvetica", 11)
    c.drawString(40, y, data["summary"])
    y -= 40

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Areas Needing Attention:")
    y -= 20

    c.setFont("Helvetica", 10)
    for a in data["attention"]:
        c.drawString(40, y, f"- {a['area']} ({a['priority']}): {a['issue']}")
        y -= 15

    c.showPage()
    c.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="energy_audit_report.pdf")

# ---------------- RENDER ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
