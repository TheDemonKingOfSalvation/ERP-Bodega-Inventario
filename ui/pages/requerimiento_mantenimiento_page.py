from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, QMessageBox,
)
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from pypdf import PdfReader, PdfWriter
from io import BytesIO
from datetime import datetime
import os

from logic.logic_mongo import guardar_requerimiento_maquina
from ui.utils import (
    obtener_base_pdf, ruta_recurso, limpiar_nombre_archivo, obtener_pdf_unico,
)


class RequerimientoMantenimientoPage(QWidget):
    def __init__(self, codigo_maquina="", nombre_maquina="", callback_actualizar=None):
        super().__init__()

        self.codigo_maquina = codigo_maquina
        self.nombre_maquina = nombre_maquina
        self.callback_actualizar = callback_actualizar

        self.setWindowTitle("Requerimiento de mantenimiento")
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        self.codigo_input = QLineEdit()
        self.codigo_input.setText(codigo_maquina)
        self.codigo_input.setPlaceholderText("Codigo de la maquina")
        self.nombre_input = QLineEdit()
        self.nombre_input.setText(nombre_maquina)
        self.nombre_input.setPlaceholderText("Nombre de la maquina")
        self.razon_input = QTextEdit()
        self.razon_input.setPlaceholderText("Razon por la cual la maquina requiere mantenimiento")
        self.btn_generar = QPushButton("Generar requerimiento PDF")

        layout.addWidget(QLabel("Codigo de maquina"))
        layout.addWidget(self.codigo_input)
        layout.addWidget(QLabel("Nombre de maquina"))
        layout.addWidget(self.nombre_input)
        layout.addWidget(QLabel("Razon del mantenimiento"))
        layout.addWidget(self.razon_input)
        layout.addWidget(self.btn_generar)
        self.btn_generar.clicked.connect(self.generar_pdf)

    def escribir_texto_limitado(self, c, texto, x, y, fuente, tamano, ancho_max, max_lineas, salto_linea):
        c.setFont(fuente, tamano)
        texto = str(texto or "").strip()
        if not texto:
            return
        lineas_finales = []
        for parrafo in texto.split("\n"):
            parrafo = parrafo.strip()
            if not parrafo:
                continue
            lineas_finales.extend(simpleSplit(parrafo, fuente, tamano, ancho_max))
        lineas_finales = lineas_finales[:max_lineas]
        for linea in lineas_finales:
            while c.stringWidth(linea, fuente, tamano) > ancho_max and len(linea) > 3:
                linea = linea[:-1]
            c.drawString(x, y, linea)
            y -= salto_linea

    def generar_pdf(self):
        codigo = self.codigo_input.text().strip()
        nombre = self.nombre_input.text().strip()
        razon = self.razon_input.toPlainText().strip()
        fecha = datetime.now().strftime("%Y-%m-%d")

        if not codigo or not nombre or not razon:
            QMessageBox.warning(self, "Campos incompletos", "Debe completar el codigo, el nombre de la maquina y la razon del mantenimiento.")
            return

        respuesta = QMessageBox.question(
            self, "Confirmar generacion",
            "¿Deseas generar el requerimiento de mantenimiento?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if respuesta != QMessageBox.Yes:
            return

        plantilla_pdf = ruta_recurso("ui/requerimiento/Requerimiento_mantenimiento.pdf")
        if not os.path.exists(plantilla_pdf):
            QMessageBox.critical(self, "Plantilla no encontrada", f"No se encontro la plantilla:\n{plantilla_pdf}")
            return

        carpeta_salida = os.path.join(obtener_base_pdf(), "requerimientos", "mantenimiento")
        salida_pdf = obtener_pdf_unico(carpeta_salida, f"Requerimiento_mantenimiento_{limpiar_nombre_archivo(codigo)}_{fecha}")

        self.btn_generar.setEnabled(False)
        try:
            plantilla = PdfReader(plantilla_pdf)
            if len(plantilla.pages) == 0:
                QMessageBox.critical(self, "Plantilla invalida", "La plantilla PDF no tiene paginas.")
                return
            pagina_base = plantilla.pages[0]
            ancho = float(pagina_base.mediabox.width)
            alto = float(pagina_base.mediabox.height)

            packet = BytesIO()
            c = canvas.Canvas(packet, pagesize=(ancho, alto))
            self.escribir_texto_limitado(
                c=c, texto=f"{codigo} - {nombre}",
                x=300, y=578, fuente="Helvetica-Bold", tamano=9,
                ancho_max=300, max_lineas=1, salto_linea=11,
            )
            self.escribir_texto_limitado(
                c=c, texto=razon,
                x=240, y=550, fuente="Helvetica-Bold", tamano=9,
                ancho_max=360, max_lineas=3, salto_linea=12,
            )
            c.save()
            packet.seek(0)

            overlay = PdfReader(packet)
            writer = PdfWriter()
            pagina = plantilla.pages[0]
            pagina.merge_page(overlay.pages[0])
            writer.add_page(pagina)

            with open(salida_pdf, "wb") as f:
                writer.write(f)
        except Exception as e:
            QMessageBox.critical(self, "Error al generar PDF", f"No se pudo generar el requerimiento:\n{e}")
            return
        finally:
            self.btn_generar.setEnabled(True)

        ok, mensaje = guardar_requerimiento_maquina(
            codigo=codigo, nombre=nombre, fecha=fecha, razon=razon, pdf_path=salida_pdf,
        )
        if not ok:
            QMessageBox.warning(self, "No se pudo guardar", mensaje)
            return
        if self.callback_actualizar:
            self.callback_actualizar()
        QMessageBox.information(self, "PDF generado", f"Requerimiento generado correctamente:\n{salida_pdf}")
