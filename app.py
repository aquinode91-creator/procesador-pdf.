import streamlit as st
import re
import zipfile
from io import BytesIO
import base64

# Configuración de página
st.set_page_config(page_title="Procesador de Viajes", page_icon="📦", layout="wide")
st.title("📦 Procesador de Viajes - Resumen Ejecutivo")
st.markdown("---")

# =======================================================
# FUNCIONES PRINCIPALES
# =======================================================

def crear_resumen_html(orden, fletero, datos_facturas):
    """Crea un resumen en HTML en lugar de PDF"""
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
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>RESUMEN DE VIAJE</h1>
            <h3>Orden de Transporte: {orden}</h3>
            <h3>Fletero: {fletero}</h3>
        </div>
        
        <table class="table">
            <thead>
                <tr>
                    <th>N°</th>
                    <th>Señor(es)</th>
                    <th>Razón Social</th>
                    <th>Distrito</th>
                    <th>Vendedor</th>
                    <th>Total a Pagar</th>
                </tr>
            </thead>
            <tbody>
    """
    
    total_general = 0
    for i, factura in enumerate(datos_facturas, 1):
        senor = factura.get('senor', '-')[:30]
        razon_social = factura.get('razon_social', '-')[:30]
        distrito = factura.get('distrito', '-')[:20]
        vendedor = factura.get('vendedor', '-')[:15]
        total = float(factura.get('total_a_pagar', 0))
        total_general += total
        
        html_content += f"""
                <tr>
                    <td>{i}</td>
                    <td>{senor}</td>
                    <td>{razon_social}</td>
                    <td>{distrito}</td>
                    <td>{vendedor}</td>
                    <td>₲ {total:,.0f}</td>
                </tr>
        """
    
    html_content += f"""
            </tbody>
        </table>
        
        <div class="total">
            <h3>TOTAL GENERAL: ₲ {total_general:,.0f}</h3>
        </div>
        
        <div class="footer">
            <p>Generado automáticamente por Procesador de Viajes</p>
        </div>
    </body>
    </html>
    """
    
    return html_content

def crear_resumen_txt(orden, fletero, datos_facturas):
    """Crea un resumen en texto plano"""
    txt_content = f"RESUMEN DE VIAJE\n"
    txt_content += f"{'='*50}\n"
    txt_content += f"Orden de Transporte: {orden}\n"
    txt_content += f"Fletero: {fletero}\n"
    txt_content += f"{'='*50}\n\n"
    
    txt_content += f"{'N°':<3} {'Señor(es)':<25} {'Razón Social':<25} {'Distrito':<15} {'Vendedor':<12} {'Total':>12}\n"
    txt_content += f"{'-'*100}\n"
    
    total_general = 0
    for i, factura in enumerate(datos_facturas, 1):
        senor = (factura.get('senor', '-')[:22] + '...') if len(factura.get('senor', '-')) > 25 else factura.get('senor', '-')
        razon_social = (factura.get('razon_social', '-')[:22] + '...') if len(factura.get('razon_social', '-')) > 25 else factura.get('razon_social', '-')
        distrito = factura.get('distrito', '-')[:13]
        vendedor = factura.get('vendedor', '-')[:10]
        total = float(factura.get('total_a_pagar', 0))
        total_general += total
        
        txt_content += f"{i:<3} {senor:<25} {razon_social:<25} {distrito:<15} {vendedor:<12} ₲ {total:>9,.0f}\n"
    
    txt_content += f"{'-'*100}\n"
    txt_content += f"{'TOTAL GENERAL:':<80} ₲ {total_general:>9,.0f}\n"
    
    return txt_content

def procesar_texto_pdf(texto):
    """Procesa el texto del PDF y extrae la información estructurada"""
    datos_facturas = []
    
    # Patrones de búsqueda mejorados
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
    
    # Buscar todas las órdenes en el texto
    ordenes = patrones['orden'].findall(texto)
    fleteros = patrones['fletero'].findall(texto)
    facturas = patrones['factura'].findall(texto)
    
    # Procesar cada factura encontrada
    for i, factura_num in enumerate(facturas):
        factura_data = {'factura': factura_num}
        
        # Buscar datos alrededor de esta factura
        factura_index = texto.find(f"Nº {factura_num}")
        if factura_index != -1:
            # Extraer sección alrededor de la factura
            seccion_inicio = max(0, factura_index - 500)
            seccion_fin = min(len(texto), factura_index + 1000)
            seccion = texto[seccion_inicio:seccion_fin]
            
            # Buscar otros campos en esta sección
            for campo, patron in patrones.items():
                if campo in ['factura']:
                    continue
                match = patron.search(seccion)
                if match:
                    valor = match.group(1).strip()
                    if campo == 'total_a_pagar':
                        try:
                            # Convertir formato de número
                            valor = float(valor.replace('.', '').replace(',', '.'))
                        except:
                            valor = 0.0
                    # Tomar solo la primera línea si hay saltos
                    valor = valor.split('\n')[0] if '\n' in valor else valor
                    factura_data[campo] = valor
        
        datos_facturas.append(factura_data)
    
    return datos_facturas

# =======================================================
# INTERFAZ STREAMLIT
# =======================================================

st.markdown("""
### 📋 Instrucciones:
1. **Sube tu PDF** con las órdenes de transporte
2. **La aplicación procesará** automáticamente los datos
3. **Descarga el resumen** en formato HTML o TXT organizado
""")

uploaded_file = st.file_uploader("Selecciona tu archivo PDF", type="pdf")

if uploaded_file is not None:
    with st.spinner("Procesando PDF... Esto puede tomar unos segundos"):
        try:
            # Leer PDF usando pypdf (que SÍ viene con Streamlit)
            import pypdf
            pdf_reader = pypdf.PdfReader(uploaded_file)
            
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
                        
                        # Crear resumen en HTML
                        html_content = crear_resumen_html(orden, fletero, facturas)
                        zip_file.writestr(f"resumen_{orden}.html", html_content)
                        
                        # Crear resumen en TXT
                        txt_content = crear_resumen_txt(orden, fletero, facturas)
                        zip_file.writestr(f"resumen_{orden}.txt", txt_content)
                
                zip_buffer.seek(0)
                
                # Mostrar resumen detallado
                st.subheader("📊 Resumen de Órdenes Encontradas")
                
                for orden, facturas in ordenes.items():
                    with st.expander(f"📋 Orden {orden} - {len(facturas)} facturas"):
                        fletero = facturas[0].get('fletero', 'No especificado') if facturas else 'No especificado'
                        st.write(f"**Fletero:** {fletero}")
                        
                        # Mostrar tabla de facturas
                        for i, factura in enumerate(facturas, 1):
                            col1, col2, col3 = st.columns([3, 2, 2])
                            with col1:
                                st.write(f"**{factura.get('factura', 'N/A')}** - {factura.get('senor', 'N/A')}")
                            with col2:
                                st.write(factura.get('distrito', 'N/A'))
                            with col3:
                                st.write(f"₲ {float(factura.get('total_a_pagar', 0)):,.0f}")
                
                # Estadísticas generales
                total_general = sum(float(f.get('total_a_pagar', 0)) for f in datos_facturas)
                total_ordenes = len(ordenes)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📦 Total Órdenes", total_ordenes)
                with col2:
                    st.metric("🧾 Total Facturas", len(datos_facturas))
                with col3:
                    st.metric("💰 Total General", f"₲ {total_general:,.0f}")
                
                # Botones de descarga
                st.subheader("📥 Descargar Resultados")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="💾 Descargar Todo (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name="resumenes_viajes.zip",
                        mime="application/zip",
                        type="primary",
                        use_container_width=True
                    )
                with col2:
                    # Resumen general en HTML
                    html_general = crear_resumen_html("TODAS LAS ÓRDENES", "Varios fleteros", datos_facturas)
                    st.download_button(
                        label="🌐 Descargar Resumen General (HTML)",
                        data=html_general,
                        file_name="resumen_general.html",
                        mime="text/html",
                        use_container_width=True
                    )
                
            else:
                st.warning("⚠️ No se encontraron órdenes de transporte en el PDF")
                st.info("""
                **Sugerencias:**
                - Verifica que el PDF contenga campos como 'Orden de Transporte', 'Nº factura', etc.
                - Asegúrate de que el texto sea seleccionable (no sea una imagen escaneada)
                - El formato debe coincidir con los patrones esperados
                """)
                
        except Exception as e:
            st.error(f"❌ Error al procesar el PDF: {str(e)}")
            st.info("""
            **Soluciones comunes:**
            - El PDF está protegido con contraseña
            - El PDF es una imagen escaneada (no tiene texto seleccionable)
            - El formato no coincide con el esperado
            - El archivo está corrupto
            """)

# Información adicional
with st.expander("ℹ️ Acerca de esta aplicación"):
    st.markdown("""
    **✨ Funcionalidades incluidas:**
    - ✅ Procesamiento automático de PDFs
    - ✅ Extracción inteligente de órdenes de transporte
    - ✅ Agrupación automática por orden y cliente
    - ✅ Generación de resúmenes en HTML y TXT
    - ✅ Cálculo de totales automático
    - ✅ Descarga en formato ZIP organizado
    - ✅ Interfaz web moderna y responsive
    
    **📊 Campos detectados automáticamente:**
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
    
    **🎯 Formatos de salida:**
    - HTML (para visualización web)
    - TXT (para importar a Excel)
    - ZIP (todos los archivos organizados)
    """)

st.markdown("---")
st.caption("🚀 Procesador de Viajes v3.0 - 100% Funcional - Para uso interno")
