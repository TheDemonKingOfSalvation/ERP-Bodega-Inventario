from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
)

from config.db_mongo import db
from ui.admin_state import admin_state
from ui.utils import BusquedaConDebounce
from logic.logic_mongo import (
    agregar_herramienta, editar_herramienta, eliminar_herramienta,
    existe_id, obtener_usados_herramientas_batch,
)
from ui.pages.requerimiento_reabastecimiento_page import RequerimientoReabastecimientoPage
from ui.pages.informe_reabastecimiento_page import InformeReabastecimientoPage


class HerramientasPage(QWidget):
    def __init__(self, navegar_callback=None):
        super().__init__()
        self.setWindowTitle("Herramientas")
        self.resize(900, 500)
        self.seleccionado = False

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Herramientas"))

        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar por ID o nombre")
        layout.addWidget(self.search)

        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("ID")
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText("Nombre")
        self.cantidad_input = QSpinBox()
        self.cantidad_input.setMinimum(0)
        self.cantidad_input.setMaximum(999999)
        self.id_status = QLabel("")

        layout.addWidget(QLabel("ID"))
        layout.addWidget(self.id_input)
        layout.addWidget(self.id_status)
        layout.addWidget(QLabel("Nombre"))
        layout.addWidget(self.nombre_input)
        layout.addWidget(QLabel("Cantidad total"))
        layout.addWidget(self.cantidad_input)

        botones_layout = QHBoxLayout()
        self.btn_agregar = QPushButton("Agregar")
        self.btn_editar = QPushButton("Editar")
        self.btn_eliminar = QPushButton("Eliminar")
        self.btn_limpiar = QPushButton("Nuevo / Limpiar")
        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_reabastecimiento = QPushButton("Crear requerimiento")
        self.btn_ver_reabastecimiento = QPushButton("Ver requerimientos")
        for boton in (self.btn_agregar, self.btn_editar, self.btn_eliminar,
                      self.btn_limpiar, self.btn_actualizar):
            botones_layout.addWidget(boton)
        layout.addLayout(botones_layout)

        self.layout().insertWidget(self.layout().count() - 1, self.btn_reabastecimiento)
        self.layout().insertWidget(self.layout().count() - 1, self.btn_ver_reabastecimiento)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Cantidad total", "Usados", "Disponibles"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        self.busqueda = BusquedaConDebounce(self.search, self.cargar)
        self.id_input.textChanged.connect(self.validar_id)
        self.btn_agregar.clicked.connect(self.agregar)
        self.btn_editar.clicked.connect(self.editar)
        self.btn_eliminar.clicked.connect(self.eliminar)
        self.btn_limpiar.clicked.connect(self.limpiar)
        self.btn_actualizar.clicked.connect(self.cargar)
        self.table.itemSelectionChanged.connect(self.cargar_seleccion)
        self.btn_reabastecimiento.clicked.connect(self.abrir_requerimiento_reabastecimiento)
        self.btn_ver_reabastecimiento.clicked.connect(self.abrir_informe_reabastecimiento)
        admin_state.changed.connect(self.aplicar_modo_admin)

        self.limpiar()
        self.aplicar_modo_admin(admin_state.is_admin())

    def aplicar_modo_admin(self, activo):
        self.btn_editar.setEnabled(activo)
        self.btn_eliminar.setEnabled(activo)
        if activo:
            self.btn_editar.setToolTip("")
            self.btn_eliminar.setToolTip("")
        else:
            self.btn_editar.setToolTip("Solo el administrador puede editar herramientas.")
            self.btn_eliminar.setToolTip("Solo el administrador puede eliminar herramientas.")

    def validar_id(self):
        if self.seleccionado:
            self.id_status.setText("Registro seleccionado")
            self.btn_agregar.setEnabled(False)
            return
        id_val = self.id_input.text().strip()
        if not id_val:
            self.id_status.setText("")
            self.btn_agregar.setEnabled(False)
            return
        if existe_id("herramientas", id_val):
            self.id_status.setText("ID ya existe")
            self.btn_agregar.setEnabled(False)
        else:
            self.id_status.setText("ID disponible")
            self.btn_agregar.setEnabled(True)

    def cargar(self):
        texto = self.search.text().strip()
        patron = {"$regex": texto, "$options": "i"} if texto else None
        filtro = {}
        if patron:
            filtro = {"$or": [{"nombre": patron}]}

        herramientas = list(db.herramientas.find(filtro))
        usados_por_id = obtener_usados_herramientas_batch()

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for doc in herramientas:
            row = self.table.rowCount()
            self.table.insertRow(row)
            codigo = str(doc.get("_id", ""))
            cantidad_total = int(doc.get("cantidad", 0))
            usados = int(usados_por_id.get(codigo, 0))
            disponibles = max(cantidad_total - usados, 0)
            valores = [codigo, doc.get("nombre", ""), cantidad_total, usados, disponibles]
            for c, v in enumerate(valores):
                self.table.setItem(row, c, QTableWidgetItem(str(v)))
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()

    def cargar_seleccion(self):
        row = self.table.currentRow()
        if row < 0:
            return
        self.seleccionado = True
        self.id_input.setReadOnly(True)
        self.id_input.setText(self.table.item(row, 0).text())
        self.nombre_input.setText(self.table.item(row, 1).text())
        try:
            cantidad = int(self.table.item(row, 2).text())
        except ValueError:
            cantidad = 0
        self.cantidad_input.setValue(cantidad)
        self.validar_id()

    def limpiar(self):
        self.seleccionado = False
        self.id_input.setReadOnly(False)
        self.id_input.clear()
        self.nombre_input.clear()
        self.cantidad_input.setValue(0)
        self.table.clearSelection()
        self.validar_id()

    def _leer_datos(self):
        codigo = self.id_input.text().strip()
        nombre = self.nombre_input.text().strip()
        cantidad = self.cantidad_input.value()
        if not codigo or not nombre:
            QMessageBox.warning(self, "Campos incompletos", "Completa el ID y el nombre de la herramienta.")
            return None
        if cantidad <= 0:
            QMessageBox.warning(self, "Cantidad invalida", "La cantidad total debe ser mayor a 0.")
            return None
        return codigo, nombre, cantidad

    def agregar(self):
        if self.seleccionado:
            QMessageBox.warning(self, "Registro seleccionado", "Presiona Nuevo / Limpiar para crear otra herramienta.")
            return
        datos = self._leer_datos()
        if not datos:
            return
        codigo, nombre, cantidad = datos
        ok, mensaje = agregar_herramienta(codigo, nombre, cantidad)
        if not ok:
            QMessageBox.warning(self, "Error", mensaje)
            return
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Herramienta agregada", "La herramienta fue agregada correctamente.")

    def editar(self):
        if not admin_state.is_admin():
            QMessageBox.warning(self, "Acceso restringido", "Solo el administrador puede editar herramientas.")
            return
        if not self.seleccionado:
            QMessageBox.warning(self, "Selecciona una herramienta", "Debes seleccionar una herramienta para editarla.")
            return
        datos = self._leer_datos()
        if not datos:
            return
        codigo, nombre, cantidad = datos
        usados = int(obtener_usados_herramientas_batch().get(codigo, 0))
        if cantidad < usados:
            QMessageBox.warning(
                self, "Cantidad invalida",
                f"No puedes colocar una cantidad menor a las unidades en uso.\n\nUsados actualmente: {usados}",
            )
            return
        respuesta = QMessageBox.question(
            self, "Confirmar edicion",
            f"¿Deseas guardar los cambios de la herramienta {codigo} - {nombre}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if respuesta != QMessageBox.Yes:
            return
        ok, mensaje = editar_herramienta(codigo, nombre, cantidad)
        if not ok:
            QMessageBox.warning(self, "Error", mensaje)
            return
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Herramienta editada", "Los cambios fueron guardados correctamente.")

    def eliminar(self):
        if not admin_state.is_admin():
            QMessageBox.warning(self, "Acceso restringido", "Solo el administrador puede eliminar herramientas.")
            return
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selecciona una herramienta", "Debes seleccionar una herramienta para eliminarla.")
            return
        codigo = self.table.item(row, 0).text()
        nombre = self.table.item(row, 1).text()
        usados = int(obtener_usados_herramientas_batch().get(codigo, 0))
        if usados > 0:
            QMessageBox.warning(
                self, "Herramienta en uso",
                f"No se puede eliminar la herramienta:\n\n{codigo} - {nombre}\n\nActualmente tiene {usados} unidad(es) asignada(s) a puntos de trabajo.",
            )
            return
        respuesta = QMessageBox.question(
            self, "Confirmar eliminacion",
            f"¿Deseas eliminar la herramienta {codigo} - {nombre}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if respuesta != QMessageBox.Yes:
            return
        eliminar_herramienta(codigo)
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Herramienta eliminada", "La herramienta fue eliminada correctamente.")

    def abrir_requerimiento_reabastecimiento(self):
        self.ventana_reabastecimiento = RequerimientoReabastecimientoPage("herramienta")
        self.ventana_reabastecimiento.show()

    def abrir_informe_reabastecimiento(self):
        self.ventana_informe_reabastecimiento = InformeReabastecimientoPage("herramienta", callback_actualizar=self.cargar)
        self.ventana_informe_reabastecimiento.show()

