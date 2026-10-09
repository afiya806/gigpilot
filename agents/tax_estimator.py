"""Tax Estimator Agent: quarterly advance tax and TDS tracking for Indian freelancers."""

from datetime import datetime


# Indian income tax slabs for FY 2025-26 (New Tax Regime)
NEW_REGIME_SLABS = [
    (400000, 0.00),
    (400000, 0.05),
    (400000, 0.10),
    (400000, 0.15),
    (400000, 0.20),
    (float('inf'), 0.30),
]

# Standard deduction for salaried/pension (not applicable for freelancers under new regime)
# Section 80C, 80D etc. only under old regime
OLD_REGIME_SLABS = [
    (250000, 0.00),
    (250000, 0.05),
    (500000, 0.20),
    (float('inf'), 0.30),
]

# Advance tax schedule
ADVANCE_TAX_SCHEDULE = [
    {"quarter": "Q1", "due_date": "June 15", "cumulative_percent": 15},
    {"quarter": "Q2", "due_date": "September 15", "cumulative_percent": 45},
    {"quarter": "Q3", "due_date": "December 15", "cumulative_percent": 75},
    {"quarter": "Q4", "due_date": "March 15", "cumulative_percent": 100},
]

# Common TDS rates for freelancers
TDS_RATES = {
    "194J_technical": {"section": "194J", "description": "Technical Services", "rate": 2},
    "194J_professional": {"section": "194J", "description": "Professional Services", "rate": 10},
    "194C_individual": {"section": "194C", "description": "Contractor (Individual/HUF)", "rate": 1},
    "194C_others": {"section": "194C", "description": "Contractor (Others)", "rate": 2},
    "194O_ecommerce": {"section": "194O", "description": "E-commerce Operator", "rate": 1},
}

# Presumptive taxation thresholds
PRESUMPTIVE_LIMIT_44ADA = 7500000  # 75 lakhs for professionals (digital receipts)
PRESUMPTIVE_RATE_44ADA = 0.50  # 50% of gross receipts deemed as income


class TaxEstimatorAgent:

    def estimate(self, data: dict) -> dict:
        """Estimate tax liability for Indian freelancer."""
        gross_income = float(data.get("gross_income", 0))
        expenses = float(data.get("expenses", 0))
        tds_paid = float(data.get("tds_paid", 0))
        regime = data.get("regime", "new")  # "new" or "old"
        deductions_80c = float(data.get("deductions_80c", 0))
        health_insurance_80d = float(data.get("health_insurance_80d", 0))
        use_presumptive = data.get("use_presumptive", False)

        # Calculate taxable income
        if use_presumptive and gross_income <= PRESUMPTIVE_LIMIT_44ADA:
            taxable_income = gross_income * PRESUMPTIVE_RATE_44ADA
            method = "Presumptive (Section 44ADA)"
        else:
            taxable_income = max(0, gross_income - expenses)
            method = "Regular (Actual expenses)"

        # Apply deductions (only under old regime)
        total_deductions = 0
        if regime == "old":
            deductions_80c = min(deductions_80c, 150000)
            health_insurance_80d = min(health_insurance_80d, 25000)
            total_deductions = deductions_80c + health_insurance_80d
            taxable_income = max(0, taxable_income - total_deductions)
            # Standard deduction of 50,000 under old regime
            taxable_income = max(0, taxable_income - 50000)
            total_deductions += 50000
        else:
            # New regime standard deduction
            taxable_income = max(0, taxable_income - 75000)
            total_deductions = 75000

        # Calculate tax
        slabs = NEW_REGIME_SLABS if regime == "new" else OLD_REGIME_SLABS
        tax = self._calculate_slab_tax(taxable_income, slabs)

        # Rebate u/s 87A
        rebate = 0
        if regime == "new" and taxable_income <= 1200000:
            rebate = min(tax, 60000)
        elif regime == "old" and taxable_income <= 500000:
            rebate = min(tax, 12500)

        tax_after_rebate = max(0, tax - rebate)

        # Health and Education Cess (4%)
        cess = tax_after_rebate * 0.04
        total_tax = tax_after_rebate + cess

        # Net tax payable after TDS
        net_payable = max(0, total_tax - tds_paid)

        # Advance tax breakdown
        advance_tax = self._calculate_advance_tax(total_tax, tds_paid)

        # Determine current quarter
        now = datetime.now()
        month = now.month
        if month <= 6:
            current_quarter = "Q1"
        elif month <= 9:
            current_quarter = "Q2"
        elif month <= 12:
            current_quarter = "Q3"
        else:
            current_quarter = "Q4"

        return {
            "gross_income": gross_income,
            "expenses": expenses,
            "computation_method": method,
            "taxable_income": round(taxable_income),
            "regime": regime.upper(),
            "total_deductions": round(total_deductions),
            "tax_before_rebate": round(tax),
            "rebate_87a": round(rebate),
            "tax_after_rebate": round(tax_after_rebate),
            "cess": round(cess),
            "total_tax_liability": round(total_tax),
            "tds_already_paid": round(tds_paid),
            "net_tax_payable": round(net_payable),
            "effective_tax_rate": round(total_tax / gross_income * 100, 1) if gross_income > 0 else 0,
            "advance_tax_schedule": advance_tax,
            "current_quarter": current_quarter,
            "tds_reference": TDS_RATES,
            "tips": self._get_tips(gross_income, regime, taxable_income),
        }

    def _calculate_slab_tax(self, income: float, slabs: list) -> float:
        tax = 0
        remaining = income
        for slab_limit, rate in slabs:
            if remaining <= 0:
                break
            taxable_in_slab = min(remaining, slab_limit)
            tax += taxable_in_slab * rate
            remaining -= taxable_in_slab
        return tax

    def _calculate_advance_tax(self, total_tax: float, tds_paid: float) -> list:
        net = max(0, total_tax - tds_paid)
        if net < 10000:
            return [{"note": "No advance tax required (liability under 10,000)"}]

        schedule = []
        for entry in ADVANCE_TAX_SCHEDULE:
            cumulative = net * entry["cumulative_percent"] / 100
            schedule.append({
                "quarter": entry["quarter"],
                "due_date": entry["due_date"],
                "cumulative_amount": round(cumulative),
                "percent": entry["cumulative_percent"],
            })
        return schedule

    def _get_tips(self, gross: float, regime: str, taxable: float) -> list:
        tips = []
        if gross <= PRESUMPTIVE_LIMIT_44ADA:
            tips.append("You qualify for Section 44ADA presumptive taxation. Only 50% of receipts are taxed, and no books of accounts needed.")
        if regime == "new" and taxable > 1200000:
            tips.append("Consider old regime if your Section 80C + 80D + HRA deductions exceed 3.75 lakhs.")
        if regime == "old":
            tips.append("Max out Section 80C (1.5L) and 80D (health insurance) to reduce taxable income.")
        tips.append("Keep all expense receipts and invoices. Digital payments over 50L attract 194N TDS.")
        tips.append("File ITR-3 (regular) or ITR-4 (presumptive) before July 31.")
        return tips
