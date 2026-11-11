from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
)

from config.db_mongo import db
from ui.admin_state import admin_state
from ui.utils import BusquedaConDebounce
from logic.logic_mongo import (
    agregar_maquina, editar_maquina, eliminar_maquina, existe_id,
)
from ui.pages.requerimiento_mantenimiento_page import RequerimientoMantenimientoPage
from ui.pages.informe_mantenimiento_maquinas_page import InformeMantenimientoMaquinasPage


class MaquinasPage(QWidget):
    def __init__(self, navegar_callback=None):
        super().__init__()
        self.setWindowTitle("Maquinas")
        self.seleccionado = False

        layout = QVBoxLayout(self)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar por ID o nombre")
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("ID")
        self.nombre = QLineEdit()
        self.nombre.setPlaceholderText("Nombre")
        self.id_status = QLabel("")

        layout.addWidget(QLabel("Maquinas"))
        layout.addWidget(self.search)
        layout.addWidget(QLabel("ID"))
        layout.addWidget(self.id_input)
        layout.addWidget(self.id_status)
        layout.addWidget(QLabel("Nombre"))
        layout.addWidget(self.nombre)

        botones_layout = QHBoxLayout()
        self.btn_add = QPushButton("Agregar")
        self.btn_edit = QPushButton("Editar")
        self.btn_del = QPushButton("Eliminar")
        self.btn_limpiar = QPushButton("Nuevo / Limpiar")
        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_requerimiento = QPushButton("Crear requerimiento")
        self.btn_informe_mantenimiento = QPushButton("Informe mantenimiento")
        for boton in (self.btn_add, self.btn_edit, self.btn_del, self.btn_limpiar,
                      self.btn_actualizar, self.btn_requerimiento, self.btn_informe_mantenimiento):
            botones_layout.addWidget(boton)
        layout.addLayout(botones_layout)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Disponibilidad", "Estado"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        self.busqueda = BusquedaConDebounce(self.search, self.cargar)
        self.id_input.textChanged.connect(self.validar_id)
        self.btn_add.clicked.connect(self.agregar)
        self.btn_edit.clicked.connect(self.editar)
        self.btn_del.clicked.connect(self.eliminar)
        self.btn_limpiar.clicked.connect(self.limpiar)
        self.btn_actualizar.clicked.connect(self.cargar)
        self.btn_requerimiento.clicked.connect(self.abrir_requerimiento)
        self.btn_informe_mantenimiento.clicked.connect(self.abrir_informe_mantenimiento)
        self.table.itemSelectionChanged.connect(self.cargar_seleccion)
        admin_state.changed.connect(self.aplicar_modo_admin)

        self.limpiar()
        self.aplicar_modo_admin(admin_state.is_admin())

    def aplicar_modo_admin(self, activo):
        self.btn_edit.setEnabled(activo)
        self.btn_del.setEnabled(activo)
        if activo:
            self.btn_edit.setToolTip("")
            self.btn_del.setToolTip("")
        else:
            self.btn_edit.setToolTip("Solo el administrador puede editar maquinas.")
            self.btn_del.setToolTip("Solo el administrador puede eliminar maquinas.")

    def obtener_trabajo_de_maquina(self, maquina_id):
        return db.trabajos.find_one({
            "detalle": {"$elemMatch": {"tipo": "maquina", "id": maquina_id}},
            "estatus": {"$in": ["activo", "pendiente de devolucion"]},
        }, projection={"nombre": 1, "_id": 1})

    def obtener_estado_visible_maquina(self, maquina):
        maquina_id = str(maquina.get("_id", ""))
        estatus = str(maquina.get("estatus", "disponible")).strip().lower()
        if estatus == "trabajando":
            trabajo = self.obtener_trabajo_de_maquina(maquina_id)
            if trabajo:
                punto = trabajo.get("nombre", "Sin nombre de punto")
                trabajo_id = trabajo.get("_id", "")
                return f"Trabajando en: {punto} ({trabajo_id})"
            return "Trabajando"
        if estatus == "mantenimiento":
            return "En mantenimiento"
        if estatus == "disponible":
            return "Disponible"
        return estatus

    def validar_id(self):
        if self.seleccionado:
            self.id_status.setText("Registro seleccionado")
            self.btn_add.setEnabled(False)
            return
        idv = self.id_input.text().strip()
        if not idv:
            self.id_status.setText("")
            self.btn_add.setEnabled(False)
            return
        if existe_id("maquinas", idv):
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
            filtro = {"$or": [{"nombre": patron}]}

        data = list(db.maquinas.find(filtro))
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for maquina in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            valores = [
                maquina.get("_id", ""),
                maquina.get("nombre", ""),
                maquina.get("disponibilidad", ""),
                self.obtener_estado_visible_maquina(maquina),
            ]
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
        self.nombre.setText(self.table.item(row, 1).text())
        self.validar_id()

    def limpiar(self):
        self.seleccionado = False
        self.id_input.setReadOnly(False)
        self.id_input.clear()
        self.nombre.clear()
        self.table.clearSelection()
        self.validar_id()

    def agregar(self):
        if self.seleccionado:
            QMessageBox.warning(self, "Registro seleccionado", "Presiona Nuevo / Limpiar para crear otra maquina.")
            return
        idv = self.id_input.text().strip()
        nom = self.nombre.text().strip()
        if not idv or not nom:
            QMessageBox.warning(self, "Campos incompletos", "Completa el ID y el nombre de la maquina.")
            return
        ok, msg = agregar_maquina(idv, nom)
        if not ok:
            QMessageBox.warning(self, "Error", msg)
            return
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Maquina agregada", "La maquina fue agregada correctamente.")

    def editar(self):
        if not admin_state.is_admin():
            QMessageBox.warning(self, "Acceso restringido", "Solo el administrador puede editar maquinas.")
            return
        if not self.seleccionado:
            QMessageBox.warning(self, "Selecciona una maquina", "Debes seleccionar una maquina para editarla.")
            return
        idv = self.id_input.text().strip()
        nom = self.nombre.text().strip()
        if not idv or not nom:
            QMessageBox.warning(self, "Campos incompletos", "Completa el ID y el nombre de la maquina.")
            return
        resp = QMessageBox.question(
            self, "Confirmar edicion",
            f"¿Deseas guardar los cambios de la maquina {idv}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        ok, msg = editar_maquina(idv, nom)
        if not ok:
            QMessageBox.warning(self, "Error", msg)
            return
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Maquina editada", "Los cambios fueron guardados correctamente.")

    def eliminar(self):
        if not admin_state.is_admin():
            QMessageBox.warning(self, "Acceso restringido", "Solo el administrador puede eliminar maquinas.")
            return
        r = self.table.currentRow()
        if r < 0:
            QMessageBox.warning(self, "Selecciona una maquina", "Debes seleccionar una maquina para eliminarla.")
            return
        idv = self.table.item(r, 0).text()
        maquina = db.maquinas.find_one({"_id": idv}, projection={"disponibilidad": 1})
        if maquina:
            disponibilidad = str(maquina.get("disponibilidad", "")).strip().upper()
            if disponibilidad != "SI":
                QMessageBox.warning(
                    self, "Maquina no disponible",
                    "No se puede eliminar una maquina que esta trabajando o en mantenimiento.",
                )
                return
        resp = QMessageBox.question(
            self, "Confirmar eliminacion",
            f"¿Deseas eliminar la maquina {idv}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        eliminar_maquina(idv)
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Maquina eliminada", "La maquina fue eliminada correctamente.")

    def abrir_requerimiento(self):
        r = self.table.currentRow()
        if r < 0:
            QMessageBox.warning(self, "Selecciona una maquina", "Debes seleccionar una maquina para crear el requerimiento de mantenimiento.")
            return
        codigo = self.table.item(r, 0).text()
        nombre = self.table.item(r, 1).text()
        maquina = db.maquinas.find_one({"_id": codigo}, projection={"disponibilidad": 1, "estatus": 1})
        if not maquina:
            QMessageBox.warning(self, "Maquina no encontrada", "No se encontro la maquina seleccionada en la base de datos.")
            self.cargar()
            return

        disponibilidad = str(maquina.get("disponibilidad", "")).strip().upper()
        estatus = str(maquina.get("estatus", "")).strip().lower()

        if disponibilidad != "SI" or estatus != "disponible":
            if estatus == "trabajando":
                trabajo = self.obtener_trabajo_de_maquina(codigo)
                if trabajo:
                    punto = trabajo.get("nombre", "Sin nombre de punto")
                    trabajo_id = trabajo.get("_id", "")
                    mensaje = (
                        f"No se puede crear un requerimiento de mantenimiento para la maquina:\n\n"
                        f"{codigo} - {nombre}\n\n"
                        f"La maquina actualmente se encuentra asignada a un trabajo.\n\n"
                        f"Punto de trabajo: {punto}\n"
                        f"ID del trabajo: {trabajo_id}"
                    )
                else:
                    mensaje = f"La maquina {codigo} - {nombre} actualmente se encuentra marcada como trabajando."
            elif estatus == "mantenimiento":
                mensaje = f"La maquina {codigo} - {nombre} ya se encuentra en mantenimiento."
            else:
                mensaje = (
                    f"No se puede crear el requerimiento de mantenimiento para la maquina:\n\n"
                    f"{codigo} - {nombre}\n\n"
                    f"Disponibilidad actual: {disponibilidad}\n"
                    f"Estado actual: {estatus}"
                )
            QMessageBox.warning(self, "Maquina no disponible", mensaje)
            self.cargar()
            return

        self.ventana_requerimiento = RequerimientoMantenimientoPage(codigo, nombre, callback_actualizar=self.cargar)
        self.ventana_requerimiento.show()

    def abrir_informe_mantenimiento(self):
        self.ventana_informe_mantenimiento = InformeMantenimientoMaquinasPage(callback_actualizar=self.cargar)
        self.ventana_informe_mantenimiento.show()

