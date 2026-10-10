"""Email Parser Agent: extracts scope, deadlines, deliverables from client emails.

Enhanced with:
- Better name extraction (company names, email signatures)
- Date parsing with relative dates ("next Friday", "in 2 weeks")
- Technology stack detection
- Sentiment & tone analysis
- Payment term extraction
- Multi-email thread awareness
- Smart project title generation
"""

import re
from datetime import datetime, timedelta
from .base import call_llm, extract_json


# Technology keywords for auto-detection
TECH_KEYWORDS = {
    "frontend": ["react", "vue", "angular", "nextjs", "next.js", "html", "css", "tailwind", "bootstrap", "svelte", "flutter", "swift", "kotlin"],
    "backend": ["python", "django", "flask", "fastapi", "node", "express", "spring", "laravel", "rails", "golang", "rust", ".net"],
    "database": ["mysql", "postgres", "mongodb", "redis", "firebase", "supabase", "dynamodb", "sqlite"],
    "cloud": ["aws", "azure", "gcp", "docker", "kubernetes", "vercel", "netlify", "heroku", "render"],
    "mobile": ["ios", "android", "react native", "flutter", "swift", "kotlin", "expo"],
    "ai_ml": ["machine learning", "ai", "gpt", "llm", "tensorflow", "pytorch", "nlp", "computer vision", "chatbot"],
    "devops": ["ci/cd", "jenkins", "github actions", "terraform", "ansible", "monitoring"],
}

# Sentiment indicators
POSITIVE_CUES = ["excited", "looking forward", "great", "love", "impressed", "fantastic", "excellent", "wonderful", "thrilled"]
NEGATIVE_CUES = ["disappointed", "frustrated", "unhappy", "issue", "problem", "complaint", "delay", "concern", "worried"]
URGENCY_CUES = ["asap", "urgent", "immediately", "rush", "critical", "tight deadline", "top priority", "emergency", "yesterday", "right away", "as soon as possible"]

# Project type patterns
PROJECT_TYPES = {
    "Web Application": [r"web\s*app", r"website", r"web\s*platform", r"web\s*portal", r"saas", r"dashboard"],
    "Mobile App": [r"mobile\s*app", r"ios\s*app", r"android\s*app", r"cross[- ]?platform", r"native\s*app"],
    "API Development": [r"api\s*(?:development|integration|endpoint)", r"rest\s*api", r"graphql", r"microservice"],
    "E-Commerce": [r"e[- ]?commerce", r"online\s*store", r"shopping", r"marketplace", r"product\s*catalog"],
    "Data/Analytics": [r"data\s*(?:analytics|pipeline|visualization)", r"reporting", r"bi\s*tool", r"etl"],
    "UI/UX Design": [r"ui/?ux", r"design\s*(?:system|mockup|prototype)", r"figma", r"wireframe"],
    "DevOps/Infra": [r"devops", r"infrastructure", r"deployment", r"ci/?cd", r"cloud\s*migration"],
}


class EmailParserAgent:
    SYSTEM_PROMPT = """You are an expert AI assistant that extracts structured project information from freelancer client emails.
Analyze the email carefully and extract:
{
  "client_name": "name of the client or company",
  "project_title": "concise, descriptive project title (not just 'Project from X')",
  "project_type": "Web Application/Mobile App/API Development/E-Commerce/Data Analytics/UI UX Design/DevOps/Other",
  "scope": "clear description of the work required",
  "deliverables": ["list", "of", "specific", "deliverables"],
  "deadline": "YYYY-MM-DD or null if not mentioned",
  "budget": "amount mentioned or null",
  "currency": "INR/USD/EUR or null",
  "priority": "high/medium/low based on urgency cues",
  "estimated_hours": "estimated hours based on scope complexity, or null",
  "tech_stack": ["detected", "technologies"],
  "action_items": ["immediate next steps for the freelancer"],
  "red_flags": ["any concerning patterns like scope creep, unrealistic timelines"],
  "client_sentiment": "positive/neutral/cautious/demanding",
  "payment_terms": "any payment terms mentioned or null",
  "follow_up_needed": true/false,
  "suggested_reply_tone": "professional/friendly/formal"
}
Return ONLY valid JSON."""

    def parse(self, email_text: str) -> dict:
        llm_result = call_llm(self.SYSTEM_PROMPT, email_text)
        result = extract_json(llm_result)
        if result and result.get("client_name"):
            return result
        return self._rule_based_parse(email_text)

    def _rule_based_parse(self, text: str) -> dict:
        text_lower = text.lower()

        # --- Extract client name ---
        client_name = "Unknown Client"
        company_name = None
        name_patterns = [
            r'(?:from|regards|thanks|cheers|best|sincerely|warm regards)[,:\s]+([A-Z][a-z]+ (?:[A-Z][a-z]+)?)',
            r'(?:Hi|Hello|Dear)\s+.*?(?:from|at)\s+([A-Z][\w\s&]+?)[\.,\n]',
            r'^(?:From|Sender):\s*(.+?)(?:\n|<)',
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*(?:CEO|CTO|Founder|Manager|Director|Lead|Head)',
        ]
        for pat in name_patterns:
            m = re.search(pat, text)
            if m:
                client_name = m.group(1).strip()
                break

        # Company name extraction
        company_patterns = [
            r'(?:at|from|@)\s+([A-Z][\w\s&]+?(?:Inc|LLC|Ltd|Corp|Solutions|Technologies|Tech|Labs|Studio|Agency|Group|Services|Consulting)\.?)',
            r'([A-Z][\w]+(?:\s[A-Z][\w]+)*\s(?:Pvt|Private)\.?\s*(?:Ltd|Limited)\.?)',
        ]
        for pat in company_patterns:
            m = re.search(pat, text)
            if m:
                company_name = m.group(1).strip()
                break

        # --- Extract deadline with relative date support ---
        deadline = None
        date_patterns = [
            (r'(?:by|before|deadline|due|deliver\w*)\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})', "date"),
            (r'(?:by|before|deadline|due)\s+(\w+ \d{1,2},?\s*\d{4})', "date"),
            (r'(\d{4}-\d{2}-\d{2})', "iso"),
            (r'(?:within|in)\s+(\d+)\s*(?:days?)', "relative_days"),
            (r'(?:within|in)\s+(\d+)\s*(?:weeks?)', "relative_weeks"),
            (r'(?:within|in)\s+(\d+)\s*(?:months?)', "relative_months"),
            (r'(?:next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', "weekday"),
            (r'end of (?:this\s+)?(week|month|quarter|year)', "end_of"),
        ]
        for pat, dtype in date_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                if dtype == "relative_days":
                    deadline = (datetime.now() + timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")
                elif dtype == "relative_weeks":
                    deadline = (datetime.now() + timedelta(weeks=int(m.group(1)))).strftime("%Y-%m-%d")
                elif dtype == "relative_months":
                    deadline = (datetime.now() + timedelta(days=int(m.group(1)) * 30)).strftime("%Y-%m-%d")
                elif dtype == "end_of":
                    period = m.group(1).lower()
                    now = datetime.now()
                    if period == "week":
                        deadline = (now + timedelta(days=(6 - now.weekday()))).strftime("%Y-%m-%d")
                    elif period == "month":
                        if now.month == 12:
                            deadline = f"{now.year + 1}-01-01"
                        else:
                            deadline = f"{now.year}-{now.month + 1:02d}-01"
                    elif period == "quarter":
                        q_month = ((now.month - 1) // 3 + 1) * 3
                        deadline = f"{now.year}-{q_month:02d}-28"
                    elif period == "year":
                        deadline = f"{now.year}-12-31"
                else:
                    deadline = m.group(1)
                break

        # --- Priority assessment (multi-factor) ---
        urgency_score = sum(1 for w in URGENCY_CUES if w in text_lower)
        has_short_deadline = False
        if deadline:
            try:
                dl_date = datetime.strptime(deadline, "%Y-%m-%d")
                days_until = (dl_date - datetime.now()).days
                if days_until < 7:
                    has_short_deadline = True
            except ValueError:
                pass

        if urgency_score >= 2 or has_short_deadline:
            priority = "high"
        elif urgency_score == 1:
            priority = "medium"
        else:
            priority = "medium" if deadline else "low"

        # --- Budget extraction ---
        budget = None
        currency = None
        budget_patterns = [
            r'(?:budget|rate|pay|compensation|offer|price|cost|fee|quote)\s*(?:is|of|:|around|approximately|roughly|about)?\s*[\$₹€]?\s*([\d,]+(?:\.\d{2})?)\s*(?:k|K|lakh|lakhs|L|cr)?',
            r'[\$₹€]\s*([\d,]+(?:\.\d{2})?)',
            r'([\d,]+(?:\.\d{2})?)\s*(?:INR|USD|EUR|rupees?|dollars?)',
        ]
        for pat in budget_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                raw = m.group(1).replace(',', '')
                budget = float(raw)
                # Check for multipliers
                context = text[max(0, m.start()-5):m.end()+10].lower()
                if 'lakh' in context or 'l' == context[-1:]:
                    budget *= 100000
                elif 'cr' in context:
                    budget *= 10000000
                elif 'k' in context.rstrip():
                    budget *= 1000
                budget = str(int(budget))

                if "₹" in text or "inr" in text_lower or "rupee" in text_lower:
                    currency = "INR"
                elif "€" in text or "eur" in text_lower:
                    currency = "EUR"
                else:
                    currency = "USD"
                break

        # --- Deliverables extraction (enhanced) ---
        deliverables = []
        lines = text.split('\n')
        in_list = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(('-', '*', '•', '→', '▸')) or re.match(r'^\d+[\.\)]\s', stripped):
                item = re.sub(r'^[-*•→▸\d\.\)\s]+', '', stripped).strip()
                if item and len(item) > 3:
                    deliverables.append(item)
                    in_list = True
            elif in_list and stripped and not stripped.endswith(':'):
                in_list = False

        # --- Tech stack detection ---
        tech_stack = []
        for category, keywords in TECH_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    tech_stack.append(kw.capitalize() if len(kw) > 3 else kw.upper())
        tech_stack = list(set(tech_stack))

        # --- Project type detection ---
        project_type = "General"
        for ptype, patterns in PROJECT_TYPES.items():
            for pat in patterns:
                if re.search(pat, text_lower):
                    project_type = ptype
                    break
            if project_type != "General":
                break

        # --- Client sentiment ---
        pos_count = sum(1 for w in POSITIVE_CUES if w in text_lower)
        neg_count = sum(1 for w in NEGATIVE_CUES if w in text_lower)
        if neg_count > pos_count:
            sentiment = "cautious"
        elif pos_count > 1:
            sentiment = "positive"
        elif urgency_score >= 2:
            sentiment = "demanding"
        else:
            sentiment = "neutral"

        # --- Red flags (enhanced) ---
        red_flags = []
        if any(w in text_lower for w in ['scope change', 'additional feature', 'one more thing', 'also add', 'while you\'re at it']):
            red_flags.append("Possible scope creep detected — clarify if these are part of the original scope")
        if any(w in text_lower for w in ['no contract', 'skip paperwork', 'trust basis', 'handshake deal']):
            red_flags.append("No formal agreement mentioned — insist on a written contract")
        if priority == "high" and not budget:
            red_flags.append("Urgent request with no budget discussed — clarify compensation before starting")
        if any(w in text_lower for w in ['free', 'exposure', 'equity only', 'for experience', 'unpaid']):
            red_flags.append("Suggests unpaid/exposure-based work — evaluate carefully")
        if any(w in text_lower for w in ['unlimited revision', 'as many changes', 'until perfect']):
            red_flags.append("No revision limits — negotiate a cap on revisions")
        if any(w in text_lower for w in ['nda', 'non-disclosure', 'confidential']):
            red_flags.append("NDA mentioned — review terms before signing")
        word_count = len(text.split())
        if word_count < 30 and not deliverables:
            red_flags.append("Very brief email with vague scope — request a detailed brief")

        # --- Payment terms ---
        payment_terms = None
        payment_patterns = [
            (r'(?:net|payment\s+within)\s*(\d+)\s*days?', "Net {} days"),
            (r'(\d+)%?\s*(?:upfront|advance|down\s*payment)', "{}% upfront"),
            (r'milestone[- ]?based', "Milestone-based payments"),
            (r'(?:upon|after|on)\s+(?:completion|delivery)', "Payment on completion"),
            (r'(?:monthly|weekly|bi-weekly)\s+(?:payment|billing|invoice)', "Recurring billing"),
        ]
        for pat, fmt in payment_patterns:
            m = re.search(pat, text_lower)
            if m:
                try:
                    payment_terms = fmt.format(m.group(1))
                except (IndexError, KeyError):
                    payment_terms = fmt
                break

        # --- Scope from first substantial paragraph ---
        scope = ""
        for line in lines:
            stripped = line.strip()
            if len(stripped) > 40 and not stripped.startswith(('Hi', 'Hello', 'Dear', 'From', 'Subject', 'To:', 'Date:', 'Cc:')):
                scope = stripped[:300]
                break

        # --- Smart project title ---
        if project_type != "General":
            title = f"{project_type}"
            if company_name:
                title += f" for {company_name}"
            elif client_name != "Unknown Client":
                title += f" for {client_name}"
        else:
            title = f"Project from {company_name or client_name}"

        # --- Estimated hours (rough heuristic) ---
        estimated_hours = None
        hours_match = re.search(r'(\d+)\s*(?:hours?|hrs?)', text, re.IGNORECASE)
        if hours_match:
            estimated_hours = int(hours_match.group(1))
        elif budget:
            # Rough estimate: ₹1500/hr for INR, $50/hr for USD
            rate = 1500 if currency == "INR" else 50
            estimated_hours = round(float(budget) / rate)

        # --- Action items ---
        action_items = ["Review scope and confirm feasibility"]
        if not budget:
            action_items.append("Discuss budget and payment terms")
        if not deadline:
            action_items.append("Agree on a timeline and milestones")
        if deliverables:
            action_items.append("Confirm deliverables list and acceptance criteria")
        else:
            action_items.append("Request detailed requirements document")
        if tech_stack:
            action_items.append("Verify tech stack compatibility and setup dev environment")
        action_items.append("Send acknowledgment and availability to client")
        if priority == "high":
            action_items.insert(0, "⚡ URGENT: Respond within 2-4 hours")

        return {
            "client_name": company_name or client_name,
            "project_title": title,
            "project_type": project_type,
            "scope": scope or "See email for details — request a detailed brief",
            "deliverables": deliverables or ["Review email and request specifics"],
            "deadline": deadline,
            "budget": budget,
            "currency": currency,
            "priority": priority,
            "estimated_hours": estimated_hours,
            "tech_stack": tech_stack[:8],
            "action_items": action_items,
            "red_flags": red_flags,
            "client_sentiment": sentiment,
            "payment_terms": payment_terms,
            "follow_up_needed": bool(not budget or not deadline or not deliverables),
            "suggested_reply_tone": "formal" if sentiment == "demanding" else "friendly" if sentiment == "positive" else "professional",
        }
