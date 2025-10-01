import streamlit as st
import re
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from io import BytesIO
import tempfile
import zipfile
import base64

st.title("📦 Procesador de Viajes - VERSIÓN FUNCIONAL")
st.write("Sube tu PDF para generar el resumen ejecutivo")

# =======================================================
# FUNCIONES SIMPLIFICADAS (sin pypdf)
# =======================================================
def wrap_text(c, text, max_width, font_name, font_size):
    c.setFont(font_name, font_size)
    if not text or str(text).strip() == "":
        return ["-"]
    words = str(text).split()
    lines, current_line = [], words[0]
    for word in words[1:]:
        if c.stringWidth(f"{current_line} {word}", font_name, font_size) < max_width:
            current_line += f" {word}"
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    return lines

def crear_resumen_pdf(datos_viajes):
    """Crea un PDF de resumen usando solo reportlab"""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    ancho, alto = landscape(A4)
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, alto - 50, "Resumen de Viajes Procesados")
    
    # Información básica
    c.setFont("Helvetica", 10)
    c.drawString(50, alto - 80, f"Total de viajes procesados: {len(datos_viajes)}")
    
    # Ejemplo de tabla simple
    y_pos = alto - 120
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y_pos, "Orden de Transporte")
    c.drawString(200, y_pos, "Fletero")
    c.drawString(350, y_pos, "Total Facturas")
    
    y_pos -= 20
    c.setFont("Helvetica", 8)
    
    for viaje in datos_viajes[:10]:  # Mostrar primeros 10
        c.drawString(50, y_pos, viaje.get('orden', 'N/A'))
        c.drawString(200, y_pos, viaje.get('fletero', 'N/A'))
        c.drawString(350, y_pos, str(viaje.get('total_facturas', 0)))
        y_pos -= 15
        
        if y_pos < 100:
            c.showPage()
            y_pos = alto - 50
            c.setFont("Helvetica", 8)
    
    c.save()
    buffer.seek(0)
    return buffer

def extraer_datos_simples(texto):
    """Extrae datos básicos sin procesar PDF complejo"""
    datos = {}
    
    # Patrones simples
    orden_pattern = re.compile(r"Orden\s+de\s+Transporte\s*:\s*([A-Za-z0-9\-_]+)", re.IGNORECASE)
    fletero_pattern = re.compile(r"Fletero\s*:\s*(.+)", re.IGNORECASE)
    factura_pattern = re.compile(r"Nº\s*([0-9-]+)", re.IGNORECASE)
    
    match_orden = orden_pattern.search(texto)
    if match_orden:
        datos['orden'] = match_orden.group(1).strip()
    
    match_fletero = fletero_pattern.search(texto)
    if match_fletero:
        datos['fletero'] = match_fletero.group(1).strip().split('\n')[0]
    
    facturas = factura_pattern.findall(texto)
    datos['total_facturas'] = len(set(facturas))
    
    return datos

# =======================================================
# INTERFAZ PRINCIPAL
# =======================================================
uploaded_file = st.file_uploader("Sube tu archivo PDF", type="pdf")

if uploaded_file is not None:
    with st.spinner("Procesando PDF..."):
        try:
            # Leer contenido del PDF (versión simple)
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            
            datos_viajes = []
            for page in pdf_reader.pages:
                texto = page.extract_text() or ""
                datos = extraer_datos_simples(texto)
                if datos.get('orden'):
                    datos_viajes.append(datos)
            
            if datos_viajes:
                st.success(f"✅ PDF procesado correctamente")
                st.write(f"📊 Se encontraron {len(datos_viajes)} órdenes de transporte")
                
                # Crear resumen PDF
                pdf_buffer = crear_resumen_pdf(datos_viajes)
                
                # Botón de descarga
                st.download_button(
                    label="📥 Descargar Resumen PDF",
                    data=pdf_buffer.getvalue(),
                    file_name="resumen_viajes.pdf",
                    mime="application/pdf"
                )
                
                # Mostrar resumen en tabla
                st.subheader("Resumen de Órdenes Encontradas")
                for viaje in datos_viajes:
                    st.write(f"**Orden {viaje.get('orden')}** - Fletero: {viaje.get('fletero', 'N/A')} - Facturas: {viaje.get('total_facturas')}")
                    
            else:
                st.warning("⚠️ No se encontraron órdenes de transporte en el PDF")
                
        except Exception as e:
            st.error(f"❌ Error al procesar el PDF: {str(e)}")
            st.info("💡 Asegúrate de que el PDF tenga el formato correcto con 'Orden de Transporte'")

st.info("""
**Funcionalidades incluidas:**
- ✅ Procesamiento básico de PDF
- ✅ Extracción de órdenes de transporte  
- ✅ Generación de resumen ejecutivo
- ✅ Descarga de resultados
""")

