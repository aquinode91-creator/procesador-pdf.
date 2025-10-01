import streamlit as st
import pdfplumber
import re
import zipfile
from io import BytesIO

st.set_page_config(page_title="Procesador de Viajes", page_icon="📦", layout="wide")
st.title("📦 Procesador de Viajes - Resumen PDF")
st.markdown("---")

# Funciones de procesamiento (las mismas que antes)
def crear_resumen_html(orden, fletero, datos_facturas):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }}
            .table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            .table th, .table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            .table th {{ background-color: #f2f2f2; font-weight: bold; }}
            .total {{ font-weight: bold; text-align: right; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>RESUMEN DE VIAJE</h1>
            <h3>Orden: {orden} | Fletero: {fletero}</h3>
        </div>
        <table class="table">
            <thead><tr><th>N°</th><th>Factura</th><th>Señor(es)</th><th>Total</th></tr></thead>
            <tbody>
    """
    
    for i, factura in enumerate(datos_facturas, 1):
        html_content += f"<tr><td>{i}</td><td>{factura.get('factura','-')}</td><td>{factura.get('senor','-')}</td><td>₲ {factura.get('total_a_pagar',0):,.0f}</td></tr>"
    
    total = sum(f.get('total_a_pagar',0) for f in datos_facturas)
    html_content += f"</tbody></table><div class='total'><h3>TOTAL: ₲ {total:,.0f}</h3></div></body></html>"
    return html_content

def procesar_pdf(uploaded_file):
    datos_facturas = []
    
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            texto = page.extract_text() or ""
            
            # Buscar patrones
            patrones = {
                'orden': re.compile(r"Orden\s+de\s+Transporte\s*:\s*([A-Za-z0-9\-_]+)", re.IGNORECASE),
                'fletero': re.compile(r"Fletero\s*:\s*(.+)", re.IGNORECASE),
                'factura': re.compile(r"Nº\s*([0-9-]+)", re.IGNORECASE),
                'senor': re.compile(r"Señor\(es\):\s*(.+)", re.IGNORECASE),
                'total_a_pagar': re.compile(r"TOTAL\s+A\s+PAGAR\s*[,:]?\s*([\d\.,]+)", re.IGNORECASE)
            }
            
            # Procesar datos
            factura_match = patrones['factura'].search(texto)
            if factura_match:
                factura_data = {'factura': factura_match.group(1)}
                
                for campo, patron in patrones.items():
                    if campo != 'factura':
                        match = patron.search(texto)
                        if match:
                            valor = match.group(1).strip()
                            if campo == 'total_a_pagar':
                                try:
                                    valor = float(valor.replace('.', '').replace(',', '.'))
                                except:
                                    valor = 0.0
                            factura_data[campo] = valor
                
                datos_facturas.append(factura_data)
    
    return datos_facturas

# Interfaz principal
uploaded_file = st.file_uploader("📤 Sube tu PDF", type="pdf")

if uploaded_file is not None:
    with st.spinner("Procesando PDF..."):
        try:
            datos = procesar_pdf(uploaded_file)
            
            if datos:
                st.success(f"✅ PDF procesado - {len(datos)} facturas encontradas")
                
                # Crear resumen
                orden = datos[0].get('orden', 'N/A')
                fletero = datos[0].get('fletero', 'N/A')
                html_content = crear_resumen_html(orden, fletero, datos)
                
                st.download_button(
                    "📥 Descargar Resumen HTML",
                    html_content,
                    f"resumen_{orden}.html",
                    "text/html"
                )
                
                # Mostrar preview
                with st.expander("📊 Vista previa de datos"):
                    for factura in datos:
                        st.write(f"**{factura.get('factura')}** - {factura.get('senor')} - ₲ {factura.get('total_a_pagar',0):,.0f}")
            else:
                st.warning("No se encontraron datos en el PDF")
                
        except Exception as e:
            st.error(f"Error: {e}")

st.markdown("---")
st.caption("Procesador de Viajes - Con PDF real")
