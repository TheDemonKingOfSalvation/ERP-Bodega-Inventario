from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDoubleSpinBox,
    QPushButton, QTableWidget, QTableWidgetItem, QCheckBox, QMessageBox,
)
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from pypdf import PdfReader, PdfWriter
from io import BytesIO
from datetime import datetime
import os
from ui.admin_state import admin_state, ADMIN_USUARIO
from ui.utils import (
    obtener_base_pdf, ruta_recurso, limpiar_nombre_archivo, obtener_pdf_unico,
)
from config.config_manager import obtener_nombre_empresa
from logic.logic_mongo import (
    obtener_inventario_reabastecimiento,
    obtener_proveedores,
    guardar_requerimiento_reabastecimiento,
)



TIPO_A_PLANTILLA = {
    "herramienta": "Requerimiento_herramientas.pdf",
    "consumible":  "Reabastecimiento_consumible.pdf",
    "pvc":         "Reabastecimiento_pvc.pdf",
    "epp":         "Reabastecimiento_epp.pdf",
}

class RequerimientoReabastecimientoPage(QWidget):
    def __init__(self, tipo, callback_actualizar=None):
        super().__init__()

        self.tipo = tipo
        self.callback_actualizar = callback_actualizar

        self.setWindowTitle(f"Requerimiento de reabastecimiento - {tipo.upper()}")
        self.resize(900, 500)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Crear requerimiento de reabastecimiento - {tipo.upper()}"))

        proveedor_layout = QHBoxLayout()
        self.proveedor_combo = QComboBox()
        self.precio_input = QDoubleSpinBox()
        self.precio_input.setMinimum(0)
        self.precio_input.setMaximum(999999999)
        self.precio_input.setDecimals(2)
        self.precio_input.setPrefix("$ ")

        proveedor_layout.addWidget(QLabel("Proveedor"))
        proveedor_layout.addWidget(self.proveedor_combo)
        proveedor_layout.addWidget(QLabel("Costo del requerimiento"))
        proveedor_layout.addWidget(self.precio_input)
        layout.addLayout(proveedor_layout)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Seleccionar", "Codigo", "Nombre", "Disponibles", "Cantidad a pedir",
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        self.btn_generar = QPushButton("Generar requerimiento PDF")
        layout.addWidget(self.btn_generar)
        self.btn_generar.clicked.connect(self.generar_requerimiento)

        self.cargar_proveedores()
        self.cargar_inventario()

    def cargar_proveedores(self):
        self.proveedor_combo.clear()
        self.proveedor_combo.addItem("Seleccione un proveedor", None)
        for proveedor in obtener_proveedores():
            self.proveedor_combo.addItem(
                f"{proveedor.get('_id', '')} - {proveedor.get('nombre', '')}",
                {
                    "_id": str(proveedor.get("_id", "")),
                    "nombre": str(proveedor.get("nombre", "")),
                    "telefono": str(proveedor.get("telefono", "")),
                },
            )

    def cargar_inventario(self):
        self.table.setRowCount(0)
        for item in obtener_inventario_reabastecimiento(self.tipo):
            row = self.table.rowCount()
            self.table.insertRow(row)
            codigo = str(item.get("_id", ""))
            nombre = str(item.get("nombre", ""))
            cantidad = int(item.get("cantidad", 0))
            chk = QCheckBox()
            spin = QDoubleSpinBox()
            spin.setMinimum(0)
            spin.setMaximum(999999)
            spin.setDecimals(0)
            self.table.setCellWidget(row, 0, chk)
            self.table.setItem(row, 1, QTableWidgetItem(codigo))
            self.table.setItem(row, 2, QTableWidgetItem(nombre))
            self.table.setItem(row, 3, QTableWidgetItem(str(cantidad)))
            self.table.setCellWidget(row, 4, spin)
        self.table.resizeColumnsToContents()

    def generar_requerimiento(self):
        proveedor = self.proveedor_combo.currentData()
        if not proveedor:
            QMessageBox.warning(self, "Proveedor requerido", "Selecciona un proveedor.")
            return
        precio = float(self.precio_input.value())

        items = []
        for row in range(self.table.rowCount()):
            chk = self.table.cellWidget(row, 0)
            spin = self.table.cellWidget(row, 4)
            if chk is None or spin is None:
                continue
            if not chk.isChecked():
                continue
            codigo = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
            nombre = self.table.item(row, 2).text() if self.table.item(row, 2) else ""
            disponibles = self.table.item(row, 3).text() if self.table.item(row, 3) else "0"
            cantidad = int(spin.value())
            if cantidad <= 0:
                continue
            items.append({
                "codigo": codigo,
                "nombre": nombre,
                "disponibles": disponibles,
                "cantidad_solicitada": cantidad,
            })

        if not items:
            QMessageBox.warning(self, "Sin items", "Selecciona al menos un item y define una cantidad mayor a 0.")
            return

        fecha = datetime.now().strftime("%Y-%m-%d")
        nombre_plantilla = TIPO_A_PLANTILLA.get(self.tipo, "Reabastecimiento_consumible.pdf")
        plantilla_pdf = ruta_recurso(f"ui/requerimiento/{nombre_plantilla}")
        carpeta_salida = os.path.join(obtener_base_pdf(), "requerimientos", "reabastecimiento")
        salida_pdf = obtener_pdf_unico(carpeta_salida, f"Reabastecimiento_{limpiar_nombre_archivo(self.tipo)}_{fecha}")

        self.btn_generar.setEnabled(False)
        try:
            self.crear_pdf_desde_plantilla(plantilla_pdf, salida_pdf, fecha, items, proveedor, precio)
        except Exception as e:
            QMessageBox.critical(self, "Error al generar PDF", f"No se pudo generar el requerimiento:\n{e}")
            return
        finally:
            self.btn_generar.setEnabled(True)

        usuario_actual = ADMIN_USUARIO if admin_state.is_admin() else ""
        ok, mensaje = guardar_requerimiento_reabastecimiento(
            tipo=self.tipo, fecha=fecha, items=items, pdf_path=salida_pdf,
            proveedor=proveedor, precio=precio, creado_por=usuario_actual,
        )
        if not ok:
            QMessageBox.warning(self, "No se pudo guardar", mensaje)
            return
        if self.callback_actualizar:
            self.callback_actualizar()
        QMessageBox.information(self, "Requerimiento creado", f"Requerimiento generado correctamente:\n{salida_pdf}")
        self.close()

    def crear_pdf_desde_plantilla(self, plantilla_pdf, salida_pdf, fecha, items, proveedor, precio):
        import os
        if not os.path.exists(plantilla_pdf):
            raise Exception(f"Plantilla no encontrada: {plantilla_pdf}")
        plantilla = PdfReader(plantilla_pdf)
        if len(plantilla.pages) == 0:
            raise Exception("La plantilla PDF no tiene paginas.")
        pagina_base = plantilla.pages[0]
        ancho = float(pagina_base.mediabox.width)
        alto = float(pagina_base.mediabox.height)

        paginas_overlay = self.crear_overlay_pdf(ancho, alto, fecha, items, proveedor, precio)
        overlay = PdfReader(paginas_overlay)
        writer = PdfWriter()
        for i in range(len(overlay.pages)):
            pagina = plantilla.pages[0]
            pagina.merge_page(overlay.pages[i])
            writer.add_page(pagina)
        with open(salida_pdf, "wb") as f:
            writer.write(f)

    def crear_overlay_pdf(self, ancho, alto, fecha, items, proveedor, precio):
        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=(ancho, alto))
        items_por_pagina = 13
        empresa = obtener_nombre_empresa()
        for indice_inicio in range(0, len(items), items_por_pagina):
            items_pagina = items[indice_inicio:indice_inicio + items_por_pagina]
            numero_pagina = (indice_inicio // items_por_pagina) + 1
            total_paginas = ((len(items) - 1) // items_por_pagina) + 1
            self.dibujar_pagina(c, ancho, alto, fecha, items_pagina, proveedor, precio, numero_pagina, total_paginas, empresa)
            if indice_inicio + items_por_pagina < len(items):
                c.showPage()
        c.save()
        packet.seek(0)
        return packet

    def dibujar_pagina(self, c, ancho, alto, fecha, items, proveedor, precio, numero_pagina, total_paginas, empresa):
        margen_x = 42

        c.line(40, 515, ancho - 40, 515)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margen_x, 500, f"Tipo de requerimiento: {self.tipo.upper()}")
        c.setFont("Helvetica", 9)
        c.drawString(390, 500, f"Fecha: {fecha}")
        c.drawString(margen_x, 485, f"Proveedor: {proveedor.get('nombre', '')}")
        c.drawString(390, 485, f"Costo: $ {precio:.2f}")

        y = 450
        x_codigo, x_nombre, x_disponibles, x_pedido = 45, 130, 360, 465
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x_codigo, y, "Codigo")
        c.drawString(x_nombre, y, "Nombre")
        c.drawString(x_disponibles, y, "Disponibles")
        c.drawString(x_pedido, y, "Cantidad pedida")
        y -= 8
        c.line(40, y, ancho - 40, y)
        y -= 18

        c.setFont("Helvetica", 8)
        for item in items:
            codigo = str(item.get("codigo", ""))
            nombre = str(item.get("nombre", ""))
            disponibles = str(item.get("disponibles", ""))
            cantidad = str(item.get("cantidad_solicitada", ""))
            lineas = simpleSplit(nombre, "Helvetica", 8, 200)
            c.drawString(x_codigo, y, codigo[:15])
            c.drawString(x_nombre, y, lineas[0] if lineas else "")
            c.drawString(x_disponibles, y, disponibles)
            c.drawString(x_pedido, y, cantidad)
            if len(lineas) > 1:
                y -= 10
                c.drawString(x_nombre, y, lineas[1])
            y -= 22

        c.setFont("Helvetica", 8)
        c.drawRightString(ancho - 45, 70, f"Pagina {numero_pagina} de {total_paginas}")



