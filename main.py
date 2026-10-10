"""GigPilot: AI-Powered Freelancer Copilot - FastAPI Backend

5 AI Agents:
1. Email Parser — extracts scope, budget, deadlines from client emails
2. Invoice Generator — GST-compliant Indian invoice PDFs
3. Contract Scanner — red flag detection with risk scoring
4. Tax Estimator — advance tax, regime comparison, GST check
5. Deadline Tracker — project management with workload analytics
"""

import os
import json
import base64
from datetime import datetime
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from agents.email_parser import EmailParserAgent
from agents.invoice_generator import InvoiceGeneratorAgent
from agents.contract_scanner import ContractScannerAgent
from agents.tax_estimator import TaxEstimatorAgent
from agents.deadline_tracker import DeadlineTrackerAgent

app = FastAPI(
    title="GigPilot",
    description="AI-Powered Freelancer Back-Office Copilot — 5 specialized AI agents for Indian freelancers",
    version="2.0.0",
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def indian_number(value):
    """Format number with Indian lakh/crore grouping: 6,65,000 instead of 665,000."""
    try:
        value = int(float(value))
    except (ValueError, TypeError):
        return str(value)
    if value < 0:
        return "-" + indian_number(-value)
    s = str(value)
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    # Group the remaining digits in pairs from right
    groups = []
    while rest:
        groups.append(rest[-2:])
        rest = rest[:-2]
    groups.reverse()
    return ",".join(groups) + "," + last3


templates.env.filters["indian_number"] = indian_number


def format_date_indian(value):
    """Format YYYY-MM-DD to DD Mon YYYY (e.g., 15 Oct 2026)."""
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(str(value).split("T")[0])
        return dt.strftime("%d %b %Y")
    except (ValueError, TypeError):
        return str(value)


templates.env.filters["indian_date"] = format_date_indian

# Initialize agents
email_agent = EmailParserAgent()
invoice_agent = InvoiceGeneratorAgent()
contract_agent = ContractScannerAgent()
tax_agent = TaxEstimatorAgent()
deadline_agent = DeadlineTrackerAgent()


# ============ Pages ============

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    dash_data = deadline_agent.get_dashboard()
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request, "dashboard": dash_data})


@app.get("/email-parser", response_class=HTMLResponse)
async def email_parser_page(request: Request):
    return templates.TemplateResponse(request=request, name="email_parser.html", context={"request": request})


@app.get("/invoices", response_class=HTMLResponse)
async def invoices_page(request: Request):
    template = invoice_agent.get_template()
    return templates.TemplateResponse(request=request, name="invoices.html", context={"request": request, "template": template})


@app.get("/contracts", response_class=HTMLResponse)
async def contracts_page(request: Request):
    return templates.TemplateResponse(request=request, name="contracts.html", context={"request": request})


@app.get("/tax", response_class=HTMLResponse)
async def tax_page(request: Request):
    return templates.TemplateResponse(request=request, name="tax.html", context={"request": request})


# ============ API Endpoints ============

@app.post("/api/parse-email")
async def parse_email(request: Request):
    body = await request.json()
    email_text = body.get("email_text", "")
    if not email_text.strip():
        return JSONResponse({"error": "Email text is required"}, status_code=400)
    result = email_agent.parse(email_text)
    return JSONResponse(result)


@app.post("/api/generate-invoice")
async def generate_invoice(request: Request):
    data = await request.json()
    pdf_bytes = invoice_agent.generate(data)
    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    return JSONResponse({"pdf_base64": b64, "filename": f"invoice_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"})


@app.post("/api/scan-contract")
async def scan_contract(request: Request):
    body = await request.json()
    contract_text = body.get("contract_text", "")
    if not contract_text.strip():
        return JSONResponse({"error": "Contract text is required"}, status_code=400)
    result = contract_agent.scan(contract_text)
    return JSONResponse(result)


@app.post("/api/estimate-tax")
async def estimate_tax(request: Request):
    data = await request.json()
    result = tax_agent.estimate(data)
    return JSONResponse(result)


@app.post("/api/projects")
async def add_project(request: Request):
    data = await request.json()
    project = deadline_agent.add_project(data)
    return JSONResponse(project)


@app.get("/api/dashboard")
async def get_dashboard():
    return JSONResponse(deadline_agent.get_dashboard())


@app.put("/api/projects/{project_id}")
async def update_project(project_id: int, request: Request):
    data = await request.json()
    result = deadline_agent.update_project(project_id, data)
    return JSONResponse(result)


@app.post("/api/projects/{project_id}/log-hours")
async def log_hours(project_id: int, request: Request):
    data = await request.json()
    hours = float(data.get("hours", 0))
    result = deadline_agent.log_hours(project_id, hours)
    return JSONResponse(result)


# ============ NEW: Inter-Agent Features ============

@app.post("/api/email-to-project")
async def email_to_project(request: Request):
    """Parse an email AND auto-create a project from it (Email Agent → Deadline Agent)."""
    body = await request.json()
    email_text = body.get("email_text", "")
    if not email_text.strip():
        return JSONResponse({"error": "Email text is required"}, status_code=400)

    # Step 1: Parse the email
    parsed = email_agent.parse(email_text)

    # Step 2: Create a project from parsed data
    project_data = {
        "client": parsed.get("client_name", "Unknown"),
        "title": parsed.get("project_title", "New Project"),
        "status": "active",
        "deadline": parsed.get("deadline", ""),
        "budget": float(parsed.get("budget", 0) or 0),
        "currency": parsed.get("currency", "INR"),
        "hours_estimated": float(parsed.get("estimated_hours", 0) or 0),
        "hours_logged": 0,
        "deliverables": parsed.get("deliverables", []),
        "priority": parsed.get("priority", "medium"),
        "notes": f"Auto-created from email. Scope: {parsed.get('scope', 'N/A')}",
    }
    project = deadline_agent.add_project(project_data)

    return JSONResponse({
        "parsed_email": parsed,
        "created_project": project,
        "message": f"Project '{project['title']}' created successfully from email",
    })


@app.get("/api/analytics")
async def get_analytics():
    """Detailed analytics from the Deadline Tracker Agent."""
    return JSONResponse(deadline_agent.get_analytics())


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: int):
    """Delete a project by marking it as cancelled."""
    result = deadline_agent.update_project(project_id, {"status": "cancelled"})
    return JSONResponse(result)


@app.post("/api/projects/{project_id}/complete")
async def complete_project(project_id: int):
    """Mark a project as completed."""
    result = deadline_agent.update_project(project_id, {"status": "completed"})
    return JSONResponse(result)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "GigPilot",
        "version": "2.0.0",
        "agents": {
            "email_parser": "active",
            "invoice_generator": "active",
            "contract_scanner": "active",
            "tax_estimator": "active",
            "deadline_tracker": "active",
        },
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
