from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
)

from config.db_mongo import db
from ui.admin_state import admin_state
from ui.utils import BusquedaConDebounce
from logic.logic_mongo import (
    agregar_trabajador, editar_trabajador, eliminar_trabajador, existe_id,
)


class TrabajadoresPage(QWidget):
    def __init__(self, navegar_callback=None):
        super().__init__()
        self.setWindowTitle("Trabajadores")
        self.seleccionado = False

        layout = QVBoxLayout(self)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar por ID o nombre")
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("ID")
        self.nombre = QLineEdit()
        self.nombre.setPlaceholderText("Nombre")
        self.tipo = QComboBox()
        self.tipo.addItems(["supervisor", "soldador", "conductor"])
        self.id_status = QLabel("")

        layout.addWidget(QLabel("Trabajadores"))
        layout.addWidget(self.search)
        layout.addWidget(QLabel("ID"))
        layout.addWidget(self.id_input)
        layout.addWidget(self.id_status)
        layout.addWidget(QLabel("Nombre"))
        layout.addWidget(self.nombre)
        layout.addWidget(QLabel("Cargo"))
        layout.addWidget(self.tipo)

        b = QHBoxLayout()
        self.btn_add = QPushButton("Agregar")
        self.btn_editar = QPushButton("Editar")
        self.btn_eliminar = QPushButton("Eliminar")
        self.btn_agregar_epp = QPushButton("Agregar EPP")
        self.btn_informe_epp = QPushButton("Informe EPP")
        self.btn_limpiar = QPushButton("Nuevo / Limpiar")
        self.btn_actualizar = QPushButton("Actualizar")
        for x in (self.btn_add, self.btn_editar, self.btn_eliminar,
                  self.btn_agregar_epp, self.btn_informe_epp,
                  self.btn_limpiar, self.btn_actualizar):
            b.addWidget(x)
        layout.addLayout(b)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Tipo"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        self.busqueda = BusquedaConDebounce(self.search, self.cargar)
        self.id_input.textChanged.connect(self.validar_id)
        self.btn_add.clicked.connect(self.agregar)
        self.btn_editar.clicked.connect(self.editar)
        self.btn_eliminar.clicked.connect(self.eliminar)
        self.btn_agregar_epp.clicked.connect(self.abrir_agregar_epp)
        self.btn_informe_epp.clicked.connect(self.abrir_informe_epp)
        self.btn_limpiar.clicked.connect(self.limpiar)
        self.btn_actualizar.clicked.connect(self.cargar)
        self.table.itemSelectionChanged.connect(self.cargar_seleccion)
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
            self.btn_editar.setToolTip("Solo el administrador puede editar trabajadores.")
            self.btn_eliminar.setToolTip("Solo el administrador puede eliminar trabajadores.")

    def validar_id(self):
        idv = self.id_input.text().strip()
        if self.seleccionado:
            self.id_status.setText("Registro seleccionado")
            self.btn_add.setEnabled(False)
            return
        if not idv:
            self.id_status.setText("")
            self.btn_add.setEnabled(False)
            return
        if existe_id("trabajadores", idv):
            self.id_status.setText("ID ya existe")
            self.btn_add.setEnabled(False)
        else:
            self.id_status.setText("ID disponible")
            self.btn_add.setEnabled(True)

    def cargar(self):
        texto = self.search.text().strip()
        patron = {"$regex": texto, "$options": "i"} if texto else None
        filtro = {}
        if patron:
            filtro = {"$or": [{"nombre": patron}, {"tipo": patron}]}

        data = list(db.trabajadores.find(filtro, projection={"_id": 1, "nombre": 1, "tipo": 1}))
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for row in data:
            i = self.table.rowCount()
            self.table.insertRow(i)
            for c, v in enumerate([row.get("_id", ""), row.get("nombre", ""), row.get("tipo", "")]):
                self.table.setItem(i, c, QTableWidgetItem(str(v)))
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()

    def cargar_seleccion(self):
        r = self.table.currentRow()
        if r < 0:
            return
        self.seleccionado = True
        self.id_input.setReadOnly(True)
        self.id_input.setText(self.table.item(r, 0).text())
        self.nombre.setText(self.table.item(r, 1).text())
        cargo = self.table.item(r, 2).text()
        idx = self.tipo.findText(cargo)
        self.tipo.setCurrentIndex(idx if idx >= 0 else 0)
        self.validar_id()

    def limpiar(self):
        self.seleccionado = False
        self.id_input.setReadOnly(False)
        self.id_input.clear()
        self.nombre.clear()
        self.tipo.setCurrentIndex(0)
        self.table.clearSelection()
        self.validar_id()

    def _leer_datos(self):
        idv = self.id_input.text().strip()
        nom = self.nombre.text().strip()
        cargo = self.tipo.currentText().strip()
        if not idv or not nom:
            QMessageBox.warning(self, "Campos incompletos", "Completa el ID y el nombre.")
            return None
        return idv, nom, cargo

    def agregar(self):
        if self.seleccionado:
            QMessageBox.warning(self, "Registro seleccionado", "Presiona Nuevo / Limpiar para crear otro trabajador.")
            return
        datos = self._leer_datos()
        if not datos:
            return
        idv, nom, cargo = datos
        ok, msg = agregar_trabajador(idv, nom, cargo)
        if not ok:
            QMessageBox.warning(self, "Error", msg)
            return
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Trabajador agregado", "El trabajador fue agregado correctamente.")

    def editar(self):
        if not admin_state.is_admin():
            QMessageBox.warning(self, "Acceso restringido", "Solo el administrador puede editar trabajadores.")
            return
        if not self.seleccionado:
            QMessageBox.warning(self, "Selecciona un trabajador", "Debes seleccionar un trabajador para editarlo.")
            return
        datos = self._leer_datos()
        if not datos:
            return
        idv, nom, cargo = datos
        resp = QMessageBox.question(
            self, "Confirmar edicion",
            f"¿Deseas guardar los cambios del trabajador {idv}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        ok, msg = editar_trabajador(idv, nom, cargo)
        if not ok:
            QMessageBox.warning(self, "Error", msg)
            return
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Trabajador editado", "Los cambios fueron guardados correctamente.")

    def eliminar(self):
        if not admin_state.is_admin():
            QMessageBox.warning(self, "Acceso restringido", "Solo el administrador puede eliminar trabajadores.")
            return
        r = self.table.currentRow()
        if r < 0:
            QMessageBox.warning(self, "Selecciona un trabajador", "Debes seleccionar un trabajador para eliminarlo.")
            return
        idv = self.table.item(r, 0).text()
        resp = QMessageBox.question(
            self, "Confirmar eliminacion",
            f"¿Eliminar trabajador {idv}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        eliminar_trabajador(idv)
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Trabajador eliminado", "El trabajador fue eliminado correctamente.")

    def get_trabajador_id(self):
        r = self.table.currentRow()
        if r < 0:
            QMessageBox.warning(self, "Error", "Selecciona un trabajador")
            return None
        return self.table.item(r, 0).text()

    def abrir_agregar_epp(self):
        tid = self.get_trabajador_id()
        if not tid:
            return
        from ui.pages.trabajador_epp_agregar import TrabajadorEppAgregarPage
        self.ventana_agregar_epp = TrabajadorEppAgregarPage(tid)
        self.ventana_agregar_epp.show()

    def abrir_informe_epp(self):
        tid = self.get_trabajador_id()
        if not tid:
            return
        from ui.pages.trabajador_epp_informe import TrabajadorEppInformePage
        self.ventana_informe_epp = TrabajadorEppInformePage(tid)
        self.ventana_informe_epp.show()

