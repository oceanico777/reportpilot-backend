from sqlalchemy.orm import Session
from .. import models
import time

import pytesseract
from PIL import Image
from pypdf import PdfReader
import magic
import os
import io
import platform

# Set Tesseract path for Windows
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_from_pdf(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def process_text_with_llm(text: str):
    # Placeholder for LLM processing
    # In a real app, this would send 'text' to OpenAI/Gemini to extract structured data
    return f"Processed Text (Length: {len(text)} chars). Content Preview: {text[:100]}..."

def create_report(report_id: str, db: Session):
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        return

    try:
        # 1. Read the file
        file_path = report.source_file_path
        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")

        with open(file_path, "rb") as f:
            contents = f.read()

        # 2. Detect file type
        # Note: python-magic might need system dependencies. 
        # Fallback to extension if magic fails or returns generic type could be added.
        try:
            file_type = magic.from_buffer(contents, mime=True)
        except Exception as e:
            print(f"Magic failed: {e}, falling back to extension")
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.csv': file_type = 'text/csv'
            elif ext == '.pdf': file_type = 'application/pdf'
            elif ext in ['.jpg', '.jpeg']: file_type = 'image/jpeg'
            elif ext == '.png': file_type = 'image/png'
            else: file_type = 'unknown'

        text_data = ""

        # 3. Extract Text
        if file_type == 'application/pdf':
            text_data = extract_text_from_pdf(contents)

        elif file_type == 'text/csv' or file_type == 'text/plain':
            text_data = contents.decode('utf-8')

        elif file_type in ['image/jpeg', 'image/png']:
            try:
                image = Image.open(io.BytesIO(contents))
                text_data = pytesseract.image_to_string(image)
            except Exception as e:
                raise Exception(f"OCR Failed: {str(e)}")
        
        else:
            raise Exception(f"Unsupported file type: {file_type}")

        if not text_data:
            raise Exception("No text extracted from file.")

        # 4. Process with LLM (Mock)
        processed_summary = process_text_with_llm(text_data)
        
        # 5. Update Report
        report.summary_text = processed_summary
        report.file_url = f"https://example.com/reports/{report.id}.pdf" # Mock URL
        report.status = models.ReportStatus.SENT.value # Success
        
    except Exception as e:
        print(f"Error generating report {report_id}: {e}")
        report.status = models.ReportStatus.FAILED.value
        report.summary_text = f"Error: {str(e)}"
    
    finally:
        db.commit()

def generate_tour_summary(reports):
    """
    Aggregates reports by Tour ID and Category for the Admin View.
    Returns a dictionary structure.
    """
    tour_map = {}
    
    for r in reports:
        tid = r.tour_id or "Unassigned"
        if tid not in tour_map:
            tour_map[tid] = {
                "tour_id": tid,
                "total_amount": 0.0,
                "reports_count": 0,
                "categories": {},
                "guide_id": r.user_id,
                "guide_name": r.client_name,
                "has_duplicates": False
            }
        
        if r.is_duplicate:
            tour_map[tid]["has_duplicates"] = True

        amount = r.amount or 0
        cat = r.category or "📦 Otros"
        
        tour_map[tid]["total_amount"] += amount
        tour_map[tid]["reports_count"] += 1
        tour_map[tid]["categories"][cat] = tour_map[tid]["categories"].get(cat, 0) + amount

    return list(tour_map.values())

def generate_excel_report(reports):
    """
    Generates a professional Excel report with Financial Summary and Details.
    Returns bytes buffer.
    """
    import pandas as pd
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    # 1. Prepare Data & Calculations
    data = []
    
    total_advances = 0
    total_collections = 0
    total_expenses = 0
    
    # Financial Categories mapping
    INCOME_CATEGORIES = ["ANTICIPO_RECIBIDO", "RECAUDO_CLIENTE"]
    
    for r in reports:
        amount = r.amount or 0
        cat = r.category or "📦 Otros"
        
        # Financial Sums
        if cat == "ANTICIPO_RECIBIDO":
            total_advances += amount
        elif cat == "RECAUDO_CLIENTE":
            total_collections += amount
        else:
            total_expenses += amount
            
        data.append({
            "ID Reporte": r.id,
            "Fecha": r.created_at.strftime("%d/%m/%Y") if r.created_at else "",
            "Tour ID": r.tour_id or "Sin Asignar",
            "Guía": r.client_name or "Desconocido",
            "Proveedor": r.vendor,
            "NIT": r.vendor_nit or "No Detectado", # NEW
            "Categoría": cat,
            "Descripción": r.summary_text,
            "Monto (COP)": amount,
            "Estado": r.status or "BORRADOR"
        })
        
    df = pd.DataFrame(data)

    # Calculate Net Balance (Liability)
    # Logic: Liability = (Advances + Collections) - Expenses
    # If Positive: Guide owes agency (Reintegrar)
    # If Negative: Agency owes guide (Reembolsar)
    net_balance = (total_advances + total_collections) - total_expenses
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # --- SHEET 1: LIQUIDATION SUMMARY ---
        # Create a summary dataframe structure
        summary_data = {
            "Concepto": [
                "TOTAL ANTICIPOS RECIBIDOS",
                "TOTAL RECAUDOS CLIENTE",
                "SUBTOTAL INGRESOS (Responsabilidad)",
                "TOTAL GASTOS LEGALIZADOS",
                "BALANCE NETO (A LIQUIDAR)"
            ],
            "Monto": [
                total_advances,
                total_collections,
                total_advances + total_collections,
                total_expenses,
                net_balance
            ]
        }
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Resumen Liquidación', startrow=3, index=False)
        
        workbook = writer.book
        ws_summary = writer.sheets['Resumen Liquidación']
        
        # Styles
        header_font = Font(bold=True, color="FFFFFF", size=12)
        header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid") # Dark Slate
        currency_format = '"$" #,##0'
        border_style = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

        # Title
        ws_summary['A1'] = "LIQUIDACIÓN DE GASTOS DE VIAJE"
        ws_summary['A1'].font = Font(bold=True, size=16, color="0F172A")
        ws_summary.merge_cells('A1:B1')
        
        # Tour Info
        if not df.empty:
            tour_id = df.iloc[0]["Tour ID"]
            guide_name = df.iloc[0]["Guía"]
            ws_summary['A2'] = f"Tour ID: {tour_id} | Guía: {guide_name}"
        else:
            ws_summary['A2'] = "Sin datos de reporte"
            
        ws_summary['A2'].font = Font(bold=True, italic=True, size=11, color="64748B")

        # Format Summary Table
        # Headers (Row 4)
        for cell in ws_summary[4]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
        
        # Data Rows (Row 5 to 9)
        for row in ws_summary.iter_rows(min_row=5, max_row=9, min_col=1, max_col=2):
            for cell in row:
                cell.border = border_style
                if cell.column == 2: # Amount Column
                    cell.number_format = currency_format
                    cell.font = Font(name='Courier New', bold=True)
        
        # Highlight Net Balance (Last Row)
        last_row = 9
        balance_cell = ws_summary.cell(row=last_row, column=2)
        if net_balance > 0:
            status_text = "⚠️ EL GUÍA DEBE REINTEGRAR"
            balance_cell.font = Font(bold=True, color="DC2626") # Red
        elif net_balance < 0:
            status_text = "🔵 LA AGENCIA DEBE REEMBOLSAR"
            balance_cell.font = Font(bold=True, color="2563EB") # Blue
        else:
            status_text = "✅ CUADRE PERFECTO"
            balance_cell.font = Font(bold=True, color="16A34A") # Green
            
        ws_summary.cell(row=last_row, column=3, value=status_text).font = Font(bold=True)

        # Warning Note for Unbalanced Closure
        if abs(net_balance) > 1000:
            ws_summary.cell(row=last_row + 2, column=1, value="⚠️ NOTA: Liquidación con Diferencia Pendiente (> $1.000 COP)").font = Font(bold=True, color="DC2626", size=11)

        # Adjust Column Widths
        ws_summary.column_dimensions['A'].width = 40
        ws_summary.column_dimensions['B'].width = 25
        ws_summary.column_dimensions['C'].width = 35

        # --- SHEET 2: DETAILED REPORTS ---
        if not df.empty:
            df.to_excel(writer, sheet_name='Detalle Movimientos', index=False, startrow=1)
            ws_details = writer.sheets['Detalle Movimientos']
            
            # Title
            ws_details['A1'] = "DETALLE DE MOVIMIENTOS"
            ws_details['A1'].font = Font(bold=True, size=14)
            
            # Headers Customization
            for cell in ws_details[2]: # Row 2 because startrow=1
                cell.font = header_font
                cell.fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid") # Lighter Slate
                cell.alignment = Alignment(horizontal='center')
            
            # Auto-filter
            ws_details.auto_filter.ref = ws_details.dimensions
            
            # Formatting Columns
            for row in ws_details.iter_rows(min_row=3):
                currency_cell = row[8] # 'Monto (COP)' is now 9th column (0-indexed 8) because of NIT
                currency_cell.number_format = currency_format
                
            # Adjust Widths
            for col in ws_details.columns:
                max_length = 0
                column = [cell for cell in col]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = (max_length + 2) if max_length < 50 else 50
                ws_details.column_dimensions[get_column_letter(column[0].column)].width = adjusted_width

    output.seek(0)
    return output

def generate_clearance_act(tour_data, signature_path):
    """
    Generates a PDF 'Acta de Liquidación' using WeasyPrint.
    Returns bytes buffer.
    """
    import logging
    from weasyprint import HTML, CSS
    
    # 1. Prepare Data
    company_name = tour_data.get("company_name", "Empresa de Turismo")
    tour_id = tour_data.get("tour_id", "Unknown")
    guide_name = tour_data.get("guide_name", "Unknown")
    closed_at = tour_data.get("closed_at", datetime.now()).strftime("%d/%m/%Y %H:%M")
    
    advances = tour_data.get("total_advances", 0)
    collections = tour_data.get("total_collections", 0)
    expenses = tour_data.get("total_expenses", 0)
    balance = (advances + collections) - expenses
    
    balance_text = ""
    if balance > 0:
        balance_text = f"EL GUÍA DEBE REINTEGRAR: ${balance:,.0f} COP"
        balance_color = "#dc2626"
    elif balance < 0:
        balance_text = f"LA AGENCIA DEBE REEMBOLSAR: ${abs(balance):,.0f} COP"
        balance_color = "#2563eb"
    else:
        balance_text = "PAZ Y SALVO (Saldo $0)"
        balance_color = "#16a34a"

    # 2. HTML Template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Helvetica', sans-serif; color: #334155; line-height: 1.6; }}
            .header {{ text-align: center; margin-bottom: 2rem; border-bottom: 2px solid #0f172a; padding-bottom: 1rem; }}
            .title {{ font-size: 24px; font-weight: bold; color: #0f172a; }}
            .subtitle {{ font-size: 14px; color: #64748b; }}
            .section {{ margin-bottom: 1.5rem; }}
            .label {{ font-weight: bold; font-size: 12px; color: #64748b; text-transform: uppercase; }}
            .value {{ font-size: 16px; font-weight: 500; color: #0f172a; }}
            .table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
            .table th {{ text-align: left; background: #f1f5f9; padding: 8px; font-size: 12px; text-transform: uppercase; }}
            .table td {{ padding: 8px; border-bottom: 1px solid #e2e8f0; }}
            .balance-box {{ 
                margin-top: 2rem; padding: 1.5rem; border-radius: 8px; text-align: center;
                background: {balance_color}10; border: 2px solid {balance_color}; 
            }}
            .balance-title {{ color: {balance_color}; font-weight: bold; font-size: 18px; }}
            .declaration {{ margin-top: 3rem; font-size: 12px; color: #64748b; text-align: justify; }}
            .signature-section {{ margin-top: 4rem; text-align: center; }}
            .signature-line {{ border-top: 1px solid #cbd5e1; width: 300px; margin: 0 auto 10px auto; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="title">ACTA DE LIQUIDACIÓN DE TOUR</div>
            <div class="subtitle">{company_name} | Ref: {tour_id}</div>
        </div>

        <div class="section">
            <div class="label">Responsable del Tour</div>
            <div class="value">{guide_name}</div>
            <div class="label" style="margin-top: 10px;">Fecha de Cierre</div>
            <div class="value">{closed_at}</div>
        </div>

        <div class="section">
            <div class="label">Resumen Financiero</div>
            <table class="table">
                <tr>
                    <th>Concepto</th>
                    <th style="text-align: right;">Monto (COP)</th>
                </tr>
                <tr>
                    <td>(+) Anticipos Recibidos</td>
                    <td style="text-align: right;">${advances:,.0f}</td>
                </tr>
                <tr>
                    <td>(+) Recaudos de Clientes</td>
                    <td style="text-align: right;">${collections:,.0f}</td>
                </tr>
                <tr>
                    <td>(-) Total Gastos Legalizados</td>
                    <td style="text-align: right;">-${expenses:,.0f}</td>
                </tr>
            </table>
        </div>

        <div class="balance-box">
            <div class="label">Balance Final</div>
            <div class="balance-title">{balance_text}</div>
        </div>
        
        <div class="declaration">
            DECLARACIÓN DE PAZ Y SALVO:
            <br><br>
            Yo, <b>{guide_name}</b>, declaro que los valores aquí reportados son verídicos y que he legalizado la totalidad del efectivo a mi cargo.
            <br>
            Al firmar este documento, acepto el balance final resultante y libero a {company_name} de cualquier reclamación futura relacionada con estos gastos, así como la empresa me extiende el correspondiente paz y salvo una vez liquidado el saldo pendiente.
        </div>

        <div class="signature-section">
            <img src="{signature_path}" width="200" style="margin-bottom: 2rem;" />
            <div class="signature-line"></div>
            <div class="value">{guide_name}</div>
            <div class="label">Firma del Guía / Responsable</div>
        </div>

        <div style="position: absolute; bottom: 20px; width: 100%; text-align: center; font-size: 10px; color: #94a3b8;">
            Generado por ReportPilot AI el {datetime.now().strftime("%d/%m/%Y %H:%M")}
        </div>
    </body>
    </html>
    """

    # 3. Generate PDF
    try:
        pdf_file = HTML(string=html_content, base_url=".").write_pdf()
        return pdf_file
    except Exception as e:
        logging.error(f"Error generating PDF: {e}")
        return None
