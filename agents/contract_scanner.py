"""Contract Scanner Agent: highlights unfavorable clauses and red flags."""

import re
from .base import call_llm, extract_json


RED_FLAG_PATTERNS = {
    "Non-compete clause": [
        r'non[- ]?compet(?:e|ition)',
        r'shall not (?:work|engage|provide services).*(?:competitor|similar)',
    ],
    "IP assignment without compensation": [
        r'(?:all|any) (?:intellectual property|IP|work product).*(?:belong|assign|transfer).*(?:client|company)',
        r'work[- ]?(?:for[- ]?hire|made for hire)',
    ],
    "Unlimited liability": [
        r'unlimited liability',
        r'liable for (?:all|any and all) (?:damages|losses)',
        r'indemnif(?:y|ication).*(?:all|any) (?:claims|losses|damages)',
    ],
    "No payment terms": [
        r'payment.*(?:upon|after) (?:completion|delivery|acceptance)',
    ],
    "Auto-renewal trap": [
        r'auto(?:matic(?:ally)?)?[- ]?renew',
        r'(?:shall|will) (?:automatically )?(?:renew|extend)',
    ],
    "Unilateral termination": [
        r'(?:client|company) may terminate.*(?:at any time|without cause|without reason|for convenience)',
        r'terminate.*(?:immediately|without notice).*(?:sole discretion)',
    ],
    "Scope creep enabler": [
        r'(?:additional|other) (?:tasks|work|services).*(?:as (?:needed|required|requested))',
        r'(?:reasonable|related) (?:additional )?(?:tasks|duties|responsibilities)',
    ],
    "Late payment no penalty": [
        r'no (?:interest|penalty|late fee)',
    ],
    "Confidentiality over-reach": [
        r'confidential(?:ity)?.*(?:perpetual|indefinite|survive.*termination)',
        r'(?:shall not|may not) disclose.*(?:existence|terms).*(?:agreement|contract)',
    ],
    "Jurisdiction risk": [
        r'(?:governed by|jurisdiction of|laws of).*(?:foreign|international)',
    ],
}

FAVORABLE_PATTERNS = {
    "Payment milestones defined": [
        r'(?:milestone|phase|installment).*(?:payment|paid)',
        r'(?:advance|upfront).*(?:payment|\d+%)',
    ],
    "Termination rights": [
        r'(?:either|both) part(?:y|ies) may terminate',
        r'freelancer.*(?:may|right to).*terminate',
    ],
    "Late payment penalty": [
        r'(?:interest|penalty|late fee).*(?:overdue|late|delayed)',
        r'(?:\d+%|percent).*(?:per month|monthly).*(?:late|overdue)',
    ],
    "Scope clearly defined": [
        r'(?:scope of work|deliverables|specifications).*(?:set forth|described|listed)',
    ],
    "Revision limits": [
        r'(?:revision|change|modification).*(?:limit|maximum|up to \d+)',
    ],
}


class ContractScannerAgent:

    SYSTEM_PROMPT = """You are a contract analysis AI for freelancers. Analyze the contract and return JSON:
{
  "red_flags": [
    {"clause": "exact quote from contract", "issue": "why this is problematic", "severity": "high/medium/low", "suggestion": "what to negotiate"}
  ],
  "favorable_terms": [
    {"clause": "exact quote", "reason": "why this is good"}
  ],
  "missing_clauses": ["list of important clauses not found in the contract"],
  "overall_risk": "high/medium/low",
  "summary": "2-3 sentence summary of key findings"
}
Focus on: payment terms, IP rights, liability, termination, scope, confidentiality, non-compete, revision limits.
Return ONLY valid JSON."""

    def scan(self, contract_text: str) -> dict:
        llm_result = call_llm(self.SYSTEM_PROMPT, contract_text)
        result = extract_json(llm_result)
        if result and result.get("red_flags"):
            return result
        return self._rule_based_scan(contract_text)

    def _rule_based_scan(self, text: str) -> dict:
        text_lower = text.lower()

        red_flags = []
        for flag_name, patterns in RED_FLAG_PATTERNS.items():
            for pat in patterns:
                matches = re.finditer(pat, text_lower)
                for m in matches:
                    start = max(0, m.start() - 50)
                    end = min(len(text), m.end() + 50)
                    context = text[start:end].strip()
                    red_flags.append({
                        "clause": context,
                        "issue": flag_name,
                        "severity": "high" if flag_name in [
                            "Unlimited liability", "IP assignment without compensation",
                            "Unilateral termination"
                        ] else "medium",
                        "suggestion": self._get_suggestion(flag_name),
                    })
                    break

        favorable = []
        for term_name, patterns in FAVORABLE_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, text_lower):
                    favorable.append({"clause": term_name, "reason": f"Contract includes {term_name.lower()}"})
                    break

        # Check missing clauses
        missing = []
        essential = {
            "Payment terms": r'(?:payment|compensation|fee|rate)',
            "Termination clause": r'terminat(?:e|ion)',
            "Confidentiality": r'confidential',
            "Liability limitation": r'(?:liability|indemnif)',
            "Dispute resolution": r'(?:dispute|arbitrat|mediat)',
            "Revision/change policy": r'(?:revision|change order|amendment)',
        }
        for clause_name, pat in essential.items():
            if not re.search(pat, text_lower):
                missing.append(clause_name)

        high_count = sum(1 for f in red_flags if f["severity"] == "high")
        overall_risk = "high" if high_count >= 2 else "medium" if red_flags else "low"

        return {
            "red_flags": red_flags,
            "favorable_terms": favorable,
            "missing_clauses": missing,
            "overall_risk": overall_risk,
            "summary": f"Found {len(red_flags)} red flag(s) and {len(favorable)} favorable term(s). "
                       f"{len(missing)} important clause(s) appear to be missing. "
                       f"Overall risk level: {overall_risk}.",
        }

    def _get_suggestion(self, flag: str) -> str:
        suggestions = {
            "Non-compete clause": "Negotiate to limit scope, geography, and duration. 6 months max is reasonable.",
            "IP assignment without compensation": "Ensure IP transfers only after full payment. Retain portfolio rights.",
            "Unlimited liability": "Cap liability at the total contract value. Add professional indemnity clause.",
            "No payment terms": "Request milestone-based payments with at least 25-50% upfront.",
            "Auto-renewal trap": "Add a notification requirement 30 days before renewal. Request opt-in instead.",
            "Unilateral termination": "Make termination mutual. Add a 15-30 day notice period and kill fee.",
            "Scope creep enabler": "Define scope precisely. Add a change order process with separate pricing.",
            "Late payment no penalty": "Add 1.5-2% monthly interest on overdue payments.",
            "Confidentiality over-reach": "Limit to 2 years post-termination. Exclude publicly available information.",
            "Jurisdiction risk": "Negotiate for your local jurisdiction or neutral arbitration.",
        }
        return suggestions.get(flag, "Review this clause with a legal professional.")
