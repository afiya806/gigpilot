# GigPilot - AI-Powered Freelancer Copilot

> Your AI back-office that handles the boring stuff so you can focus on the work.

GigPilot is a multi-agent AI system built for freelancers. It replaces scattered spreadsheets, manual invoicing, and contract anxiety with five specialized AI agents that work together as your virtual back-office assistant.

Built for **HackNowa Global Hackathon 2026** | Problem Statement 5: Future of Work & Automation

## The Problem

Indian freelancers spend 30-40% of their time on non-billable admin work: chasing payments, calculating GST, decoding client emails, reviewing contracts, and tracking deadlines across WhatsApp messages and email threads. This is time they could spend doing actual paid work.

## The Solution

GigPilot deploys five specialized AI agents that automate the entire freelancer back-office:

### 1. Email Parser Agent
Paste a client email. The AI extracts project scope, deliverables, deadlines, budget, and flags red flags like scope creep or missing payment terms. One click adds it to your project dashboard.

### 2. Invoice Generator
Create GST-compliant invoices with CGST/SGST/IGST breakdowns, HSN/SAC codes, and bank details. Downloads as professional PDF. Supports INR, USD, EUR.

### 3. Contract Red-Flag Scanner
Paste any freelance contract. The AI scans for unfavorable clauses (non-competes, unlimited liability, IP assignment without compensation, unilateral termination) and suggests negotiation points.

### 4. Tax Helper
Calculates advance tax liability under both New and Old tax regimes. Shows quarterly payment schedule, TDS tracking, presumptive taxation (44ADA) eligibility, and personalized tax-saving tips.

### 5. Deadline Dashboard
Central command for all active projects. Tracks deadlines, flags overdue work, logs hours, and shows revenue pipeline at a glance.

## Tech Stack

- **Backend**: Python, FastAPI
- **AI**: Multi-agent architecture with Claude API (falls back to rule-based heuristics)
- **PDF Generation**: ReportLab (GST-compliant invoices)
- **Frontend**: Jinja2 templates, Tailwind CSS
- **Deployment**: Docker, Render/Railway ready

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/gigpilot.git
cd gigpilot

# Install dependencies
pip install -r requirements.txt

# Run
python main.py

# Open http://localhost:8000
```

### With Docker

```bash
docker build -t gigpilot .
docker run -p 8000:8000 gigpilot
```

### Environment Variables (Optional)

```
ANTHROPIC_API_KEY=sk-ant-...  # Enables Claude AI for smarter parsing (optional, falls back to rule-based)
PORT=8000
```

## Architecture

```
gigpilot/
  agents/
    base.py              # LLM integration + fallback logic
    email_parser.py      # NLP extraction from client emails
    invoice_generator.py # GST-compliant PDF generation
    contract_scanner.py  # Red-flag pattern matching + AI analysis
    tax_estimator.py     # Indian tax computation engine
    deadline_tracker.py  # Project and deadline management
  templates/             # Jinja2 HTML templates with Tailwind
  static/                # CSS/JS assets
  main.py                # FastAPI application
  Dockerfile             # Container deployment
  render.yaml            # Render.com deployment config
```

## Key Design Decisions

1. **Hybrid AI**: Every agent works with AND without an API key. Rule-based fallbacks mean the app is fully functional even without LLM access. When Claude API is available, parsing quality jumps significantly.

2. **India-first**: GST calculations (CGST/SGST/IGST), Indian tax slabs (FY 2025-26), Section 44ADA presumptive taxation, TDS rates under 194J/194C. Built for the 24M+ Indian freelancers.

3. **Agent Architecture**: Each agent is self-contained with its own system prompt, extraction logic, and output schema. Agents communicate through the dashboard (email parser feeds into deadline tracker).

4. **Zero-config deployment**: No database setup required. File-based storage for project data. Single `pip install` and run.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/parse-email` | POST | Parse client email, extract structured data |
| `/api/generate-invoice` | POST | Generate GST-compliant PDF invoice |
| `/api/scan-contract` | POST | Scan contract for red flags |
| `/api/estimate-tax` | POST | Calculate tax liability |
| `/api/projects` | GET/POST | Manage projects |
| `/api/dashboard` | GET | Get dashboard data |
| `/api/health` | GET | Health check |

## License

MIT
