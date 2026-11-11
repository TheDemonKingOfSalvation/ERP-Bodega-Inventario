from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
)
from PySide6.QtGui import QIntValidator

from config.db_mongo import db
from ui.admin_state import admin_state
from ui.utils import BusquedaConDebounce
from ui.pages.carro_km_page import CarroKilometrajePage
from ui.pages.carro_tanqueo_page import CarroTanqueoPage


class CarrosPage(QWidget):
    def __init__(self, navegar_callback=None):
        super().__init__()
        self.setWindowTitle("Carros")
        self.resize(900, 500)
        self.navegar_callback = navegar_callback

        layout = QVBoxLayout(self)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar por ID o nombre")
        layout.addWidget(QLabel("Carros"))
        layout.addWidget(self.search)

        form_layout = QGridLayout()
        form_layout.addWidget(QLabel("ID"), 0, 0)
        self.id_input = QLineEdit()
        form_layout.addWidget(self.id_input, 0, 1)
        self.id_status = QLabel("")
        form_layout.addWidget(self.id_status, 0, 2)

        form_layout.addWidget(QLabel("Placa / Nombre"), 1, 0)
        self.nombre = QLineEdit()
        form_layout.addWidget(self.nombre, 1, 1)

        form_layout.addWidget(QLabel("Descripcion"), 2, 0)
        self.descripcion = QLineEdit()
        form_layout.addWidget(self.descripcion, 2, 1)

        form_layout.addWidget(QLabel("Km cambio aceite"), 3, 0)
        self.km_interval = QLineEdit()
        self.km_interval.setValidator(QIntValidator(0, 10000000))
        form_layout.addWidget(self.km_interval, 3, 1)

        layout.addLayout(form_layout)

        btns = QHBoxLayout()
        self.btn_add = QPushButton("Agregar")
        self.btn_edit = QPushButton("Editar")
        self.btn_del = QPushButton("Eliminar")
        self.btn_nuevo = QPushButton("Nuevo / Limpiar")
        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_km = QPushButton("Registro kilometraje")
        self.btn_tanqueo = QPushButton("Registro tanqueo")
        for boton in (
            self.btn_add, self.btn_edit, self.btn_del, self.btn_nuevo,
            self.btn_actualizar, self.btn_km, self.btn_tanqueo,
        ):
            btns.addWidget(boton)
        layout.addLayout(btns)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Placa / Nombre", "Descripcion", "Km cambio aceite"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        self.busqueda = BusquedaConDebounce(self.search, self.cargar)
        self.id_input.textChanged.connect(self.validar_id)
        self.btn_add.clicked.connect(self.agregar)
        self.btn_edit.clicked.connect(self.editar)
        self.btn_del.clicked.connect(self.eliminar)
        self.btn_nuevo.clicked.connect(self.limpiar)
        self.btn_actualizar.clicked.connect(self.cargar)
        self.btn_km.clicked.connect(self.abrir_kilometraje)
        self.btn_tanqueo.clicked.connect(self.abrir_tanqueo)
        self.table.itemSelectionChanged.connect(self.cargar_seleccion)
        admin_state.changed.connect(self.aplicar_modo_admin)

        self.limpiar()
        self.aplicar_modo_admin(admin_state.is_admin())

    def aplicar_modo_admin(self, activo):
        self.btn_del.setEnabled(activo)
        self.btn_edit.setEnabled(activo)
        if activo:
            self.btn_del.setToolTip("")
            self.btn_edit.setToolTip("")
        else:
            self.btn_del.setToolTip("Solo el administrador puede eliminar registros.")
            self.btn_edit.setToolTip("Solo el administrador puede editar registros.")

    def validar_id(self):
        id_val = self.id_input.text().strip()
        if not id_val:
            self.id_status.setText("")
            self.btn_add.setEnabled(False)
            return
        existe = db.carros.find_one({"_id": id_val}, projection={"_id": 1}) is not None
        if existe:
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
            filtro = {"$or": [{"nombre": patron}, {"descripcion": patron}, {"placa": patron}]}

        data = list(db.carros.find(filtro, projection={
            "_id": 1, "nombre": 1, "placa": 1, "descripcion": 1, "km_cambio_intervalo": 1,
        }))
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for doc in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            valores = [
                doc.get("_id", ""),
                doc.get("nombre") or doc.get("placa") or "",
                doc.get("descripcion", ""),
                doc.get("km_cambio_intervalo", ""),
            ]
            for c, v in enumerate(valores):
                self.table.setItem(row, c, QTableWidgetItem(str(v)))
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()

    def cargar_seleccion(self):
        row = self.table.currentRow()
        if row < 0:
            return
        id_val = self.table.item(row, 0).text()
        doc = db.carros.find_one({"_id": id_val})
        if not doc:
            return
        self.id_input.setReadOnly(True)
        self.id_input.setText(str(doc.get("_id", "")))
        self.nombre.setText(str(doc.get("nombre") or doc.get("placa") or ""))
        self.descripcion.setText(str(doc.get("descripcion", "")))
        self.km_interval.setText(str(doc.get("km_cambio_intervalo", "")))

    def limpiar(self):
        self.id_input.setReadOnly(False)
        self.id_input.clear()
        self.nombre.clear()
        self.descripcion.clear()
        self.km_interval.clear()
        self.table.clearSelection()

    def agregar(self):
        id_val = self.id_input.text().strip()
        nombre = self.nombre.text().strip()
        descripcion = self.descripcion.text().strip()
        km_int = self._leer_km()
        if km_int is None:
            return
        if not id_val or not nombre:
            QMessageBox.warning(self, "Campos incompletos", "Completa ID y Nombre.")
            return
        if db.carros.find_one({"_id": id_val}, projection={"_id": 1}):
            QMessageBox.warning(self, "ID existente", "El ID ya existe.")
            return
        doc = {"_id": id_val, "nombre": nombre, "descripcion": descripcion}
        if km_int is not None:
            doc["km_cambio_intervalo"] = km_int
        db.carros.insert_one(doc)
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Registro agregado", "El carro fue agregado correctamente.")

    def editar(self):
        if not admin_state.is_admin():
            QMessageBox.warning(self, "Acceso restringido", "Solo el administrador puede editar registros.")
            return
        if not self.id_input.isReadOnly():
            QMessageBox.warning(self, "Selecciona un registro", "Debes seleccionar un registro para editarlo.")
            return
        id_val = self.id_input.text().strip()
        nombre = self.nombre.text().strip()
        descripcion = self.descripcion.text().strip()
        km_int = self._leer_km()
        if km_int is None:
            return
        if not id_val or not nombre:
            QMessageBox.warning(self, "Campos incompletos", "Completa ID y Nombre.")
            return
        resp = QMessageBox.question(
            self, "Confirmar edicion",
            f"¿Deseas guardar los cambios del carro {id_val}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        update = {"nombre": nombre, "descripcion": descripcion}
        if km_int is not None:
            update["km_cambio_intervalo"] = km_int
        db.carros.update_one({"_id": id_val}, {"$set": update})
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Registro editado", "Los cambios fueron guardados correctamente.")

    def eliminar(self):
        if not admin_state.is_admin():
            QMessageBox.warning(self, "Acceso restringido", "Solo el administrador puede eliminar registros.")
            return
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selecciona un registro", "Debes seleccionar un registro para eliminarlo.")
            return
        id_val = self.table.item(row, 0).text()
        resp = QMessageBox.question(
            self, "Confirmar eliminacion",
            f"¿Seguro que deseas eliminar {id_val}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        db.carros.delete_one({"_id": id_val})
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Registro eliminado", "El registro fue eliminado correctamente.")

    def _leer_km(self):
        texto = self.km_interval.text().strip()
        if not texto:
            return 0
        try:
            return int(texto)
        except ValueError:
            QMessageBox.warning(self, "Km invalido", "El valor de Km cambio aceite debe ser un numero entero.")
            return None

    def abrir_kilometraje(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selecciona un carro", "Debes seleccionar un carro para ver el registro de kilometraje.")
            return
        item = self.table.item(row, 0)
        if item is None:
            return
        self.km_page = CarroKilometrajePage(item.text())
        self.km_page.show()

    def abrir_tanqueo(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selecciona un carro", "Debes seleccionar un carro para ver el registro de tanqueo.")
            return
        item = self.table.item(row, 0)
        if item is None:
            return
        self.tanqueo_page = CarroTanqueoPage(item.text())
        self.tanqueo_page.show()
