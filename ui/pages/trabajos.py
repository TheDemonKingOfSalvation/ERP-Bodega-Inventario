from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox,
)

from config.db_mongo import db
from ui.admin_state import admin_state
from ui.utils import abrir_archivo, BusquedaConDebounce
from logic.logic_mongo import (
    crear_trabajo, eliminar_trabajo, finalizar_trabajo, revertir_trabajo,
)


class TrabajosPage(QWidget):
    def __init__(self, navegar_callback=None):
        super().__init__()
        self.setWindowTitle("Trabajos")
        self.seleccionado = False

        layout = QVBoxLayout(self)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar por ID, planta o estado")
        self.planta = QLineEdit()
        self.planta.setPlaceholderText("Punto / Planta")

        layout.addWidget(QLabel("Trabajos"))
        layout.addWidget(self.search)
        layout.addWidget(QLabel("Punto / Planta"))
        layout.addWidget(self.planta)

        b = QHBoxLayout()
        self.btn_crear = QPushButton("Crear")
        self.btn_editar = QPushButton("Editar")
        self.btn_eliminar = QPushButton("Eliminar")
        self.btn_finalizar = QPushButton("Finalizar")
        self.btn_revertir = QPushButton("Revertir")
        self.btn_detalle = QPushButton("Detalles")
        self.btn_limpiar = QPushButton("Limpiar")
        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_abrir_salida_bodega = QPushButton("Abrir PDF salida bodega")
        self.btn_abrir_herramientas_faltantes = QPushButton("Abrir herramientas faltantes")

        for x in (
            self.btn_crear, self.btn_editar, self.btn_eliminar,
            self.btn_finalizar, self.btn_revertir, self.btn_detalle,
            self.btn_limpiar, self.btn_actualizar,
            self.btn_abrir_salida_bodega, self.btn_abrir_herramientas_faltantes,
        ):
            b.addWidget(x)
        layout.addLayout(b)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Punto / Planta", "Estado", "Fecha inicio"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        self.busqueda = BusquedaConDebounce(self.search, self.cargar)

        self.btn_crear.clicked.connect(self.crear)
        self.btn_editar.clicked.connect(self.editar)
        self.btn_eliminar.clicked.connect(self.eliminar)
        self.btn_finalizar.clicked.connect(self.finalizar)
        self.btn_revertir.clicked.connect(self.revertir)
        self.btn_detalle.clicked.connect(self.abrir_detalle)
        self.btn_limpiar.clicked.connect(self.limpiar)
        self.btn_actualizar.clicked.connect(self.cargar)
        self.btn_abrir_salida_bodega.clicked.connect(self.abrir_pdf_salida_bodega)
        self.btn_abrir_herramientas_faltantes.clicked.connect(self.abrir_pdf_herramientas_faltantes)
        self.table.itemSelectionChanged.connect(self.cargar_seleccion)
        admin_state.changed.connect(self.aplicar_modo_admin)

        self.aplicar_modo_admin(admin_state.is_admin())

    def aplicar_modo_admin(self, activo):
        self.btn_editar.setEnabled(activo)
        self.btn_eliminar.setEnabled(activo)
        if activo:
            self.btn_editar.setToolTip("")
            self.btn_eliminar.setToolTip("")
        else:
            self.btn_editar.setToolTip("Solo el administrador puede editar trabajos.")
            self.btn_eliminar.setToolTip("Solo el administrador puede eliminar trabajos.")

    def cargar(self):
        texto = self.search.text().strip()
        patron = {"$regex": texto, "$options": "i"} if texto else None
        filtro = {}
        if patron:
            filtro = {"$or": [{"nombre": patron}, {"estatus": patron}]}

        data = list(db.trabajos.find(filtro, projection={"_id": 1, "nombre": 1, "estatus": 1, "fecha_inicio": 1}).sort("fecha_inicio", -1))

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for row in data:
            i = self.table.rowCount()
            self.table.insertRow(i)
            vals = [row.get("_id", ""), row.get("nombre", ""), row.get("estatus", ""), str(row.get("fecha_inicio", ""))[:19]]
            for c, v in enumerate(vals):
                self.table.setItem(i, c, QTableWidgetItem(str(v)))

        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        self.actualizar_botones()

    def cargar_seleccion(self):
        r = self.table.currentRow()
        if r < 0:
            self.seleccionado = False
            self.planta.clear()
            self.actualizar_botones()
            return
        self.seleccionado = True
        self.planta.setText(self.table.item(r, 1).text())
        self.actualizar_botones()

    def get_id(self):
        r = self.table.currentRow()
        return None if r < 0 else self.table.item(r, 0).text()

    def actualizar_botones(self):
        idv = self.get_id()
        salida_path = ""
        no_dev_path = ""
        if idv:
            trabajo = db.trabajos.find_one(
                {"_id": idv},
                projection={"pdf_salida_bodega": 1, "pdf_no_devueltos": 1},
            )
            if trabajo:
                salida_path = trabajo.get("pdf_salida_bodega", "")
                no_dev_path = trabajo.get("pdf_no_devueltos", "")

        import os
        self.btn_abrir_salida_bodega.setEnabled(bool(salida_path and os.path.exists(salida_path)))
        self.btn_abrir_herramientas_faltantes.setEnabled(bool(no_dev_path and os.path.exists(no_dev_path)))

    def abrir_pdf_salida_bodega(self):
        idv = self.get_id()
        if not idv:
            QMessageBox.warning(self, "Selecciona un trabajo", "Debes seleccionar un trabajo.")
            return
        trabajo = db.trabajos.find_one({"_id": idv}, projection={"pdf_salida_bodega": 1})
        ruta = trabajo.get("pdf_salida_bodega", "") if trabajo else ""
        abrir_archivo(ruta, self)

    def abrir_pdf_herramientas_faltantes(self):
        idv = self.get_id()
        if not idv:
            QMessageBox.warning(self, "Selecciona un trabajo", "Debes seleccionar un trabajo.")
            return
        trabajo = db.trabajos.find_one({"_id": idv}, projection={"pdf_no_devueltos": 1})
        ruta = trabajo.get("pdf_no_devueltos", "") if trabajo else ""
        abrir_archivo(ruta, self)

    def limpiar(self):
        self.seleccionado = False
        self.planta.clear()
        self.table.clearSelection()

    def crear(self):
        if self.seleccionado:
            QMessageBox.warning(self, "Registro seleccionado", "Presiona Limpiar para crear otro trabajo.")
            return
        planta = self.planta.text().strip()
        if not planta:
            QMessageBox.warning(self, "Campos incompletos", "Completa punto/planta.")
            return
        crear_trabajo(planta)
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Trabajo creado", "El trabajo fue creado correctamente.")

    def editar(self):
        if not admin_state.is_admin():
            QMessageBox.warning(self, "Acceso restringido", "Solo el administrador puede editar trabajos.")
            return
        idv = self.get_id()
        if not idv:
            QMessageBox.warning(self, "Selecciona un trabajo", "Debes seleccionar un trabajo para editarlo.")
            return
        planta = self.planta.text().strip()
        if not planta:
            QMessageBox.warning(self, "Campos incompletos", "Completa punto/planta.")
            return
        resp = QMessageBox.question(
            self, "Confirmar edicion",
            f"¿Deseas guardar los cambios del trabajo {idv}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        db.trabajos.update_one({"_id": idv}, {"$set": {"nombre": planta}})
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Trabajo editado", "Los cambios fueron guardados correctamente.")

    def eliminar(self):
        if not admin_state.is_admin():
            QMessageBox.warning(self, "Acceso restringido", "Solo el administrador puede eliminar trabajos.")
            return
        idv = self.get_id()
        if not idv:
            QMessageBox.warning(self, "Selecciona un trabajo", "Debes seleccionar un trabajo.")
            return
        resp = QMessageBox.question(
            self, "Confirmar eliminacion", f"¿Eliminar trabajo {idv}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        eliminar_trabajo(idv)
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Trabajo eliminado", "El trabajo fue eliminado correctamente.")

    def finalizar(self):
        idv = self.get_id()
        if not idv:
            QMessageBox.warning(self, "Selecciona un trabajo", "Debes seleccionar un trabajo.")
            return
        resp = QMessageBox.question(
            self, "Finalizar",
            "¿Finalizar trabajo? Si hay faltantes quedara como pendiente de devolucion.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        ok, msg = finalizar_trabajo(idv)
        if not ok:
            QMessageBox.warning(self, "Error", msg)
            return
        self.cargar()
        QMessageBox.information(self, "Trabajo actualizado", "Trabajo finalizado / actualizado correctamente.")

    def revertir(self):
        idv = self.get_id()
        if not idv:
            QMessageBox.warning(self, "Selecciona un trabajo", "Debes seleccionar un trabajo.")
            return
        revertir_trabajo(idv)
        self.cargar()
        QMessageBox.information(self, "Trabajo revertido", "El trabajo fue revertido correctamente.")

    def abrir_detalle(self):
        idv = self.get_id()
        if not idv:
            QMessageBox.warning(self, "Selecciona un trabajo", "Debes seleccionar un trabajo.")
            return
        from ui.pages.trabajo_detalle import TrabajoDetallePage
        self.detalle = TrabajoDetallePage(idv)
        self.detalle.show()

