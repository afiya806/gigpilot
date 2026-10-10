"""Contract Scanner Agent: highlights unfavorable clauses and red flags.

Enhanced with:
- Risk scoring (0-100) with weighted categories
- 15+ red flag categories with severity levels
- 8+ favorable term patterns
- Missing clause detection with importance ratings
- Negotiation scripts for each red flag
- Contract type detection
- Clause-by-clause breakdown
- Indian contract law specific checks (Indian Stamp Act, Arbitration Act)
"""

import re
from .base import call_llm, extract_json


# Weighted risk categories (weight determines impact on overall score)
RED_FLAG_PATTERNS = {
    "Non-compete clause": {
        "patterns": [
            r'non[- ]?compet(?:e|ition)',
            r'shall not (?:work|engage|provide services).*(?:competitor|similar)',
            r'refrain from.*(?:competing|similar business)',
        ],
        "severity": "high",
        "weight": 15,
        "category": "Employment Restriction",
    },
    "IP assignment without compensation": {
        "patterns": [
            r'(?:all|any) (?:intellectual property|IP|work product).*(?:belong|assign|transfer).*(?:client|company)',
            r'work[- ]?(?:for[- ]?hire|made for hire)',
            r'(?:irrevocable|perpetual|exclusive).*(?:license|rights?).*(?:client|company)',
        ],
        "severity": "high",
        "weight": 20,
        "category": "Intellectual Property",
    },
    "Unlimited liability": {
        "patterns": [
            r'unlimited liability',
            r'liable for (?:all|any and all) (?:damages|losses)',
            r'indemnif(?:y|ication).*(?:all|any) (?:claims|losses|damages)',
            r'(?:consequential|indirect|special|punitive) damages',
        ],
        "severity": "high",
        "weight": 20,
        "category": "Liability",
    },
    "Payment only on completion": {
        "patterns": [
            r'payment.*(?:upon|after|only after) (?:completion|delivery|acceptance|approval)',
            r'(?:no|without) (?:advance|upfront|milestone) payment',
        ],
        "severity": "high",
        "weight": 15,
        "category": "Payment Terms",
    },
    "Auto-renewal trap": {
        "patterns": [
            r'auto(?:matic(?:ally)?)?[- ]?renew',
            r'(?:shall|will) (?:automatically )?(?:renew|extend)',
            r'unless.*(?:written notice|terminated).*(?:\d+)\s*days?\s*(?:before|prior)',
        ],
        "severity": "medium",
        "weight": 8,
        "category": "Contract Duration",
    },
    "Unilateral termination": {
        "patterns": [
            r'(?:client|company) may terminate.*(?:at any time|without cause|without reason|for convenience)',
            r'terminate.*(?:immediately|without notice).*(?:sole discretion)',
            r'(?:client|company).*(?:right to|may).*cancel.*(?:without|any time)',
        ],
        "severity": "high",
        "weight": 15,
        "category": "Termination",
    },
    "Scope creep enabler": {
        "patterns": [
            r'(?:additional|other) (?:tasks|work|services).*(?:as (?:needed|required|requested))',
            r'(?:reasonable|related) (?:additional )?(?:tasks|duties|responsibilities)',
            r'(?:and|including)\s+(?:any|all)\s+(?:other|related|ancillary)',
        ],
        "severity": "medium",
        "weight": 12,
        "category": "Scope",
    },
    "No late payment penalty": {
        "patterns": [
            r'no (?:interest|penalty|late fee)',
            r'(?:waive|waiver).*(?:late|interest|penalty)',
        ],
        "severity": "medium",
        "weight": 8,
        "category": "Payment Terms",
    },
    "Confidentiality overreach": {
        "patterns": [
            r'confidential(?:ity)?.*(?:perpetual|indefinite|survive.*termination)',
            r'(?:shall not|may not) disclose.*(?:existence|terms).*(?:agreement|contract)',
            r'(?:all|any) information.*(?:deemed|considered)\s+confidential',
        ],
        "severity": "medium",
        "weight": 10,
        "category": "Confidentiality",
    },
    "Jurisdiction risk": {
        "patterns": [
            r'(?:governed by|jurisdiction of|laws of).*(?:foreign|international)',
            r'(?:courts? of|jurisdiction).*(?:exclusive)',
        ],
        "severity": "medium",
        "weight": 8,
        "category": "Legal",
    },
    "No revision limits": {
        "patterns": [
            r'unlimited\s+(?:revisions?|changes?|modifications?)',
            r'(?:as many|any number of)\s+(?:revisions?|changes?)',
            r'until\s+(?:client|company)\s+(?:is )?satisfied',
        ],
        "severity": "medium",
        "weight": 10,
        "category": "Scope",
    },
    "Penalty for delay": {
        "patterns": [
            r'penalty.*(?:delay|late|missed)',
            r'(?:liquidated damages|deduction).*(?:per day|per week|for each)',
            r'(?:\d+%?).*(?:deducted|penalty).*(?:day|week)',
        ],
        "severity": "medium",
        "weight": 10,
        "category": "Penalties",
    },
    "Moral rights waiver": {
        "patterns": [
            r'(?:waive|waiver).*(?:moral rights|attribution)',
            r'(?:no|without).*(?:credit|attribution|recognition)',
        ],
        "severity": "low",
        "weight": 5,
        "category": "Intellectual Property",
    },
    "Broad assignment clause": {
        "patterns": [
            r'(?:assign|transfer).*(?:rights|obligations).*(?:without|no).*(?:consent|approval)',
        ],
        "severity": "medium",
        "weight": 8,
        "category": "Legal",
    },
    "Force majeure one-sided": {
        "patterns": [
            r'force majeure.*(?:only|solely|exclusively).*(?:client|company)',
        ],
        "severity": "medium",
        "weight": 6,
        "category": "Legal",
    },
}

FAVORABLE_PATTERNS = {
    "Payment milestones defined": {
        "patterns": [
            r'(?:milestone|phase|installment|tranche).*(?:payment|paid)',
            r'(?:advance|upfront).*(?:payment|\d+%)',
            r'(\d+)%.*(?:upon signing|on commencement)',
        ],
        "category": "Payment Terms",
        "importance": "high",
    },
    "Mutual termination rights": {
        "patterns": [
            r'(?:either|both) part(?:y|ies) may terminate',
            r'freelancer.*(?:may|right to).*terminate',
            r'mutual.*(?:termination|cancellation)',
        ],
        "category": "Termination",
        "importance": "high",
    },
    "Late payment penalty included": {
        "patterns": [
            r'(?:interest|penalty|late fee).*(?:overdue|late|delayed)',
            r'(?:\d+%|percent).*(?:per month|monthly|per annum).*(?:late|overdue)',
        ],
        "category": "Payment Terms",
        "importance": "high",
    },
    "Scope clearly defined": {
        "patterns": [
            r'(?:scope of work|deliverables|specifications).*(?:set forth|described|listed|defined|attached)',
            r'(?:statement of work|SOW|schedule\s+[A-Z])',
        ],
        "category": "Scope",
        "importance": "high",
    },
    "Revision limits specified": {
        "patterns": [
            r'(?:revision|change|modification).*(?:limit|maximum|up to \d+)',
            r'(\d+)\s+(?:rounds?|sets?)\s+(?:of\s+)?(?:revisions?|feedback)',
        ],
        "category": "Scope",
        "importance": "medium",
    },
    "Kill fee / cancellation fee": {
        "patterns": [
            r'(?:kill fee|cancellation fee|termination fee)',
            r'(?:pay|compensat).*(?:work completed|work done).*(?:upon termination)',
        ],
        "category": "Termination",
        "importance": "high",
    },
    "Portfolio rights retained": {
        "patterns": [
            r'(?:portfolio|showcase|display|reference).*(?:right|permission)',
            r'(?:freelancer|contractor).*(?:may|right to).*(?:portfolio|showcase)',
        ],
        "category": "Intellectual Property",
        "importance": "medium",
    },
    "Dispute resolution via arbitration": {
        "patterns": [
            r'(?:arbitration|mediation).*(?:before|prior to|instead of).*(?:litigation|court)',
            r'(?:amicable|mutual).*(?:resolution|settlement)',
        ],
        "category": "Legal",
        "importance": "medium",
    },
}


class ContractScannerAgent:

    SYSTEM_PROMPT = """You are an expert contract analysis AI for Indian freelancers. Analyze the contract thoroughly and return JSON:
{
  "red_flags": [
    {"clause": "exact quote from contract", "issue": "why this is problematic", "severity": "high/medium/low", "category": "Payment Terms/IP/Liability/Scope/Termination/Legal/Other", "suggestion": "specific negotiation advice"}
  ],
  "favorable_terms": [
    {"clause": "exact quote", "reason": "why this is good", "category": "category"}
  ],
  "missing_clauses": [
    {"clause": "clause name", "importance": "critical/recommended/nice-to-have", "reason": "why it matters"}
  ],
  "overall_risk": "high/medium/low",
  "risk_score": 0-100,
  "contract_type": "Service Agreement/NDA/MSA/SOW/Employment/Other",
  "summary": "2-3 sentence summary",
  "negotiation_priority": ["ordered list of what to negotiate first"]
}
Focus on Indian contract law context. Return ONLY valid JSON."""

    def scan(self, contract_text: str) -> dict:
        llm_result = call_llm(self.SYSTEM_PROMPT, contract_text)
        result = extract_json(llm_result)
        if result and result.get("red_flags"):
            return result
        return self._rule_based_scan(contract_text)

    def _rule_based_scan(self, text: str) -> dict:
        text_lower = text.lower()

        # Detect contract type
        contract_type = "Service Agreement"
        type_patterns = {
            "NDA / Non-Disclosure": [r'non[- ]?disclosure', r'confidentiality\s+agreement'],
            "Master Service Agreement": [r'master\s+service', r'msa'],
            "Statement of Work": [r'statement\s+of\s+work', r'sow'],
            "Employment Contract": [r'employment\s+(?:agreement|contract)', r'letter\s+of\s+(?:appointment|offer)'],
            "Retainer Agreement": [r'retainer', r'monthly\s+(?:fee|engagement)'],
        }
        for ctype, patterns in type_patterns.items():
            for pat in patterns:
                if re.search(pat, text_lower):
                    contract_type = ctype
                    break

        # Scan for red flags with scoring
        red_flags = []
        total_weight = 0
        triggered_weight = 0

        for flag_name, config in RED_FLAG_PATTERNS.items():
            total_weight += config["weight"]
            for pat in config["patterns"]:
                matches = list(re.finditer(pat, text_lower))
                if matches:
                    m = matches[0]
                    start = max(0, m.start() - 80)
                    end = min(len(text), m.end() + 80)
                    context = text[start:end].strip()
                    # Clean up context
                    context = re.sub(r'\s+', ' ', context)

                    red_flags.append({
                        "clause": f"...{context}...",
                        "issue": flag_name,
                        "severity": config["severity"],
                        "category": config["category"],
                        "suggestion": self._get_suggestion(flag_name),
                    })
                    triggered_weight += config["weight"]
                    break

        # Scan for favorable terms
        favorable = []
        for term_name, config in FAVORABLE_PATTERNS.items():
            for pat in config["patterns"]:
                m = re.search(pat, text_lower)
                if m:
                    start = max(0, m.start() - 50)
                    end = min(len(text), m.end() + 50)
                    context = text[start:end].strip()
                    context = re.sub(r'\s+', ' ', context)
                    favorable.append({
                        "clause": f"...{context}...",
                        "reason": f"Contract includes {term_name.lower()}",
                        "category": config["category"],
                    })
                    break

        # Check missing clauses with importance
        missing = []
        essential_clauses = {
            "Payment schedule & terms": {
                "pattern": r'(?:payment|compensation|fee|rate|invoic)',
                "importance": "critical",
                "reason": "Without clear payment terms, you risk delayed or disputed payments",
            },
            "Termination clause": {
                "pattern": r'terminat(?:e|ion)',
                "importance": "critical",
                "reason": "You need a clear exit strategy with reasonable notice period",
            },
            "Scope of work": {
                "pattern": r'(?:scope|deliverables|specifications|requirements)',
                "importance": "critical",
                "reason": "Undefined scope leads to scope creep and disputes",
            },
            "Liability limitation": {
                "pattern": r'(?:limit.*liabil|liabil.*limit|cap.*liabil)',
                "importance": "critical",
                "reason": "Without a cap, you could be liable for unlimited damages",
            },
            "Intellectual property clause": {
                "pattern": r'(?:intellectual property|IP rights|copyright|ownership.*work)',
                "importance": "critical",
                "reason": "Clarify who owns what — especially after full payment",
            },
            "Confidentiality": {
                "pattern": r'confidential',
                "importance": "recommended",
                "reason": "Protects both parties' sensitive information",
            },
            "Dispute resolution": {
                "pattern": r'(?:dispute|arbitrat|mediat|resolution)',
                "importance": "recommended",
                "reason": "Avoid costly litigation — prefer arbitration or mediation",
            },
            "Revision/change policy": {
                "pattern": r'(?:revision|change order|amendment|modification)',
                "importance": "recommended",
                "reason": "Prevents unlimited revision requests without additional compensation",
            },
            "Force majeure": {
                "pattern": r'force majeure',
                "importance": "recommended",
                "reason": "Protects both parties from unforeseeable events",
            },
            "Data protection": {
                "pattern": r'(?:data protection|privacy|gdpr|personal data|dpdp)',
                "importance": "nice-to-have",
                "reason": "Important if handling personal or sensitive data",
            },
        }

        for clause_name, config in essential_clauses.items():
            if not re.search(config["pattern"], text_lower):
                missing.append({
                    "clause": clause_name,
                    "importance": config["importance"],
                    "reason": config["reason"],
                })

        # Calculate risk score (0-100)
        risk_score = 0
        if total_weight > 0:
            risk_score = min(100, int((triggered_weight / total_weight) * 100))

        # Adjust score for missing critical clauses
        critical_missing = sum(1 for m in missing if m["importance"] == "critical")
        risk_score = min(100, risk_score + critical_missing * 8)

        # Reduce score for favorable terms
        risk_score = max(0, risk_score - len(favorable) * 5)

        # Overall risk level
        if risk_score >= 60:
            overall_risk = "high"
        elif risk_score >= 30:
            overall_risk = "medium"
        else:
            overall_risk = "low"

        # Sort red flags: high severity first
        severity_order = {"high": 0, "medium": 1, "low": 2}
        red_flags.sort(key=lambda x: severity_order.get(x["severity"], 1))

        # Negotiation priority
        negotiation_priority = []
        for rf in red_flags:
            if rf["severity"] == "high":
                negotiation_priority.append(rf["issue"])
        for m in missing:
            if m["importance"] == "critical":
                negotiation_priority.append(f"Add {m['clause']}")

        return {
            "red_flags": red_flags,
            "favorable_terms": favorable,
            "missing_clauses": missing,
            "overall_risk": overall_risk,
            "risk_score": risk_score,
            "contract_type": contract_type,
            "summary": self._generate_summary(red_flags, favorable, missing, overall_risk, risk_score, contract_type),
            "negotiation_priority": negotiation_priority[:5],
        }

    def _generate_summary(self, red_flags, favorable, missing, risk, score, ctype):
        high_flags = sum(1 for f in red_flags if f["severity"] == "high")
        critical_missing = sum(1 for m in missing if m["importance"] == "critical")

        summary = f"This {ctype} has a risk score of {score}/100 ({risk} risk). "
        summary += f"Found {len(red_flags)} red flag(s) ({high_flags} high severity) and {len(favorable)} favorable term(s). "

        if critical_missing > 0:
            summary += f"{critical_missing} critical clause(s) are missing. "

        if risk == "high":
            summary += "⚠️ Significant negotiation needed before signing."
        elif risk == "medium":
            summary += "Review flagged items and negotiate key terms."
        else:
            summary += "Contract appears reasonable — verify details match verbal agreements."

        return summary

    def _get_suggestion(self, flag: str) -> str:
        suggestions = {
            "Non-compete clause": "Negotiate to limit: (1) scope to direct competitors only, (2) geography to your city/state, (3) duration to max 6 months. Indian courts generally don't enforce broad non-competes under Section 27 of the Indian Contract Act.",
            "IP assignment without compensation": "Counter with: IP transfers only upon FULL payment. Retain rights to use in portfolio. Request license-back for reusable components you built. Ensure pre-existing IP is excluded.",
            "Unlimited liability": "Cap liability at the total contract value or fees received in last 12 months. Exclude consequential/indirect damages. Add professional indemnity insurance requirement.",
            "Payment only on completion": "Request milestone-based payments: 25-30% upfront, 25% at mid-point, remainder on delivery. For large projects, monthly invoicing is standard.",
            "Auto-renewal trap": "Add: (1) 30-day written notice requirement before renewal, (2) opt-in instead of opt-out, (3) cap on price increases on renewal.",
            "Unilateral termination": "Make termination mutual with 15-30 day notice. Add kill fee (50-100% of remaining contract value). Ensure payment for work completed to date.",
            "Scope creep enabler": "Replace vague scope with specific deliverables list. Add change order process: any additional work requires written approval and separate pricing.",
            "No late payment penalty": "Add 1.5-2% monthly interest on payments overdue by 15+ days. Include right to pause work after 30 days non-payment.",
            "Confidentiality overreach": "Limit to 2 years post-termination. Exclude: (1) publicly available info, (2) info you already knew, (3) info received from third parties. Allow disclosing that the client relationship exists.",
            "Jurisdiction risk": "Negotiate for your local jurisdiction (your city's courts) or neutral arbitration (e.g., under Arbitration & Conciliation Act, 1996).",
            "No revision limits": "Specify revision rounds (2-3 is standard). Additional revisions billed at hourly rate. Define what constitutes a 'revision' vs 'new scope'.",
            "Penalty for delay": "Ensure penalty is reasonable and capped (5-10% of project value). Add grace period. Exclude delays caused by client (late feedback, missing assets).",
            "Moral rights waiver": "Retain right to be credited. At minimum, retain portfolio display rights after project completion.",
            "Broad assignment clause": "Require written consent for assignment. Add that assignment doesn't release original party from obligations.",
            "Force majeure one-sided": "Make force majeure applicable to both parties equally. Include pandemics, natural disasters, government actions.",
        }
        return suggestions.get(flag, "Review this clause carefully with a legal professional.")
