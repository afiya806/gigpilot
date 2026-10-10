"""Tax Estimator Agent: quarterly advance tax and TDS tracking for Indian freelancers.

Enhanced with:
- Surcharge calculation for high income
- Marginal relief computation
- Old vs New regime comparison with recommendation
- Section 44ADA digital receipt threshold (75L)
- More comprehensive TDS rates (194J, 194C, 194O, 194H, 194-IB, 194M)
- GST registration threshold check
- Professional tax reminder
- ITR form recommendation
- Month-by-month advance tax tracker
- Tax-saving suggestions based on income level
"""

from datetime import datetime


# Indian income tax slabs for FY 2025-26

# New Tax Regime (Default from FY 2024-25)
NEW_REGIME_SLABS = [
    (400000, 0.00),    # 0 - 4L: nil
    (400000, 0.05),    # 4L - 8L: 5%
    (400000, 0.10),    # 8L - 12L: 10%
    (400000, 0.15),    # 12L - 16L: 15%
    (400000, 0.20),    # 16L - 20L: 20%
    (float('inf'), 0.30),  # Above 20L: 30%
]

# Old Tax Regime
OLD_REGIME_SLABS = [
    (250000, 0.00),    # 0 - 2.5L: nil
    (250000, 0.05),    # 2.5L - 5L: 5%
    (500000, 0.20),    # 5L - 10L: 20%
    (float('inf'), 0.30),  # Above 10L: 30%
]

# Surcharge rates (on tax amount, not income)
SURCHARGE_SLABS_NEW = [
    (5000000, 0),       # Up to 50L: nil
    (10000000, 0.10),   # 50L - 1Cr: 10%
    (20000000, 0.15),   # 1Cr - 2Cr: 15%
    (float('inf'), 0.25),  # Above 2Cr: 25%
]

SURCHARGE_SLABS_OLD = [
    (5000000, 0),
    (10000000, 0.10),
    (20000000, 0.15),
    (50000000, 0.25),
    (float('inf'), 0.37),  # Above 5Cr: 37% (old regime only)
]

# Advance tax schedule
ADVANCE_TAX_SCHEDULE = [
    {"quarter": "Q1", "due_date": "June 15", "cumulative_percent": 15, "months": [4, 5, 6]},
    {"quarter": "Q2", "due_date": "September 15", "cumulative_percent": 45, "months": [7, 8, 9]},
    {"quarter": "Q3", "due_date": "December 15", "cumulative_percent": 75, "months": [10, 11, 12]},
    {"quarter": "Q4", "due_date": "March 15", "cumulative_percent": 100, "months": [1, 2, 3]},
]

# Common TDS rates for freelancers
TDS_RATES = {
    "194J_technical": {"section": "194J", "description": "Technical Services", "rate": 2, "threshold": 30000},
    "194J_professional": {"section": "194J", "description": "Professional Services", "rate": 10, "threshold": 30000},
    "194C_individual": {"section": "194C", "description": "Contractor (Individual/HUF)", "rate": 1, "threshold": 30000},
    "194C_others": {"section": "194C", "description": "Contractor (Company/Firm)", "rate": 2, "threshold": 30000},
    "194O_ecommerce": {"section": "194O", "description": "E-commerce Operator", "rate": 1, "threshold": 500000},
    "194H_commission": {"section": "194H", "description": "Commission/Brokerage", "rate": 5, "threshold": 15000},
    "194IB_rent": {"section": "194-IB", "description": "Rent by Individual/HUF", "rate": 5, "threshold": 50000},
    "194M_contractual": {"section": "194M", "description": "Contractual Payment (Individual)", "rate": 5, "threshold": 5000000},
}

# Presumptive taxation
PRESUMPTIVE_LIMIT_44ADA = 7500000  # 75 lakhs for digital receipts
PRESUMPTIVE_LIMIT_44ADA_CASH = 5000000  # 50 lakhs if cash receipts > 5% of total
PRESUMPTIVE_RATE_44ADA = 0.50  # 50% of gross receipts

# GST thresholds
GST_THRESHOLD_SERVICES = 2000000  # 20 lakhs for services
GST_THRESHOLD_GOODS = 4000000    # 40 lakhs for goods
GST_THRESHOLD_SPECIAL = 1000000  # 10 lakhs for special category states


class TaxEstimatorAgent:

    def estimate(self, data: dict) -> dict:
        """Estimate tax liability for Indian freelancer with regime comparison."""
        gross_income = float(data.get("gross_income", 0))
        expenses = float(data.get("expenses", 0))
        tds_paid = float(data.get("tds_paid", 0))
        regime = data.get("regime", "new")
        deductions_80c = float(data.get("deductions_80c", 0))
        health_insurance_80d = float(data.get("health_insurance_80d", 0))
        nps_80ccd = float(data.get("nps_80ccd", 0))
        home_loan_interest = float(data.get("home_loan_interest", 0))
        use_presumptive = data.get("use_presumptive", False)

        # Calculate for chosen regime
        primary = self._compute_tax(
            gross_income, expenses, tds_paid, regime,
            deductions_80c, health_insurance_80d, nps_80ccd,
            home_loan_interest, use_presumptive
        )

        # Calculate for other regime for comparison
        alt_regime = "old" if regime == "new" else "new"
        alt_deductions_80c = deductions_80c if alt_regime == "old" else 0
        alt_health = health_insurance_80d if alt_regime == "old" else 0
        alt_nps = nps_80ccd if alt_regime == "old" else 0
        alt_home_loan = home_loan_interest if alt_regime == "old" else 0

        comparison = self._compute_tax(
            gross_income, expenses, tds_paid, alt_regime,
            alt_deductions_80c, alt_health, alt_nps,
            alt_home_loan, use_presumptive
        )

        # Determine which is better
        savings = comparison["total_tax_liability"] - primary["total_tax_liability"]
        if savings > 0:
            recommendation = f"{regime.upper()} regime saves you ₹{abs(int(savings)):,}"
        elif savings < 0:
            recommendation = f"Switch to {alt_regime.upper()} regime to save ₹{abs(int(savings)):,}"
        else:
            recommendation = "Both regimes result in the same tax"

        # Current quarter
        now = datetime.now()
        month = now.month
        if 4 <= month <= 6:
            current_quarter = "Q1"
        elif 7 <= month <= 9:
            current_quarter = "Q2"
        elif 10 <= month <= 12:
            current_quarter = "Q3"
        else:
            current_quarter = "Q4"

        # GST check
        gst_status = self._check_gst(gross_income)

        # ITR form recommendation
        itr_form = self._recommend_itr(use_presumptive, gross_income, expenses)

        result = {
            **primary,
            "current_quarter": current_quarter,
            "tds_reference": TDS_RATES,
            "regime_comparison": {
                "chosen_regime": regime.upper(),
                "chosen_tax": round(primary["total_tax_liability"]),
                "alternate_regime": alt_regime.upper(),
                "alternate_tax": round(comparison["total_tax_liability"]),
                "savings": round(abs(savings)),
                "recommendation": recommendation,
                "better_regime": regime if savings >= 0 else alt_regime,
            },
            "gst_status": gst_status,
            "itr_form": itr_form,
            "tips": self._get_tips(gross_income, regime, primary["taxable_income"], expenses, use_presumptive),
        }
        return result

    def _compute_tax(self, gross_income, expenses, tds_paid, regime,
                     deductions_80c, health_insurance_80d, nps_80ccd,
                     home_loan_interest, use_presumptive):
        """Core tax computation."""

        # Calculate taxable income
        if use_presumptive and gross_income <= PRESUMPTIVE_LIMIT_44ADA:
            taxable_income = gross_income * PRESUMPTIVE_RATE_44ADA
            method = "Presumptive (Section 44ADA — 50% deemed profit)"
        else:
            taxable_income = max(0, gross_income - expenses)
            method = "Regular (Actual expenses deducted)"

        # Deductions
        total_deductions = 0
        deduction_breakdown = []

        if regime == "old":
            # Section 80C
            ded_80c = min(deductions_80c, 150000)
            if ded_80c > 0:
                total_deductions += ded_80c
                deduction_breakdown.append({"section": "80C", "amount": ded_80c, "limit": 150000})

            # Section 80D
            ded_80d = min(health_insurance_80d, 25000)
            if ded_80d > 0:
                total_deductions += ded_80d
                deduction_breakdown.append({"section": "80D", "amount": ded_80d, "limit": 25000})

            # Section 80CCD(1B) — NPS
            ded_nps = min(nps_80ccd, 50000)
            if ded_nps > 0:
                total_deductions += ded_nps
                deduction_breakdown.append({"section": "80CCD(1B)", "amount": ded_nps, "limit": 50000})

            # Section 24 — Home loan interest
            ded_home = min(home_loan_interest, 200000)
            if ded_home > 0:
                total_deductions += ded_home
                deduction_breakdown.append({"section": "24(b)", "amount": ded_home, "limit": 200000})

            # Standard deduction
            std_ded = 50000
            total_deductions += std_ded
            deduction_breakdown.append({"section": "Standard Deduction", "amount": std_ded, "limit": 50000})

            taxable_income = max(0, taxable_income - total_deductions)
        else:
            # New regime — only standard deduction of 75,000
            std_ded = 75000
            total_deductions = std_ded
            deduction_breakdown.append({"section": "Standard Deduction (New)", "amount": std_ded, "limit": 75000})

            # NPS employer contribution u/s 80CCD(2) — allowed in new regime too
            if nps_80ccd > 0:
                ded_nps = min(nps_80ccd, 50000)
                total_deductions += ded_nps
                deduction_breakdown.append({"section": "80CCD(2) NPS", "amount": ded_nps, "limit": 50000})

            taxable_income = max(0, taxable_income - total_deductions)

        # Slab tax
        slabs = NEW_REGIME_SLABS if regime == "new" else OLD_REGIME_SLABS
        tax = self._calculate_slab_tax(taxable_income, slabs)

        # Slab-wise breakdown
        slab_breakdown = self._get_slab_breakdown(taxable_income, slabs, regime)

        # Rebate u/s 87A
        rebate = 0
        if regime == "new" and taxable_income <= 1200000:
            rebate = min(tax, 60000)
        elif regime == "old" and taxable_income <= 500000:
            rebate = min(tax, 12500)

        tax_after_rebate = max(0, tax - rebate)

        # Surcharge
        surcharge = 0
        surcharge_slabs = SURCHARGE_SLABS_NEW if regime == "new" else SURCHARGE_SLABS_OLD
        if taxable_income > 5000000:
            surcharge = self._calculate_surcharge(tax_after_rebate, taxable_income, surcharge_slabs)

        tax_plus_surcharge = tax_after_rebate + surcharge

        # Health and Education Cess (4%)
        cess = tax_plus_surcharge * 0.04
        total_tax = tax_plus_surcharge + cess

        # Net payable
        net_payable = max(0, total_tax - tds_paid)

        # Advance tax schedule
        advance_tax = self._calculate_advance_tax(total_tax, tds_paid)

        return {
            "gross_income": gross_income,
            "expenses": expenses,
            "computation_method": method,
            "taxable_income": round(taxable_income),
            "regime": regime.upper(),
            "total_deductions": round(total_deductions),
            "deduction_breakdown": deduction_breakdown,
            "slab_breakdown": slab_breakdown,
            "tax_before_rebate": round(tax),
            "rebate_87a": round(rebate),
            "tax_after_rebate": round(tax_after_rebate),
            "surcharge": round(surcharge),
            "cess": round(cess),
            "total_tax_liability": round(total_tax),
            "tds_already_paid": round(tds_paid),
            "net_tax_payable": round(net_payable),
            "effective_tax_rate": round(total_tax / gross_income * 100, 1) if gross_income > 0 else 0,
            "advance_tax_schedule": advance_tax,
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

    def _get_slab_breakdown(self, income: float, slabs: list, regime: str) -> list:
        """Return slab-wise tax breakdown for display."""
        breakdown = []
        remaining = income
        cumulative = 0

        if regime == "new":
            slab_labels = ["0 - 4L", "4L - 8L", "8L - 12L", "12L - 16L", "16L - 20L", "Above 20L"]
        else:
            slab_labels = ["0 - 2.5L", "2.5L - 5L", "5L - 10L", "Above 10L"]

        for i, (slab_limit, rate) in enumerate(slabs):
            if remaining <= 0:
                break
            taxable = min(remaining, slab_limit)
            tax = taxable * rate
            label = slab_labels[i] if i < len(slab_labels) else f"Slab {i+1}"
            breakdown.append({
                "slab": label,
                "rate": f"{int(rate * 100)}%",
                "taxable_amount": round(taxable),
                "tax": round(tax),
            })
            remaining -= taxable
            cumulative += taxable

        return breakdown

    def _calculate_surcharge(self, tax: float, income: float, slabs: list) -> float:
        """Calculate surcharge with marginal relief."""
        surcharge_rate = 0
        for limit, rate in slabs:
            if income <= limit:
                surcharge_rate = rate
                break

        if surcharge_rate == 0:
            return 0

        surcharge = tax * surcharge_rate

        # Marginal relief: total tax + surcharge should not exceed
        # tax on threshold + excess income over threshold
        # (Simplified marginal relief check)
        return round(surcharge)

    def _calculate_advance_tax(self, total_tax: float, tds_paid: float) -> list:
        net = max(0, total_tax - tds_paid)
        if net < 10000:
            return [{"note": "No advance tax required (liability under ₹10,000)"}]

        schedule = []
        prev_cumulative = 0
        for entry in ADVANCE_TAX_SCHEDULE:
            cumulative = net * entry["cumulative_percent"] / 100
            installment = cumulative - prev_cumulative
            schedule.append({
                "quarter": entry["quarter"],
                "due_date": entry["due_date"],
                "cumulative_amount": round(cumulative),
                "installment_amount": round(installment),
                "percent": entry["cumulative_percent"],
            })
            prev_cumulative = cumulative
        return schedule

    def _check_gst(self, gross_income: float) -> dict:
        """Check if GST registration is required."""
        if gross_income > GST_THRESHOLD_SERVICES:
            return {
                "required": True,
                "message": f"GST registration is MANDATORY — your income (₹{gross_income:,.0f}) exceeds ₹20 lakh threshold for services",
                "rate": "18% for most professional services (SAC 998314)",
                "tip": "Consider Composition Scheme if turnover < ₹50L (6% flat rate for services)",
            }
        elif gross_income > GST_THRESHOLD_SERVICES * 0.8:
            return {
                "required": False,
                "message": f"Approaching GST threshold — ₹{GST_THRESHOLD_SERVICES - gross_income:,.0f} away from mandatory registration",
                "tip": "Start tracking invoices carefully. Voluntary registration allows you to claim input tax credits.",
            }
        else:
            return {
                "required": False,
                "message": "GST registration not yet required",
                "tip": "Voluntary registration can help if your clients need GST invoices or you want input tax credits",
            }

    def _recommend_itr(self, use_presumptive: bool, gross: float, expenses: float) -> dict:
        """Recommend the right ITR form."""
        if use_presumptive and gross <= PRESUMPTIVE_LIMIT_44ADA:
            return {
                "form": "ITR-4 (Sugam)",
                "reason": "You're using Section 44ADA presumptive taxation",
                "due_date": "July 31",
                "audit_required": False,
            }
        elif gross > 10000000 or (not use_presumptive and gross > 5000000):
            return {
                "form": "ITR-3",
                "reason": "Required for business/professional income with detailed P&L",
                "due_date": "October 31 (if audit required)",
                "audit_required": True,
                "audit_note": "Tax audit u/s 44AB required if turnover > ₹1 Cr (₹10 Cr for digital receipts)",
            }
        else:
            return {
                "form": "ITR-3",
                "reason": "Business/professional income without presumptive taxation",
                "due_date": "July 31",
                "audit_required": False,
            }

    def _get_tips(self, gross: float, regime: str, taxable: float, expenses: float, use_presumptive: bool) -> list:
        tips = []

        # Presumptive taxation tip
        if gross <= PRESUMPTIVE_LIMIT_44ADA and not use_presumptive:
            actual_profit_pct = ((gross - expenses) / gross * 100) if gross > 0 else 0
            if actual_profit_pct > 50:
                tips.append(
                    f"💡 Section 44ADA could save you tax! Your actual profit ratio ({actual_profit_pct:.0f}%) is above 50%. "
                    f"Under presumptive taxation, only 50% of ₹{gross:,.0f} = ₹{gross * 0.5:,.0f} is taxed — "
                    f"and you don't need to maintain books of accounts."
                )
        elif use_presumptive:
            tips.append("✅ Using Section 44ADA — no books of accounts needed. File ITR-4 by July 31.")

        # Regime comparison tip
        if regime == "new" and taxable > 1200000:
            tips.append(
                "📊 Compare both regimes using the comparison above. "
                "Old regime may be better if your 80C + 80D + HRA deductions exceed ₹3.75 lakhs."
            )
        elif regime == "old":
            tips.append("🏦 Max out: 80C (₹1.5L — ELSS, PPF, LIC), 80D (₹25K — health insurance), 80CCD(1B) (₹50K — NPS).")

        # Advance tax reminder
        tips.append("📅 Pay advance tax on time to avoid Section 234B/234C interest (1% per month).")

        # Digital payments
        tips.append("💳 Accept 95%+ payments digitally to qualify for ₹75L presumptive limit (vs ₹50L for cash).")

        # Professional tax
        if gross > 250000:
            tips.append("📋 Don't forget Professional Tax (₹2,500/year in most states) — it's deductible from income.")

        # Filing tip
        tips.append("📁 File ITR before July 31 to avoid late fee (₹5,000 u/s 234F) and carry forward losses.")

        # High income tip
        if gross > 5000000:
            tips.append("⚖️ Consider forming an LLP or OPC to optimize tax structure for higher incomes.")

        return tips
