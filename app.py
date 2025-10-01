import streamlit as st
import re
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import shutil
from collections import OrderedDict, defaultdict
import tempfile
import os
import zipfile
import base64

# Configuración de la página
st.set_page_config(
    page_title="Procesador de Viajes",
    page_icon="📦",
    layout="wide"
)

# =======================================================
# FUNCIONES ORIGINALES ADAPTADAS
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

def medir_columnas(c, datos, columnas, font_name="Helvetica", font_size=7):
    col_widths = {col: c.stringWidth(col, font_name, font_size) + 10 for col in columnas}
    for fila in datos:
        for col, val in fila.items():
            texto = str(val) if val is not None else "-"
            ancho = c.stringWidth(texto, font_name, font_size) + 10
            if ancho > col_widths[col]:
                col_widths[col] = ancho
    return col_widths

def escalar_columnas(col_widths, ancho_total):
    suma = sum(col_widths.values())
    if suma == 0:
        return col_widths
    factor = ancho_total / suma
    for col in col_widths:
        w = max(20, int(col_widths[col] * factor))
        col_widths[col] = w
    return col_widths

def obtener_id_unico_cliente(d):
    cod = (d.get("cod_cliente") or "").strip()
    if cod:
        return cod
    ruc = (d.get("ruc_ci") or "").strip()
    if ruc:
        return ruc
    sen = (d.get("senor") or "").strip()
    if sen:
        return sen
    raz = (d.get("razon_social") or "").strip()
    if raz:
        return raz
    return str(d.get("factura", ""))

def make_data_page(order, fletero, client_data_grouped, all_invoice_data):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    ancho, alto = landscape(A4)

    left_margin, right_margin = 35, 50
    main_width = ancho - left_margin - right_margin

    columnas = ["N°", "Señor(es)", "Razon Social", "Distrito", "Vendedor",
                "Plazo", "Forma de Pago", "Cond. Venta", "Tipo Venta", "Total a Pagar"]

    filas_prueba = []
    cliente_id_a_num = OrderedDict()
    contador = 0

    for _, facturas in client_data_grouped.items():
        if not facturas:
            continue
        id_unico = obtener_id_unico_cliente(facturas[0])
        if id_unico not in cliente_id_a_num:
            contador += 1
            cliente_id_a_num[id_unico] = contador
        for _d in facturas:
            pass

    for _, facturas in client_data_grouped.items():
        if not facturas:
            continue
        id_unico = obtener_id_unico_cliente(facturas[0])
        numero_cliente = cliente_id_a_num.get(id_unico, "")
        first = True
        for data in facturas:
            filas_prueba.append({
                "N°": numero_cliente if first else "",
                "Señor(es)": data.get("senor", "-"),
                "Razon Social": data.get("razon_social", "-"),
                "Distrito": data.get("distrito", "-"),
                "Vendedor": data.get("vendedor", "-"),
                "Plazo": data.get("plazo", "-"),
                "Forma de Pago": data.get("forma_de_pago", "-"),
                "Cond. Venta": data.get("condicion_venta", "-"),
                "Tipo Venta": data.get("tipo_venta", "-"),
                "Total a Pagar": f"{data.get('total_a_pagar', 0):,.0f}".replace(",", "."),
            })
            first = False

    col_widths = medir_columnas(c, filas_prueba, columnas, "Helvetica", 7)
    col_widths = escalar_columnas(col_widths, main_width)

    columns = OrderedDict()
    x_cursor = left_margin
    for col in columnas[:-1]:
        w = col_widths[col]
        columns[col] = {"x": x_cursor, "width": w}
        x_cursor += w
    columns["Total a Pagar"] = {"x": ancho - right_margin, "width": col_widths["Total a Pagar"]}

    def draw_headers(y_start, is_first_page=True):
        if is_first_page:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(left_margin, alto - 40, f"Orden de Transporte: {order}")
            c.setFont("Helvetica", 10)
            c.drawString(left_margin, alto - 55, f"Fletero: {fletero}")
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(ancho / 2, alto - 75, "Resumen de Viaje")
        c.setFont("Helvetica-Bold", 7)
        for col_name, props in columns.items():
            if col_name == "Total a Pagar":
                c.drawRightString(props["x"], y_start, col_name)
            else:
                c.drawString(props["x"], y_start, col_name)
        return y_start - 15

    y = draw_headers(alto - 100)
    font_size, line_height = 7, 9

    ya_numerados = set()
    for _, facturas_cliente in client_data_grouped.items():
        if not facturas_cliente:
            continue
        id_unico = obtener_id_unico_cliente(facturas_cliente[0])
        numero_cliente = cliente_id_a_num.get(id_unico, "")
        first = True
        for data in facturas_cliente:
            tipo_venta_text = (data.get("tipo_venta") or "").strip()
            forma_pago_text = (data.get("forma_de_pago") or "").strip()
            is_whole_row_bold = (
                tipo_venta_text.lower() in ["reposición", "sin cargo"] or
                forma_pago_text.lower() == "sin cargo"
            )

            wrapped_data = {
                "N°": [str(numero_cliente) if first else ""],
                "Señor(es)": wrap_text(c, data.get("senor", "-"), columns["Señor(es)"]["width"], "Helvetica", font_size),
                "Razon Social": wrap_text(c, data.get("razon_social", "-"), columns["Razon Social"]["width"], "Helvetica", font_size),
                "Distrito": wrap_text(c, data.get("distrito", "-"), columns["Distrito"]["width"], "Helvetica", font_size),
                "Vendedor": wrap_text(c, data.get("vendedor", "-"), columns["Vendedor"]["width"], "Helvetica", font_size),
                "Plazo": wrap_text(c, data.get("plazo", "-"), columns["Plazo"]["width"], "Helvetica", font_size),
                "Forma de Pago": wrap_text(c, forma_pago_text or "-", columns["Forma de Pago"]["width"], "Helvetica", font_size),
                "Cond. Venta": wrap_text(c, data.get("condicion_venta", "-"), columns["Cond. Venta"]["width"], "Helvetica", font_size),
                "Tipo Venta": wrap_text(c, tipo_venta_text or "-", columns["Tipo Venta"]["width"], "Helvetica", font_size),
                "Total a Pagar": [f"{data.get('total_a_pagar', 0):,.0f}".replace(",", ".")]
            }

            max_lines = max(len(lines) for lines in wrapped_data.values())
            row_height = max_lines * line_height + 4
            if y - row_height < 130:
                c.showPage()
                y = draw_headers(alto - 60, is_first_page=False)

            for col_name, lines in wrapped_data.items():
                c.setFont("Helvetica-Bold" if is_whole_row_bold else "Helvetica", font_size)
                for line_index, line_text in enumerate(lines):
                    y_pos = y - (line_index * line_height)
                    if col_name == "Total a Pagar":
                        c.drawRightString(columns[col_name]["x"], y_pos, line_text)
                    else:
                        c.drawString(columns[col_name]["x"], y_pos, line_text)
            y -= row_height
            first = False

    if y < 260:
        c.showPage()
        y = draw_headers(alto - 60, is_first_page=False)

    cond_agr = defaultdict(lambda: defaultdict(float))
    gran_total = 0.0
    for f in all_invoice_data:
        cond = (f.get("condicion_venta") or "-").strip()
        plazo = (f.get("plazo") or "-").strip()
        forma = (f.get("forma_de_pago") or "-").strip()
        tipo = (f.get("tipo_venta") or "Regular").strip()
        key = (plazo, forma, tipo)
        cond_agr[cond][key] += float(f.get("total_a_pagar", 0.0))
        gran_total += float(f.get("total_a_pagar", 0.0))

    y_summary = y - 40
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(ancho/2, y_summary, "RESUMEN FINAL DE TOTALES")
    y_summary -= 25

    c.setFont("Helvetica-Bold", 9)
    c.drawString(left_margin, y_summary, "Cond. Venta")
    c.drawString(left_margin+150, y_summary, "Plazo")
    c.drawString(left_margin+300, y_summary, "Forma de Pago")
    c.drawString(left_margin+500, y_summary, "Tipo de Venta")
    c.drawRightString(ancho - right_margin, y_summary, "Subtotal")
    y_summary -= 8
    c.line(left_margin, y_summary, ancho - right_margin, y_summary)
    y_summary -= 14

    row_step = 14
    for cond, combos in cond_agr.items():
        subtotal_cond = sum(combos.values())
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left_margin, y_summary, cond)
        c.drawRightString(ancho - right_margin, y_summary, f"{subtotal_cond:,.0f}".replace(",", "."))
        y_summary -= row_step

        c.setFont("Helvetica", 8)
        for (plazo, forma, tipo), subtotal in combos.items():
            c.drawString(left_margin+150, y_summary, plazo)
            c.drawString(left_margin+300, y_summary, forma)
            c.drawString(left_margin+500, y_summary, tipo)
            c.drawRightString(ancho - right_margin, y_summary, f"{subtotal:,.0f}".replace(",", "."))
            y_summary -= row_step

        y_summary -= 6

        if y_summary < 120:
            c.showPage()
            y_summary = draw_headers(alto - 60, is_first_page=False) - 40
            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(ancho/2, y_summary, "RESUMEN FINAL DE TOTALES (cont.)")
            y_summary -= 25
            c.setFont("Helvetica-Bold", 9)
            c.drawString(left_margin, y_summary, "Cond. Venta")
            c.drawString(left_margin+150, y_summary, "Plazo")
            c.drawString(left_margin+300, y_summary, "Forma de Pago")
            c.drawString(left_margin+500, y_summary, "Tipo de Venta")
            c.drawRightString(ancho - right_margin, y_summary, "Subtotal")
            y_summary -= 8
            c.line(left_margin, y_summary, ancho - right_margin, y_summary)
            y_summary -= 14

    y_summary -= 6
    c.line(left_margin, y_summary, ancho - right_margin, y_summary)
    y_summary -= 18
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(ancho - right_margin - 150, y_summary, "GRAN TOTAL GENERAL:")
    c.drawRightString(ancho - right_margin, y_summary, f"{gran_total:,.0f}".replace(",", "."))

    c.showPage()
    c.save()
    buffer.seek(0)
    return PdfReader(buffer)

def agrupar_datos_por_cliente(datos_facturas):
    clientes = OrderedDict()
    for d in datos_facturas:
        cod = (d.get("cod_cliente") or "").strip()
        if not cod:
            display = d.get("senor") or d.get("razon_social") or "(Sin nombre)"
            key = display
        else:
            key = cod
        if key not in clientes:
            clientes[key] = []
        clientes[key].append(d)
    return clientes

def save_writer(order, all_pages, all_invoice_data, output_dir, fletero):
    if not all_pages:
        return

    client_data_grouped = agrupar_datos_por_cliente(all_invoice_data)
    summary_pdf_reader = make_data_page(order, fletero, client_data_grouped, all_invoice_data)

    final_writer = PdfWriter()
    for page in summary_pdf_reader.pages:
        final_writer.add_page(page)

    indice_paginas = {}
    factura_pattern = re.compile(r"Nº\s*([0-9-]+)", re.IGNORECASE)
    for page in all_pages:
        text = page.extract_text() or ""
        match = factura_pattern.search(text)
        if match:
            nro_factura = match.group(1)
            indice_paginas[nro_factura] = page

    for _, facturas in client_data_grouped.items():
        for datos_factura in facturas:
            nro_factura = datos_factura.get("factura")
            if nro_factura and nro_factura in indice_paginas:
                final_writer.add_page(indice_paginas[nro_factura])

    fname = output_dir / f"viaje_{order}.pdf"
    with open(fname, "wb") as f:
        final_writer.write(f)
    return fname

def procesar_pdf(uploaded_file):
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "viajes_portadas"
        output_dir.mkdir(exist_ok=True)
        
        # Guardar archivo subido temporalmente
        input_path = Path(temp_dir) / "input.pdf"
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        reader = PdfReader(input_path)

        orden_pattern = re.compile(r"Orden\s+de\s+Transporte\s*:\s*([A-Za-z0-9\-_]+)", re.IGNORECASE)
        fletero_pattern = re.compile(r"Fletero\s*:\s*(.+)", re.IGNORECASE)
        factura_pattern = re.compile(r"Nº\s*([0-9-]+)", re.IGNORECASE)

        patterns = {
            "senor": re.compile(r"Señor\(es\):\s*(.+)", re.IGNORECASE),
            "razon_social": re.compile(r"Razón\s*Social\s*:\s*(.+)", re.IGNORECASE),
            "distrito": re.compile(r"Distrito\s*:\s*(.+)", re.IGNORECASE),
            "vendedor": re.compile(r"Vendedor\s*:\s*(.+)", re.IGNORECASE),
            "plazo": re.compile(r"Plazo\s*:\s*(.+)", re.IGNORECASE),
            "total_a_pagar": re.compile(r"TOTAL\s+A\s+PAGAR\s*[,:]?\s*([\d\.,]+)", re.IGNORECASE),
            "forma_de_pago": re.compile(r"Forma\s+de\s+Pago\s*:\s*(.+)", re.IGNORECASE),
            "tipo_venta": re.compile(r"Tipo\s+de\s+Venta\s*:\s*(Reposición)", re.IGNORECASE),
            "ruc_ci": re.compile(r"(R\.?\s*U\.?\s*C\.?\s*(?:/|y)?\s*C\.?\s*I\.?|RUC\s*(?:/|y)?\s*CI|R\.?U\.?C\.?|C\.?I\.?)\s*:\s*(.+)", re.IGNORECASE),
            "cod_cliente": re.compile(r"(C[oó]d\.?\s*de\s*Cliente|C[oó]digo\s*Cliente|Cod\.\s*Cliente)\s*:\s*(.+)", re.IGNORECASE),
        }

        current_order = None
        current_fletero = None
        datos_facturas_actuales = []
        paginas_viaje_actual = []
        archivos_procesados = []

        for page in reader.pages:
            text = page.extract_text() or ""
            match_order = orden_pattern.search(text)
            found_order = match_order.group(1).strip() if match_order else None

            if found_order and found_order != current_order:
                if current_order is not None:
                    archivo_procesado = save_writer(current_order, paginas_viaje_actual, datos_facturas_actuales, output_dir, current_fletero)
                    archivos_procesados.append(archivo_procesado)
                
                current_order = found_order
                paginas_viaje_actual = []
                datos_facturas_actuales = []
                match_fletero = fletero_pattern.search(text)
                current_fletero = match_fletero.group(1).strip().split('\n')[0] if match_fletero else "No especificado"

            if current_order is None:
                continue

            paginas_viaje_actual.append(page)

            match_factura = factura_pattern.search(text)
            if match_factura:
                factura_num = match_factura.group(1)
                if not any(d.get('factura') == factura_num for d in datos_facturas_actuales):
                    invoice_details = {"factura": factura_num}
                    
                    for key, pattern in patterns.items():
                        m = pattern.search(text)
                        if m:
                            value = m.group(len(m.groups())).strip().split('\n')[0]
                            if key == 'total_a_pagar':
                                value = float(value.replace('.', '').replace(',', '.'))
                            elif key in ('ruc_ci', 'cod_cliente'):
                                value = value.strip()
                            invoice_details[key] = value

                    plazo_texto = (invoice_details.get("plazo") or "").lower()
                    invoice_details["condicion_venta"] = "Contado" if "contado" in plazo_texto else "Crédito"

                    if float(invoice_details.get("total_a_pagar", -1)) == 0:
                        invoice_details["tipo_venta"] = "Sin Cargo"
                    if (invoice_details.get("forma_de_pago") or "").strip().lower() == "sin cargo":
                        invoice_details["tipo_venta"] = "Sin Cargo"

                    if not invoice_details.get("tipo_venta"):
                        invoice_details["tipo_venta"] = "Regular"

                    datos_facturas_actuales.append(invoice_details)

        if current_order is not None:
            archivo_procesado = save_writer(current_order, paginas_viaje_actual, datos_facturas_actuales, output_dir, current_fletero)
            archivos_procesados.append(archivo_procesado)

        # Crear archivo ZIP con resultados
        zip_path = Path(temp_dir) / "resultados_procesados.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for archivo in archivos_procesados:
                zipf.write(archivo, archivo.name)

        return zip_path

# =======================================================
# INTERFAZ STREAMLIT
# =======================================================
def main():
    st.title("📦 Procesador de Viajes - Resumen PDF")
    st.markdown("""
    Esta aplicación procesa archivos PDF de órdenes de transporte y genera:
    - 📋 **Resumen ejecutivo** con todos los datos organizados
    - 🧾 **Facturas ordenadas** por cliente
    - 📊 **Tablas resumen** con totales y condiciones de venta
    """)

    st.divider()

    # Panel de subida de archivos
    uploaded_file = st.file_uploader(
        "Sube tu archivo PDF", 
        type="pdf",
        help="Selecciona el PDF que contiene las órdenes de transporte"
    )

    if uploaded_file is not None:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Procesar PDF", type="primary", use_container_width=True):
                with st.spinner("Procesando archivo... Esto puede tomar unos segundos"):
                    try:
                        # Procesar el PDF
                        zip_path = procesar_pdf(uploaded_file)
                        
                        # Leer el archivo ZIP resultante
                        with open(zip_path, "rb") as f:
                            zip_data = f.read()
                        
                        # Mostrar éxito y botón de descarga
                        st.success("✅ ¡Procesamiento completado!")
                        
                        st.download_button(
                            label="📥 Descargar Resultados (ZIP)",
                            data=zip_data,
                            file_name="viajes_procesados.zip",
                            mime="application/zip",
                            use_container_width=True
                        )
                        
                        st.info("💡 El archivo ZIP contiene los PDFs procesados con los resúmenes de viaje.")
                        
                    except Exception as e:
                        st.error(f"❌ Error durante el procesamiento: {str(e)}")
                        st.info("⚠️ Por favor, verifica que el PDF tenga el formato correcto.")

    # Panel de información
    with st.expander("ℹ️ Instrucciones de uso"):
        st.markdown("""
        ### Pasos para usar la aplicación:
        1. **Subir PDF**: Haz clic en 'Browse files' y selecciona tu PDF
        2. **Procesar**: Presiona el botón 'Procesar PDF'
        3. **Descargar**: Una vez completado, descarga el archivo ZIP resultante

        ### Formato esperado del PDF:
        - Debe contener órdenes de transporte con los campos:
          - Orden de Transporte
          - Fletero
          - Nº de factura
          - Señor(es)
          - Razón Social
          - Distrito
          - Total a Pagar
          - etc.

        ### Características del procesamiento:
        - ✅ Agrupa facturas por cliente
        - ✅ Genera resumen ejecutivo
        - ✅ Calcula totales automáticamente
        - ✅ Identifica tipos de venta especiales
        - ✅ Formato PDF profesional
        """)

    # Footer
    st.divider()
    st.caption("Procesador de Viajes v1.0 - Para uso interno")

if __name__ == "__main__":
    main()
