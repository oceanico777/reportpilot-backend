from fpdf import FPDF
from datetime import datetime
import os

class CleanReport(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, 'ACTA DE CIERRE DE CAJA', align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Generado por RestaurantPilot - {datetime.now().strftime("%d/%m/%Y %H:%M")}', align='C')

def generate_clearance_act(data: dict, signature_uri: str) -> bytes:
    """
    Generates a PDF clearance act for the daily closure using FPDF2.
    
    Args:
        data (dict): Dictionary containing closure details.
        signature_uri (str): Path or URI to the signature image.
        
    Returns:
        bytes: PDF content in bytes
    """
    
    # Format currency helper
    def format_currency(amount):
        return "${:,.0f}".format(amount).replace(",", ".")

    pdf = CleanReport()
    pdf.add_page()
    
    # Company Info
    pdf.set_font("Helvetica", size=14)
    pdf.cell(0, 8, data.get('company_name', 'Empresa'), align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Meta Data
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 5, f"Fecha de Cierre: {data.get('date', datetime.now().strftime('%Y-%m-%d'))}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Responsable: {data.get('owner_name', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Summary Box
    # Draw gray rectangle
    start_y = pdf.get_y()
    pdf.set_fill_color(248, 249, 250)
    pdf.rect(10, start_y, 190, 35, 'F')
    pdf.set_y(start_y + 5)
    
    # Summary Rows
    def add_summary_row(label, value, bold=False):
        if bold: pdf.set_font("Helvetica", 'B', 11)
        else: pdf.set_font("Helvetica", '', 11)
        
        # Manually positioning for left/right alignment simulation in a row
        current_y = pdf.get_y()
        pdf.set_x(15)
        pdf.cell(100, 6, label)
        
        pdf.set_x(115) # Right column start
        pdf.cell(80, 6, format_currency(value), align='R', new_x="LMARGIN", new_y="NEXT")
        
    add_summary_row("Ventas Totales:", data.get('total_sales', 0))
    add_summary_row("Total Gastos:", data.get('total_expenses', 0))

    
    pdf.set_xy(15, pdf.get_y() + 2)
    # Line separator
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(2)
    
    add_summary_row("Balance Final:", data.get('balance', 0), bold=True)
    pdf.ln(15)

    # Details Table
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 8, "Detalle de Gastos", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Table Header
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_fill_color(230, 230, 230)
    col_widths = [30, 60, 60, 40] # Date, Category, Vendor, Amount
    headers = ["Fecha", "Categoría", "Proveedor", "Monto"]
    
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, fill=True, align='C')
    pdf.ln()

    # Table Rows
    pdf.set_font("Helvetica", size=9)
    expenses = data.get('expense_details', [])
    
    if not expenses:
        pdf.cell(sum(col_widths), 10, "No hay gastos registrados", border=1, align='C', new_x="LMARGIN", new_y="NEXT")
    else:
        for expense in expenses:
            pdf.cell(col_widths[0], 8, str(expense.get('date', ''))[:10], border=1)
            pdf.cell(col_widths[1], 8, str(expense.get('category', ''))[:25], border=1) # Truncate if long
            pdf.cell(col_widths[2], 8, str(expense.get('vendor', ''))[:25], border=1)
            pdf.cell(col_widths[3], 8, format_currency(expense.get('amount', 0)), border=1, align='R', new_x="LMARGIN", new_y="NEXT")

    pdf.ln(20)

    # Signature Section
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 5, "He verificado y apruebo este cierre de caja:", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Signature Image
    # Clean URI to Path
    sig_path = signature_uri
    if sig_path.startswith("file:///"):
        # file:///C:/path -> C:/path (Windows specific handling usually needs care)
        # On Windows standard: file:///C:/Users...
        # We can use os.path.abspath if it was passed clean, or strip prefix.
        # Simplest is strip 'file:///' and then 'file://' if typical url.
        sig_path = sig_path.replace("file:///", "").replace("file://", "")
    
    # Check existence
    if os.path.exists(sig_path):
        x_center = (210 - 60) / 2 # A4 width approx 210mm
        pdf.image(sig_path, x=x_center, w=60)
        pdf.ln(2)
    else:
        pdf.cell(0, 10, "[Firma no encontrada o ruta inválida]", align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 5, "Firma del Responsable", align='C', new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
