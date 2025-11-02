import os
from io import BytesIO
from datetime import datetime
from typing import List, Dict

import streamlit as st
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader, simpleSplit

# --- Rutas de activos ---
ASSETS_DIR = "assets"
TEMPLATE_FILE = os.path.join(ASSETS_DIR, "plantilla_plan_izado (Espagruas)2 (7).pdf")
LOGO_FILE = os.path.join(ASSETS_DIR, "logo.png")

APP_TITLE = "ESPAGRUAS · Plan de Izaje (Web)"
EXPLANATION_PARA = (
    "Este anexo presenta la evidencia gráfica asociada al plan de izaje. "
    "Las imágenes muestran la disposición real en obra, los accesos, la ubicación de la grúa "
    "y/o el desarrollo de la maniobra, con el único fin de complementar la evaluación técnica "
    "y facilitar la verificación de las condiciones de seguridad establecidas."
)

# ----- Etiquetas amigables para campos conocidos (si alguno falta, se muestra tal cual viene del PDF) -----
FIELD_TITLES = {
    "Text1": "Obra / Proyecto",
    "Text2": "Fecha",
    "Text7": "Cliente / Contratista",
    "Text8": "Dirección de la obra",
    "Text9": "Persona de contacto",
    "Text10": "Correo electrónico",
    "Text11": "Teléfono de contacto",
    "Text12": "Carga a izar",
    "Text13": "Peso de la carga (kg)",
    "Text14": "Dimensiones de la carga",
    "Text15": "¿Mercancía peligrosa?",
    "Text16": "Puntos de estrobaje / anclaje",
    "Text17": "Capacidad máxima de la grúa (kg)",
    "Text18": "Longitud de pluma (m)",
    "Text19": "Contrapesos",
    "Text20": "Radio máximo (m)",
    "Text21": "Altura máxima (m)",
    "Text22": "Total Kg levantados",
    "Text23": "Plumín / Jib",
    "Text24": "Tipo de grúa",
    "Text25": "Tonelaje de la grúa",
    "Text26": "Dimensiones de la grúa",
    "Text27": "Matrícula",
    "Text28": "Cadenas necesarias y capacidad",
    "Text29": "Eslingas necesarias y capacidad",
    "Text30": "Grilletes necesarios y capacidad",
    "Text31": "Gancho necesario / dimensión",
    "Text49": "Separador necesario",
    "Text50": "Dirección técnica",
    "Text51": "Jefe de maniobra",
    "Text52": "Operador de grúa",
    "Text53": "Señalista",
    "Text54": "Eslingador",
    "Text55": "Seguridad / Supervisión",
}

# ------------- Utilidades PDF -------------
def _page_size(page):
    mb = page.mediabox
    return float(mb.right) - float(mb.left), float(mb.top) - float(mb.bottom)

def _draw_values_overlay(fields_on_page, page_w, page_h):
    """
    Crea un PDF de una página con los textos posicionados en las coordenadas de cada campo.
    Aproxima tamaño de fuente al alto del recuadro (+ alineación izquierda).
    """
    buf = BytesIO()
    can = canvas.Canvas(buf, pagesize=(page_w, page_h))
    for f in fields_on_page:
        val = f.get("value", "")
        if not val:
            continue
        x1, y1, x2, y2 = f["rect"]
        text = str(val).strip("()")
        font_size = min(10.5, max(8.0, (y2 - y1) * 0.50))  # aproximación visual
        can.setFont("Helvetica", font_size)               # misma familia 'neutra' y limpia
        can.setFillGray(0.0)
        can.drawString(x1 + 2, y1 + (y2 - y1 - font_size) / 2, text)  # centrado vertical suave
    can.save()
    buf.seek(0)
    return PdfReader(buf)

def flatten_template_with_values(template_bytes: bytes, fields: List[Dict]) -> PdfWriter:
    """
    Aplana la plantilla en memoria con los valores y elimina los formularios.
    """
    reader = PdfReader(BytesIO(template_bytes))
    writer = PdfWriter()

    # Agrupar campos por página
    by_page: Dict[int, List[Dict]] = {}
    for f in fields:
        by_page.setdefault(f["page"], []).append(f)

    for i, page in enumerate(reader.pages):
        page_w, page_h = _page_size(page)
        if i in by_page:
            overlay = _draw_values_overlay(by_page[i], page_w, page_h)
            page.merge_page(overlay.pages[0])
        if "/Annots" in page:
            page.pop("/Annots")
        writer.add_page(page)
    return writer

def build_annex_page(image: Image.Image, title: str, logo_img: Image.Image = None) -> bytes:
    """
    Genera una página A4 horizontal (PDF) con logo, título (sin extensión) y un párrafo explicativo + la imagen escalada.
    Devuelve bytes del PDF de una sola página.
    """
    width, height = landscape(A4)
    margin = 1.5 * cm
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))

    # Logo
    if logo_img:
        try:
            # Escala sólida de ~4.5cm de ancho
            lw = 4.5 * cm
            iw, ih = logo_img.size
            ratio = lw / iw
            lh = ih * ratio
            c.drawImage(ImageReader(logo_img), margin, height - margin - lh, width=lw, height=lh, mask='auto')
        except Exception:
            pass

    # Título (sin extensión)
    title = os.path.splitext(title)[0]
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - margin - 0.9 * cm, "ESPAGRUAS S.L.")
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - margin - 1.9 * cm, f"ANEXO – {title}")

    # Párrafo explicativo
    c.setFont("Helvetica", 10)
    text_w = width - 2 * margin
    lines = simpleSplit(EXPLANATION_PARA, "Helvetica", 10, text_w)
    y_text = height - margin - 3.0 * cm
    for line in lines:
        c.drawString(margin, y_text, line)
        y_text -= 12  # leading

    # Marco y área para imagen
    c.setLineWidth(1)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)

    # Área de imagen (debajo del párrafo)
    top_img_y = y_text - 0.6 * cm
    box_x = margin + 0.3 * cm
    box_y = margin + 0.8 * cm
    box_w = width - 2 * margin - 0.6 * cm
    box_h = top_img_y - box_y
    c.setDash(3, 3)
    c.rect(box_x, box_y, box_w, box_h)
    c.setDash()

    # Imagen escalada centrada
    if image:
        iw, ih = image.size
        scale = min(box_w / iw, box_h / ih)
        dw, dh = iw * scale, ih * scale
        dx = box_x + (box_w - dw) / 2
        dy = box_y + (box_h - dh) / 2
        c.drawImage(ImageReader(image.convert("RGB")), dx, dy, width=dw, height=dh, mask='auto')

    c.showPage()
    c.save()
    return buf.getvalue()

def merge_writer_and_annexes(writer: PdfWriter, annex_pdfs: List[bytes]) -> bytes:
    """
    Une el PdfWriter (plantilla aplanada) con anexos (cada uno PDF de 1 página). Devuelve bytes del PDF final.
    """
    final = PdfWriter()
    for p in writer.pages:
        final.add_page(p)
    for ap in annex_pdfs:
        r = PdfReader(BytesIO(ap))
        for page in r.pages:
            final.add_page(page)
    out = BytesIO()
    final.write(out)
    return out.getvalue()

# ------------- App Streamlit -------------
st.set_page_config(page_title=APP_TITLE, page_icon="🦾", layout="wide")
st.title(APP_TITLE)

# Cargamos plantilla y logo desde assets
if not os.path.exists(TEMPLATE_FILE):
    st.error("❌ No se encuentra la plantilla en assets/. Sube el PDF con ese nombre exacto.")
    st.stop()
if not os.path.exists(LOGO_FILE):
    st.warning("⚠️ No se encontró logo.png en assets/. Se generarán anexos sin logo.")
    logo_img = None
else:
    try:
        logo_img = Image.open(LOGO_FILE)
    except Exception:
        logo_img = None

# Leemos campos de la plantilla
with open(TEMPLATE_FILE, "rb") as f:
    template_bytes = f.read()
reader = PdfReader(BytesIO(template_bytes))

# Extraer campos (widgets texto) y montarlos en UI
fields = []
for page_idx, page in enumerate(reader.pages):
    annots = page.get("/Annots")
    if not annots:
        continue
    for a in annots:
        obj = a.get_object()
        if obj.get("/Subtype") != "/Widget":
            continue
        name = obj.get("/T")
        rect = obj.get("/Rect")
        val = obj.get("/V")
        if name and rect:
            try:
                rect_f = [float(x) for x in rect]
            except Exception:
                continue
            fields.append({
                "name": str(name).strip("()"),
                "value": (str(val).strip("()") if val else ""),
                "page": page_idx,
                "rect": rect_f
            })

st.markdown("### 1) Rellena los datos del plan")
cols = st.columns(2)
left, right = cols[0], cols[1]

# Mostramos entradas (mitad-izquierda y mitad-derecha alternando)
ui_values: Dict[str, str] = {}
for idx, f in enumerate(fields):
    label = FIELD_TITLES.get(f["name"], f["name"])
    default = f.get("value", "")
    target = left if idx % 2 == 0 else right
    ui_values[f["name"]] = target.text_input(label, value=default, key=f"inp_{f['name']}")

st.markdown("---")
st.markdown("### 2) Adjunta imágenes (cada imagen será un anexo)")
images_up = st.file_uploader("Imágenes (PNG, JPG, JPEG, BMP, TIFF)", type=["png", "jpg", "jpeg", "bmp", "tif", "tiff"], accept_multiple_files=True)

# Botón generar
st.markdown("---")
if st.button("🧾 Generar PDF Final"):
    try:
        # Inyectar valores en la estructura de campos
        for f in fields:
            f["value"] = ui_values.get(f["name"], "")

        # Aplanar plantilla con valores
        writer = flatten_template_with_values(template_bytes, fields)

        # Crear anexos (solo para las imágenes adjuntas)
        annex_pdfs: List[bytes] = []
        for up in images_up or []:
            try:
                img = Image.open(up).convert("RGB")
                annex_pdf = build_annex_page(img, up.name, logo_img)
                annex_pdfs.append(annex_pdf)
            except Exception:
                pass

        # Unir y ofrecer descarga
        final_bytes = merge_writer_and_annexes(writer, annex_pdfs)
        filename = f"Plan_Izado_ESPAGRUAS_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        st.success("✅ PDF final generado correctamente.")
        st.download_button("⬇️ Descargar PDF", data=final_bytes, file_name=filename, mime="application/pdf")
    except Exception as e:
        st.error(f"❌ No se pudo generar el PDF final.\n\n{e}")
