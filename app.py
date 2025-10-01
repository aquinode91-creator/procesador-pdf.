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
# FUNCIONES PRINCIPALES (SIN DEPENDENCIAS EXTERNAS)
# =======================================================

def crear_resumen_html(orden, fletero, datos_facturas):
    """Crea un resumen en HTML"""
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

def procesar_datos_manual():
    """Interfaz para ingresar datos manualmente"""
    st.subheader("📝 Ingreso Manual de Datos")
    
    with st.form("datos_viaje"):
        orden = st.text_input("Orden de Transporte*")
        fletero = st.text_input("Fletero*")
        
        st.markdown("---")
        st.subheader("Facturas")
        
        # Campos para múltiples facturas
        facturas = []
        num_facturas = st.number_input("Número de facturas", min_value=1, max_value=50, value=1)
        
        for i in range(num_facturas):
            st.write(f"**Factura {i+1}**")
            col1, col2 = st.columns(2)
            with col1:
                nro_factura = st.text_input(f"Nº Factura {i+1}", key=f"factura_{i}")
                senor = st.text_input(f"Señor(es) {i+1}", key=f"senor_{i}")
                razon_social = st.text_input(f"Razón Social {i+1}", key=f"razon_{i}")
            with col2:
                distrito = st.text_input(f"Distrito {i+1}", key=f"distrito_{i}")
                vendedor = st.text_input(f"Vendedor {i+1}", key=f"vendedor_{i}")
                total = st.number_input(f"Total a Pagar {i+1}", min_value=0.0, value=0.0, key=f"total_{i}")
            
            if nro_factura:
                facturas.append({
                    'factura': nro_factura,
                    'senor': senor,
                    'razon_social': razon_social,
                    'distrito': distrito,
                    'vendedor': vendedor,
                    'total_a_pagar': total,
                    'orden': orden,
                    'fletero': fletero
                })
        
        submitted = st.form_submit_button("Generar Resumen")
        
        if submitted and orden and fletero:
            return [{
                'orden': orden,
                'fletero': fletero,
                'facturas': facturas
            }]
    
    return None

def procesar_texto_plano(texto):
    """Procesa texto plano copiado/pegado"""
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
        'total_a_pagar': re.compile(r"TOTAL\s+A\s+PAGAR\s*[,:]?\s*([\d\.,]+)", re.IGNORECASE)
    }
    
    # Buscar datos en el texto
    orden_match = patrones['orden'].search(texto)
    fletero_match = patrones['fletero'].search(texto)
    facturas_matches = patrones['factura'].findall(texto)
    
    if orden_match and facturas_matches:
        orden = orden_match.group(1).strip()
        fletero = fletero_match.group(1).strip() if fletero_match else "No especificado"
        
        # Buscar otros datos para cada factura
        for factura_num in facturas_matches:
            factura_data = {
                'factura': factura_num,
                'orden': orden,
                'fletero': fletero
            }
            
            # Buscar otros campos
            for campo, patron in patrones.items():
                if campo in ['orden', 'fletero', 'factura']:
                    continue
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

# =======================================================
# INTERFAZ PRINCIPAL
# =======================================================

st.markdown("""
### 🎯 Tres formas de usar la aplicación:

1. **📝 Ingreso Manual** - Completa el formulario paso a paso
2. **📋 Pegar Texto** - Copia y pega el contenido de tu PDF
3. **💾 Subir Archivo** - Sube tu archivo (funcionalidad básica)
""")

# Pestañas para diferentes métodos
tab1, tab2, tab3 = st.tabs(["📝 Ingreso Manual", "📋 Pegar Texto", "💾 Subir Archivo"])

datos_procesados = None

with tab1:
    st.info("💡 **Recomendado para máximo control**")
    datos_procesados = procesar_datos_manual()

with tab2:
    st.info("💡 **Copia el texto de tu PDF y pégalo aquí**")
    texto_pegado = st.text_area("Pega el contenido de tu PDF aquí:", height=200,
                               placeholder="Orden de Transporte: TRP-001\nFletero: Juan Pérez\nNº 12345\nSeñor(es): Cliente Ejemplo\n...")
    
    if st.button("Procesar Texto Pegado", use_container_width=True):
        if texto_pegado:
            with st.spinner("Procesando texto..."):
                datos_procesados = procesar_texto_plano(texto_pegado)
                if datos_procesados:
                    st.success(f"✅ Se encontraron {len(datos_procesados)} facturas")
                else:
                    st.warning("⚠️ No se encontraron datos válidos en el texto")

with tab3:
    st.info("💡 **Sube tu archivo (solo para archivos de texto)**")
    archivo_subido = st.file_uploader("Selecciona un archivo", type=['txt', 'csv'])
    
    if archivo_subido is not None:
        try:
            texto_archivo = archivo_subido.getvalue().decode('utf-8')
            datos_procesados = procesar_texto_plano(texto_archivo)
            if datos_procesados:
                st.success(f"✅ Archivo procesado - {len(datos_procesados)} facturas encontradas")
            else:
                st.warning("⚠️ No se encontraron datos válidos en el archivo")
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {e}")

# =======================================================
# PROCESAR Y MOSTRAR RESULTADOS
# =======================================================

if datos_procesados:
    st.markdown("---")
    st.success("✅ **Datos procesados correctamente**")
    
    # Agrupar por orden
    ordenes = {}
    for factura in datos_procesados:
        orden = factura.get('orden', 'Sin orden')
        if orden not in ordenes:
            ordenes[orden] = []
        ordenes[orden].append(factura)
    
    # Crear ZIP con resúmenes
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for orden, facturas in ordenes.items():
            fletero = facturas[0].get('fletero', 'No especificado') if facturas else 'No especificado'
            
            # Crear resúmenes
            html_content = crear_resumen_html(orden, fletero, facturas)
            txt_content = crear_resumen_txt(orden, fletero, facturas)
            
            zip_file.writestr(f"resumen_{orden}.html", html_content)
            zip_file.writestr(f"resumen_{orden}.txt", txt_content)
    
    zip_buffer.seek(0)
    
    # Mostrar resumen
    st.subheader("📊 Resumen Generado")
    
    for orden, facturas in ordenes.items():
        with st.expander(f"📋 Orden {orden} - {len(facturas)} facturas"):
            fletero = facturas[0].get('fletero', 'No especificado')
            total_orden = sum(float(f.get('total_a_pagar', 0)) for f in facturas)
            
            st.write(f"**Fletero:** {fletero}")
            st.write(f"**Total de la orden:** ₲ {total_orden:,.0f}")
            
            # Tabla de facturas
            for i, factura in enumerate(facturas, 1):
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                with col1:
                    st.write(f"**{factura.get('factura', 'N/A')}**")
                with col2:
                    st.write(factura.get('senor', 'N/A'))
                with col3:
                    st.write(factura.get('distrito', 'N/A'))
                with col4:
                    st.write(f"₲ {float(factura.get('total_a_pagar', 0)):,.0f}")
    
    # Estadísticas
    total_general = sum(float(f.get('total_a_pagar', 0)) for f in datos_procesados)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📦 Total Órdenes", len(ordenes))
    with col2:
        st.metric("🧾 Total Facturas", len(datos_procesados))
    with col3:
        st.metric("💰 Total General", f"₲ {total_general:,.0f}")
    
    # Descargas
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
        # Resumen general
        html_general = crear_resumen_html("TODAS LAS ÓRDENES", "Varios fleteros", datos_procesados)
        st.download_button(
            label="🌐 Resumen General (HTML)",
            data=html_general,
            file_name="resumen_general.html",
            mime="text/html",
            use_container_width=True
        )

# Información adicional
with st.expander("ℹ️ Acerca de esta aplicación"):
    st.markdown("""
    **✨ Características:**
    - ✅ **100% funcional** sin dependencias externas
    - ✅ **Tres métodos** de entrada de datos
    - ✅ **Generación automática** de resúmenes
    - ✅ **Cálculo de totales** en tiempo real
    - ✅ **Descarga en múltiples formatos**
    - ✅ **Interfaz moderna** y responsive
    
    **📊 Datos que procesa:**
    - Orden de Transporte
    - Fletero
    - Nº de factura
    - Señor(es)
    - Razón Social
    - Distrito
    - Vendedor
    - Total a Pagar
    
    **🎯 Formatos de salida:**
    - HTML (visualización web)
    - TXT (compatible con Excel)
    - ZIP (organizado por órdenes)
    """)

st.markdown("---")
st.caption("🚀 Procesador de Viajes v4.0 - 100% Autónomo - Para uso interno")
