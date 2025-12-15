from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date
import io
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from weasyprint import HTML, CSS
from jinja2 import Template

from app.database import get_db
from app import models
from app.auth import get_current_user

router = APIRouter(prefix="/exports", tags=["exports"])

# --- HTML TEMPLATE FOR PDF ---
PDF_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: sans-serif; font-size: 10pt; color: #333; }
        h1 { text-align: center; color: #1a1a1a; margin-bottom: 5px; }
        .subtitle { text-align: center; color: #666; font-size: 9pt; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th { background-color: #f3f4f6; text-align: left; padding: 8px; font-weight: bold; border-bottom: 2px solid #ddd; font-size: 9pt; }
        td { padding: 8px; border-bottom: 1px solid #eee; font-size: 9pt; }
        .amount { text-align: right; font-family: monospace; }
        .total-row td { border-top: 2px solid #333; font-weight: bold; background-color: #fff; }
        .footer { position: fixed; bottom: 0; width: 100%; text-align: center; font-size: 8pt; color: #999; }
    </style>
</head>
<body>
    <h1>Reporte de Gastos</h1>
    <div class="subtitle">
        Generado para: {{ user_name }}<br>
        Periodo: {{ start_date }} - {{ end_date }}
    </div>

    <table>
        <thead>
            <tr>
                <th style="width: 15%">Fecha</th>
                <th style="width: 25%">Proveedor</th>
                <th style="width: 25%">Categoría</th>
                <th style="width: 20%">Cliente/Tour</th>
                <th style="width: 15%; text-align: right">Monto (COP)</th>
            </tr>
        </thead>
        <tbody>
            {% for r in reports %}
            <tr>
                <td>{{ r.date }}</td>
                <td>{{ r.vendor }}</td>
                <td>{{ r.category }}</td>
                <td>{{ r.tour }}</td>
                <td class="amount">{{ r.amount }}</td>
            </tr>
            {% endfor %}
            <tr class="total-row">
                <td colspan="4" style="text-align: right">TOTAL</td>
                <td class="amount">{{ total_amount }}</td>
            </tr>
        </tbody>
    </table>

    <div class="footer">
        Generado por ReportPilot - {{ now }}
    </div>
</body>
</html>
"""

def format_currency(amount):
    return "${:,.0f}".format(amount).replace(",", ".")

@router.get("/gastos")
def export_gastos(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    format: str = Query(..., regex="^(pdf|xlsx)$"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # 1. Query Data
    query = db.query(models.Report).filter(models.Report.company_id == current_user["company_id"])
    
    if start_date:
        query = query.filter(models.Report.created_at >= start_date)
    if end_date:
        # End of day
        query = query.filter(models.Report.created_at <= datetime.combine(end_date, datetime.max.time()))
        
    reports = query.order_by(models.Report.created_at.desc()).all()
    
    # Pre-process data
    data_list = []
    total = 0
    for r in reports:
        amt = r.amount or 0
        total += amt
        data_list.append({
            "date": r.created_at.strftime("%Y-%m-%d"),
            "vendor": r.vendor or "N/A",
            "category": r.category or "Sin Categoría",
            "tour": r.tour_id or "-",
            "amount_raw": amt,
            "amount": format_currency(amt)
        })

    # 2. GENERATE FILE
    
    if format == "pdf":
        context = {
            "user_name": current_user["full_name"],
            "start_date": start_date or "Inicio",
            "end_date": end_date or "Hoy",
            "reports": data_list,
            "total_amount": format_currency(total),
            "now": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        template = Template(PDF_TEMPLATE)
        html_content = template.render(context)
        
        pdf_file = HTML(string=html_content).write_pdf()
        
        filename = f"Gastos_{start_date or 'Inicio'}_{end_date or 'Hoy'}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_file),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    elif format == "xlsx":
        wb = Workbook()
        ws = wb.active
        ws.title = "Gastos"
        
        # Headers
        headers = ["Fecha", "Proveedor", "Categoría", "Detalle/Tour", "Monto", "Impuestos", "Total", "Comentarios"]
        ws.append(headers)
        
        # Style Headers
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
        
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        # Rows
        for item in data_list:
            ws.append([
                item["date"],
                item["vendor"],
                item["category"],
                item["tour"],
                item["amount_raw"], # Monto
                0, # Impuestos (Placeholder)
                item["amount_raw"], # Total
                "" # Comentarios
            ])
            
        # Column Widths
        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 25
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 25
        ws.column_dimensions['E'].width = 15

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"Gastos_Export_{start_date or 'All'}.xlsx"
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
