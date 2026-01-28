from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, auth
from fastapi.responses import StreamingResponse
import pandas as pd
import io
from datetime import datetime

router = APIRouter(
    prefix="/exports",
    tags=["Exports"],
)

@router.get("/providers-excel")
def export_providers_excel(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """
    Generates an Excel file with:
    1. Summary by Provider (Total Spent)
    2. Detailed Purchase History
    """
    
    # 1. Fetch Summary Data (Provider Trends)
    # Reusing logic similar to reports.py but cleaner with pandas if we fetch all 
    
    # Fetch all purchases for company
    purchases_query = db.query(models.Purchase).filter(
        models.Purchase.company_id == current_user.company_id
    ).all()
    
    if not purchases_query:
         # raise HTTPException(status_code=404, detail="No data available to export")
         pass # Allow empty export

    # Prepare Data for DataFrame
    data = []
    for p in purchases_query:
        data.append({
            "Fecha": p.date,
            "Proveedor": p.provider.name if p.provider else (p.category or "N/A"),
            "Categoría": p.category or "General",
            "Monto": float(p.amount),
            "Items": ", ".join([i.name for i in p.items]) if p.items else ""
        })
        
    df_details = pd.DataFrame(data)
    
    # Create Summary Pivot
    if not df_details.empty:
        df_summary = df_details.groupby("Proveedor")["Monto"].sum().reset_index().sort_values("Monto", ascending=False)
    else:
        df_summary = pd.DataFrame(columns=["Proveedor", "Monto"])

    # Generate Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_summary.to_excel(writer, sheet_name="Resumen por Proveedor", index=False)
        df_details.to_excel(writer, sheet_name="Detalle de Compras", index=False)
        
        # Auto-adjust columns width (Basic approximation)
        for sheet in writer.sheets.values():
            for idx, col in enumerate(sheet.columns):
                max_len = 0
                for cell in col:
                     try: 
                        if len(str(cell.value)) > max_len: max_len = len(str(cell.value))
                     except: pass
                adjusted_width = (max_len + 2)
                sheet.column_dimensions[chr(65 + idx)].width = min(adjusted_width, 50) # Cap width

    output.seek(0)
    
    filename = f"Reporte_Proveedores_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
