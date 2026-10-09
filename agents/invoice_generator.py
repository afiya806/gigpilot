"""Invoice Generator Agent: creates GST-compliant Indian invoices as PDF."""

import io
import os
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


class InvoiceGeneratorAgent:

    def generate(self, data: dict) -> bytes:
        """Generate a GST-compliant invoice PDF and return bytes."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm,
                                leftMargin=20*mm, rightMargin=20*mm)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('InvoiceTitle', parent=styles['Title'],
                                      fontSize=24, textColor=colors.HexColor('#1a1a2e'),
                                      spaceAfter=2*mm)
        header_style = ParagraphStyle('Header', parent=styles['Normal'],
                                       fontSize=10, textColor=colors.HexColor('#555555'))
        bold_style = ParagraphStyle('Bold', parent=styles['Normal'],
                                     fontSize=10, fontName='Helvetica-Bold')
        small_style = ParagraphStyle('Small', parent=styles['Normal'],
                                      fontSize=8, textColor=colors.HexColor('#888888'))

        elements = []

        # Header
        elements.append(Paragraph("INVOICE", title_style))
        elements.append(Spacer(1, 2*mm))

        invoice_number = data.get("invoice_number", f"INV-{datetime.now().strftime('%Y%m%d%H%M')}")
        invoice_date = data.get("date", datetime.now().strftime("%d %B %Y"))
        due_date_str = data.get("due_date", "")
        if not due_date_str:
            due_date_str = (datetime.now() + timedelta(days=30)).strftime("%d %B %Y")

        # Invoice meta
        meta_data = [
            [Paragraph(f"<b>Invoice #:</b> {invoice_number}", header_style),
             Paragraph(f"<b>Date:</b> {invoice_date}", header_style)],
            [Paragraph(f"<b>Due Date:</b> {due_date_str}", header_style),
             Paragraph(f"<b>Status:</b> {data.get('status', 'Unpaid')}", header_style)],
        ]
        meta_table = Table(meta_data, colWidths=[90*mm, 80*mm])
        meta_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 5*mm))

        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e0e0e0')))
        elements.append(Spacer(1, 5*mm))

        # From / To
        from_name = data.get("from_name", "Your Name")
        from_address = data.get("from_address", "Your Address")
        from_gstin = data.get("from_gstin", "")
        from_pan = data.get("from_pan", "")

        to_name = data.get("to_name", "Client Name")
        to_address = data.get("to_address", "Client Address")
        to_gstin = data.get("to_gstin", "")

        from_block = f"<b>From:</b><br/>{from_name}<br/>{from_address}"
        if from_gstin:
            from_block += f"<br/>GSTIN: {from_gstin}"
        if from_pan:
            from_block += f"<br/>PAN: {from_pan}"

        to_block = f"<b>Bill To:</b><br/>{to_name}<br/>{to_address}"
        if to_gstin:
            to_block += f"<br/>GSTIN: {to_gstin}"

        party_data = [[Paragraph(from_block, header_style), Paragraph(to_block, header_style)]]
        party_table = Table(party_data, colWidths=[90*mm, 80*mm])
        party_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        elements.append(party_table)
        elements.append(Spacer(1, 8*mm))

        # Line items table
        items = data.get("items", [])
        header_row = [
            Paragraph("<b>#</b>", bold_style),
            Paragraph("<b>Description</b>", bold_style),
            Paragraph("<b>HSN/SAC</b>", bold_style),
            Paragraph("<b>Qty</b>", bold_style),
            Paragraph("<b>Rate</b>", bold_style),
            Paragraph("<b>Amount</b>", bold_style),
        ]

        table_data = [header_row]
        subtotal = 0
        for i, item in enumerate(items, 1):
            qty = float(item.get("quantity", 1))
            rate = float(item.get("rate", 0))
            amount = qty * rate
            subtotal += amount
            table_data.append([
                str(i),
                Paragraph(item.get("description", "Service"), header_style),
                item.get("hsn_sac", "998314"),
                str(int(qty)),
                f"{rate:,.2f}",
                f"{amount:,.2f}",
            ])

        # GST calculations
        gst_rate = float(data.get("gst_rate", 18))
        is_igst = data.get("is_igst", False)

        if is_igst:
            igst = subtotal * gst_rate / 100
            total = subtotal + igst
            table_data.append(["", "", "", "", Paragraph("<b>Subtotal</b>", bold_style), f"{subtotal:,.2f}"])
            table_data.append(["", "", "", "", Paragraph(f"<b>IGST ({gst_rate}%)</b>", bold_style), f"{igst:,.2f}"])
        else:
            half_rate = gst_rate / 2
            cgst = subtotal * half_rate / 100
            sgst = subtotal * half_rate / 100
            total = subtotal + cgst + sgst
            table_data.append(["", "", "", "", Paragraph("<b>Subtotal</b>", bold_style), f"{subtotal:,.2f}"])
            table_data.append(["", "", "", "", Paragraph(f"<b>CGST ({half_rate}%)</b>", bold_style), f"{cgst:,.2f}"])
            table_data.append(["", "", "", "", Paragraph(f"<b>SGST ({half_rate}%)</b>", bold_style), f"{sgst:,.2f}"])

        currency = data.get("currency", "INR")
        symbol = "₹" if currency == "INR" else "$" if currency == "USD" else currency + " "
        table_data.append(["", "", "", "", Paragraph(f"<b>Total ({currency})</b>", bold_style),
                           Paragraph(f"<b>{symbol}{total:,.2f}</b>", bold_style)])

        col_widths = [10*mm, 60*mm, 22*mm, 15*mm, 28*mm, 30*mm]
        items_table = Table(table_data, colWidths=col_widths)
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, len(items)), 0.5, colors.HexColor('#dddddd')),
            ('LINEABOVE', (4, len(items)+1), (-1, len(items)+1), 1, colors.HexColor('#cccccc')),
            ('LINEABOVE', (-2, -1), (-1, -1), 2, colors.HexColor('#1a1a2e')),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, len(items)), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 10*mm))

        # Bank details
        bank = data.get("bank_details", {})
        if bank:
            elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e0e0e0')))
            elements.append(Spacer(1, 3*mm))
            elements.append(Paragraph("<b>Bank Details for Payment:</b>", bold_style))
            elements.append(Spacer(1, 2*mm))
            bank_lines = [
                f"Account Name: {bank.get('account_name', '')}",
                f"Bank: {bank.get('bank_name', '')}",
                f"Account Number: {bank.get('account_number', '')}",
                f"IFSC: {bank.get('ifsc', '')}",
            ]
            if bank.get('upi_id'):
                bank_lines.append(f"UPI: {bank.get('upi_id')}")
            for line in bank_lines:
                elements.append(Paragraph(line, header_style))

        elements.append(Spacer(1, 8*mm))

        # Notes
        notes = data.get("notes", "")
        if notes:
            elements.append(Paragraph(f"<b>Notes:</b> {notes}", small_style))
            elements.append(Spacer(1, 3*mm))

        elements.append(Paragraph("This is a computer-generated invoice.", small_style))
        elements.append(Paragraph("Generated by GigPilot | AI-Powered Freelancer Copilot", small_style))

        doc.build(elements)
        return buffer.getvalue()

    def get_template(self) -> dict:
        """Return a blank invoice template with all fields."""
        return {
            "invoice_number": "",
            "date": datetime.now().strftime("%d %B %Y"),
            "due_date": (datetime.now() + timedelta(days=30)).strftime("%d %B %Y"),
            "status": "Unpaid",
            "from_name": "",
            "from_address": "",
            "from_gstin": "",
            "from_pan": "",
            "to_name": "",
            "to_address": "",
            "to_gstin": "",
            "items": [{"description": "Consulting Services", "hsn_sac": "998314", "quantity": 1, "rate": 0}],
            "gst_rate": 18,
            "is_igst": False,
            "currency": "INR",
            "bank_details": {
                "account_name": "",
                "bank_name": "",
                "account_number": "",
                "ifsc": "",
                "upi_id": "",
            },
            "notes": "Payment due within 30 days of invoice date.",
        }
