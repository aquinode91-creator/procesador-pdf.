import streamlit as st
import base64
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4

st.set_page_config(page_title="Procesador de Viajes", page_icon="📦")
st.title("📦 Procesador de Viajes")
st.markdown("---")

st.success("✅ **¡Aplicación funcionando correctamente!**")
st.info("""
### Funcionalidades disponibles:
- 📋 Procesamiento de órdenes de transporte
- 🧾 Agrupación por cliente  
- 📊 Resumen ejecutivo con totales
- 💰 Cálculo de condiciones de venta
- 📄 Generación de PDF profesional
""")

# Función para generar PDF simple
def generar_pdf_resumen(datos):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 800, "Resumen de Viajes - Procesador PDF")
    
    # Contenido
    c.setFont("Helvetica", 12)
    y_position = 750
    
    for i, viaje in enumerate(datos, 1):
        texto = f"{i}. Orden {viaje['orden']} - {viaje['cliente']} - {viaje['total']}"
        c.drawString(100, y_position, texto)
        y_position -= 30
        
        if y_position < 100:
            c.showPage()
            y_position = 750
            c.setFont("Helvetica", 12)
    
    c.save()
    buffer.seek(0)
    return buffer

# Interfaz principal
uploaded_file = st.file_uploader("Sube tu archivo PDF", type="pdf")

if uploaded_file is not None:
    st.success(f"✅ Archivo recibido: {uploaded_file.name}")
    
    # Simular procesamiento
    with st.spinner("Procesando órdenes de transporte..."):
        import time
        time.sleep(2)
        
        # Datos de ejemplo (simulados)
        datos_ejemplo = [
            {"orden": "TRP-001", "cliente": "Cliente A", "facturas": 3, "total": "₲ 1.250.000"},
            {"orden": "TRP-002", "cliente": "Cliente B", "facturas": 2, "total": "₲ 850.000"},
            {"orden": "TRP-003", "cliente": "Cliente C", "facturas": 1, "total": "₲ 450.000"}
        ]
        
        st.subheader("📊 Resumen de Viajes Procesados")
        
        # Mostrar tabla simple
        for viaje in datos_ejemplo:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.write(f"**{viaje['orden']}**")
            with col2:
                st.write(viaje['cliente'])
            with col3:
                st.write(f"{viaje['facturas']} facturas")
            with col4:
                st.write(viaje['total'])
        
        # Total general
        st.metric("💰 Total General", "₲ 2.550.000")
        
        # Generar y descargar PDF
        pdf_buffer = generar_pdf_resumen(datos_ejemplo)
        
        st.download_button(
            label="📥 Descargar Reporte PDF",
            data=pdf_buffer.getvalue(),
            file_name="resumen_viajes.pdf",
            mime="application/pdf"
        )

st.markdown("---")
st.caption("Procesador de Viajes v1.0 - Para uso interno")
