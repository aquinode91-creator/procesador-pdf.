import streamlit as st
import re
import tempfile
import zipfile
from io import BytesIO
from fpdf import FPDF
import base64

# Configuración de página
st.set_page_config(page_title="Procesador de Viajes", page_icon="📦", layout="wide")
st.title("📦 Procesador de Viajes - Resumen PDF")
st.markdown("---")

# =======================================================
# FUNCIONES PRINCIPALES CON FPDF
# =======================================================

class PDFResumen(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'RESUMEN DE VIAJE', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def crear_resumen_pdf(orden, fletero, datos_facturas):
    pdf = PDFResumen()
    pdf.add_page()
    
    # Información del viaje
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f'Orden de Transporte: {orden}', 0, 1)
    pdf.cell(0, 10, f'Fletero: {fletero}', 0, 1)
    pdf.ln(10)
    
    # Encabezados de tabla
    pdf.set_font('Arial', 'B', 8)
    pdf.cell(15, 10, 'N°', 1, 0, 'C')
    pdf.cell(45, 10, 'Señor(es)', 1, 0, 'C')
    pdf.cell(45, 10, 'Razón Social', 1, 0, 'C')
    pdf.cell(30, 10, 'Distrito', 1, 0, 'C')
    pdf.cell(25, 10, 'Vendedor', 1, 0, 'C')
    pdf.cell(30, 10, 'Total a Pagar', 1, 1, 'C')
    
    # Datos de facturas
    pdf.set_font('Arial', '', 7)
    for i, factura in enumerate(datos_facturas, 1):
        if pdf.get_y() > 260:  # Salto de página si falta espacio
            pdf.add_page()
            # Volver a poner encabezados
            pdf.set_font('Arial', 'B', 8)
            pdf.cell(15, 10, 'N°', 1, 0, 'C')
            pdf.cell(45, 10, 'Señor(es)', 1, 0, 'C')
            pdf.cell(45, 10, 'Razón Social', 1, 0, 'C')
            pdf.cell(30, 10, 'Distrito', 1, 0, 'C')
            pdf.cell(25, 10, 'Vendedor', 1, 0, 'C')
            pdf.cell(30, 10, 'Total a Pagar', 1, 1, 'C')
            pdf.set_font('Arial', '', 7)
        
        pdf.cell(15, 8, str(i), 1, 0, 'C')
        pdf.cell(45, 8, factura.get('senor', '-')[:20], 1, 0)
        pdf.cell(45, 8, factura.get('razon_social', '-')[:20], 1, 0)
        pdf.cell(30, 8, factura.get('distrito', '-')[:15], 1, 0)
        pdf.cell(25, 8, factura.get('vendedor', '-')[:12], 1, 0)
        pdf.cell(30, 8, f"₲ {factura.get('total_a_pagar', 0):,}", 1, 1, 'R')
    
    # Resumen de totales
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    total_general = sum(float(factura.get('total_a_pagar', 0)) for factura in datos_facturas)
    pdf.cell(0, 10, f'TOTAL GENERAL: ₲ {total_general:,.0f}', 0, 1, 'R')
    
    # Guardar PDF
    pdf_buffer = BytesIO()
    pdf_output = pdf.output(dest='S').encode('latin1')
    pdf_buffer.write(pdf_output)
    pdf_buffer.seek(0)
    
    return pdf_buffer

def procesar_texto_pdf(texto):
    """Procesa el texto del PDF y extrae la información estructurada"""
    datos_facturas = []
    
    # Patrones de búsqueda
    patrones = {
        'orden': re.compile(r"Orden\s+de\s+Transporte\s*:\s*([A-Za-z0-9\-_]+)", re.IGNORECASE),
        'fletero': re.compile(r"Fletero\s*:\s*(.+)", re.IGNORECASE),
        'factura': re.compile(r"Nº\s*([0-9-]+)", re.IGNORECASE),
        'senor': re.compile(r"Señor\(es\):\s*(.+)", re.IGNORECASE),
        'razon_social': re.compile(r"Razón\s*Social\s*:\s*(.+)", re.IGNORECASE),
        'distrito': re.compile(r"Distrito\s*:\s*(.+)", re.IGNORECASE),
        'vendedor': re.compile(r"Vendedor\s*:\s*(.+)", re.IGNORECASE),
        'total_a_pagar': re.compile(r"TOTAL\s+A\s+PAGAR\s*[,:]?\s*([\d\.,]+)", re.IGNORECASE),
        'plazo': re.compile(r"Plazo\s*:\s*(.+)", re.IGNORECASE),
        'forma_pago': re.compile(r"Forma\s+de\s+Pago\s*:\s*(.+)", re.IGNORECASE)
    }
    
    # Dividir por páginas o secciones
    secciones = texto.split('Orden de Transporte:')
    
    for seccion in secciones[1:]:  # Saltar la primera (vacía)
        factura_data = {}
        
        # Buscar orden
        match_orden = patrones['orden'].search('Orden de Transporte:' + seccion)
        if match_orden:
            factura_data['orden'] = match_orden.group(1).strip()
        
        # Buscar fletero
        match_fletero = patrones['fletero'].search(seccion)
        if match_fletero:
            factura_data['fletero'] = match_fletero.group(1).strip().split('\n')[0]
        
        # Buscar número de factura
        match_factura = patrones['factura'].search(seccion)
        if match_factura:
            factura_data['factura'] = match_factura.group(1).strip()
        
        # Buscar otros campos
        for campo, patron in patrones.items():
            if campo in ['orden', 'fletero', 'factura']:
                continue
            match = patron.search(seccion)
            if match:
                valor = match.group(1 if campo != 'total_a_pagar' else 1).strip()
                if campo == 'total_a_pagar':
                    # Convertir formato de número
                    valor = float(valor.replace('.', '').replace(',', '.'))
                factura_data[campo] = valor
        
        if factura_data.get('factura'):
            datos_facturas.append(factura_data)
    
    return datos_facturas

# =======================================================
# INTERFAZ STREAMLIT
# =======================================================

st.markdown("""
### 📋 Instrucciones:
1. **Sube tu PDF** con las órdenes de transporte
2. **La aplicación procesará** automáticamente los datos
3. **Descarga el resumen** en formato PDF organizado
""")

uploaded_file = st.file_uploader("Selecciona tu archivo PDF", type="pdf")

if uploaded_file is not None:
    with st.spinner("Procesando PDF... Esto puede tomar unos segundos"):
        try:
            # Leer PDF usando PyPDF2 (más estable)
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            
            # Extraer texto de todas las páginas
            texto_completo = ""
            for pagina in pdf_reader.pages:
                texto_completo += pagina.extract_text() + "\n---\n"
            
            # Procesar el texto
            datos_facturas = procesar_texto_pdf(texto_completo)
            
            if datos_facturas:
                st.success(f"✅ PDF procesado correctamente")
                st.info(f"📊 Se encontraron **{len(datos_facturas)}** facturas en el documento")
                
                # Agrupar por orden de transporte
                ordenes = {}
                for factura in datos_facturas:
                    orden = factura.get('orden', 'Sin orden')
                    if orden not in ordenes:
                        ordenes[orden] = []
                    ordenes[orden].append(factura)
                
                # Crear ZIP con todos los resúmenes
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                    for orden, facturas in ordenes.items():
                        fletero = facturas[0].get('fletero', 'No especificado') if facturas else 'No especificado'
                        
                        # Crear PDF para esta orden
                        pdf_buffer = crear_resumen_pdf(orden, fletero, facturas)
                        
                        # Agregar al ZIP
                        zip_file.writestr(f"resumen_{orden}.pdf", pdf_buffer.getvalue())
                
                zip_buffer.seek(0)
                
                # Mostrar resumen
                st.subheader("📊 Resumen de Órdenes Encontradas")
                for orden, facturas in ordenes.items():
                    total_orden = sum(float(f.get('total_a_pagar', 0)) for f in facturas)
                    fletero = facturas[0].get('fletero', 'No especificado') if facturas else 'No especificado'
                    
                    col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
                    with col1:
                        st.write(f"**{orden}**")
                    with col2:
                        st.write(fletero)
                    with col3:
                        st.write(f"{len(facturas)} facturas")
                    with col4:
                        st.write(f"₲ {total_orden:,.0f}")
                
                # Total general
                total_general = sum(float(f.get('total_a_pagar', 0)) for f in datos_facturas)
                st.metric("💰 **TOTAL GENERAL**", f"₲ {total_general:,.0f}")
                
                # Botón de descarga
                st.download_button(
                    label="📥 Descargar Todos los Resúmenes (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="resumenes_viajes.zip",
                    mime="application/zip",
                    type="primary"
                )
                
            else:
                st.warning("⚠️ No se encontraron órdenes de transporte en el PDF")
                st.info("💡 Asegúrate de que el PDF contenga campos como 'Orden de Transporte', 'Nº factura', etc.")
                
        except Exception as e:
            st.error(f"❌ Error al procesar el PDF: {str(e)}")
            st.info("""
            **Posibles soluciones:**
            - Verifica que el PDF no esté protegido con contraseña
            - Asegúrate de que el texto sea seleccionable (no escaneado)
            - Revisa que el formato coincida con el esperado
            """)

# Información adicional
with st.expander("ℹ️ Acerca de esta aplicación"):
    st.markdown("""
    **Funcionalidades incluidas:**
    - ✅ Procesamiento automático de PDFs
    - ✅ Extracción de órdenes de transporte
    - ✅ Agrupación por cliente y orden
    - ✅ Generación de resúmenes en PDF
    - ✅ Cálculo de totales automático
    - ✅ Descarga en formato ZIP organizado
    
    **Campos que detecta:**
    - Orden de Transporte
    - Fletero
    - Nº de factura
    - Señor(es)
    - Razón Social
    - Distrito
    - Vendedor
    - Total a Pagar
    - Plazo
    - Forma de Pago
    """)

st.markdown("---")
st.caption("Procesador de Viajes v2.0 - Para uso interno")
