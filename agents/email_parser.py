"""Email Parser Agent: extracts scope, deadlines, deliverables from client emails."""

import re
from datetime import datetime, timedelta
from .base import call_llm, extract_json


class EmailParserAgent:
    SYSTEM_PROMPT = """You are an AI assistant that extracts structured project information from freelancer client emails.
Extract the following fields as JSON:
{
  "client_name": "name of the client or company",
  "project_title": "short project title",
  "scope": "brief description of the work",
  "deliverables": ["list", "of", "deliverables"],
  "deadline": "YYYY-MM-DD or null if not mentioned",
  "budget": "amount mentioned or null",
  "currency": "INR/USD/EUR or null",
  "priority": "high/medium/low based on urgency cues",
  "action_items": ["immediate next steps for the freelancer"],
  "red_flags": ["any concerning patterns like scope creep, unrealistic timelines"]
}
Return ONLY valid JSON."""

    def parse(self, email_text: str) -> dict:
        llm_result = call_llm(self.SYSTEM_PROMPT, email_text)
        result = extract_json(llm_result)
        if result:
            return result
        return self._rule_based_parse(email_text)

    def _rule_based_parse(self, text: str) -> dict:
        text_lower = text.lower()

        # Extract client name from greeting or signature
        client_name = "Unknown Client"
        name_patterns = [
            r'(?:from|regards|thanks|cheers)[,:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
            r'(?:Hi|Hello|Dear)\s+.*?(?:from|at)\s+([A-Z][\w\s]+?)[\.,\n]',
        ]
        for pat in name_patterns:
            m = re.search(pat, text)
            if m:
                client_name = m.group(1).strip()
                break

        # Extract deadline
        deadline = None
        date_patterns = [
            r'(?:by|before|deadline|due|deliver\w*)\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'(?:by|before|deadline|due)\s+(\w+ \d{1,2},?\s*\d{4})',
            r'(\d{4}-\d{2}-\d{2})',
        ]
        for pat in date_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                deadline = m.group(1)
                break

        # Urgency keywords
        urgent_words = ['asap', 'urgent', 'immediately', 'rush', 'critical', 'tight deadline']
        priority = "high" if any(w in text_lower for w in urgent_words) else "medium"

        # Budget
        budget = None
        currency = None
        budget_match = re.search(r'(?:budget|rate|pay|compensation|offer)\s*(?:is|of|:)?\s*[\$₹]?\s*([\d,]+)', text, re.IGNORECASE)
        if budget_match:
            budget = budget_match.group(1).replace(',', '')
            currency = "INR" if "₹" in text or "inr" in text_lower or "rupee" in text_lower else "USD"

        # Deliverables
        deliverables = []
        lines = text.split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(('-', '*', '•')) or re.match(r'^\d+[\.\)]\s', stripped):
                item = re.sub(r'^[-*•\d\.\)\s]+', '', stripped).strip()
                if item and len(item) > 3:
                    deliverables.append(item)

        # Red flags
        red_flags = []
        if any(w in text_lower for w in ['scope change', 'additional feature', 'one more thing', 'also add']):
            red_flags.append("Possible scope creep detected")
        if any(w in text_lower for w in ['no contract', 'skip paperwork', 'trust basis']):
            red_flags.append("No formal agreement mentioned")
        if priority == "high" and not budget:
            red_flags.append("Urgent request with no budget mentioned")

        # Scope from first substantial paragraph
        scope = ""
        for line in lines:
            stripped = line.strip()
            if len(stripped) > 40 and not stripped.startswith(('Hi', 'Hello', 'Dear', 'From', 'Subject')):
                scope = stripped[:200]
                break

        return {
            "client_name": client_name,
            "project_title": f"Project from {client_name}",
            "scope": scope or "See email for details",
            "deliverables": deliverables or ["Review email for specifics"],
            "deadline": deadline,
            "budget": budget,
            "currency": currency,
            "priority": priority,
            "action_items": ["Review scope and confirm feasibility", "Send acknowledgment to client"],
            "red_flags": red_flags,
        }
