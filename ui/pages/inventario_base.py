from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
)

from config.db_mongo import db
from ui.admin_state import admin_state
from ui.utils import BusquedaConDebounce


def safe_int(texto, default=0):
    try:
        return int(str(texto).strip())
    except Exception:
        return default


class InventarioBasePage(QWidget):
    def __init__(
        self,
        titulo,
        coleccion,
        agregar_fn,
        editar_fn,
        eliminar_fn,
        campos_extra=None,
        tiene_stock=True,
        botones_extra=None,
        usar_stock_minimo=False,
        navegar_callback=None,
    ):
        super().__init__()

        self.titulo = titulo
        self.coleccion = coleccion
        self.agregar_fn = agregar_fn
        self.editar_fn = editar_fn
        self.eliminar_fn = eliminar_fn
        self.campos_extra = campos_extra or []
        self.tiene_stock = tiene_stock
        self.fila_seleccionada = False
        self.botones_extra = botones_extra or []
        self.usar_stock_minimo = usar_stock_minimo
        self.navegar_callback = navegar_callback

        self.setWindowTitle(titulo)
        layout = QVBoxLayout(self)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar por ID o nombre")
        layout.addWidget(QLabel(f"{titulo}"))
        layout.addWidget(self.search)

        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("ID")
        self.nombre = QLineEdit()
        self.nombre.setPlaceholderText("Nombre")
        self.cantidad = QLineEdit()
        self.cantidad.setPlaceholderText("Cantidad")
        self.id_status = QLabel("")

        layout.addWidget(QLabel("ID"))
        layout.addWidget(self.id_input)
        layout.addWidget(self.id_status)
        layout.addWidget(QLabel("Nombre"))
        layout.addWidget(self.nombre)

        if self.tiene_stock:
            layout.addWidget(QLabel("Cantidad"))
            layout.addWidget(self.cantidad)

        self.extra_widgets = {}
        for campo in self.campos_extra:
            layout.addWidget(QLabel(campo["label"]))
            if campo.get("type") == "combo":
                widget = QComboBox()
                widget.addItems(campo.get("items", []))
            else:
                widget = QLineEdit()
                widget.setPlaceholderText(campo["label"])
            self.extra_widgets[campo["name"]] = widget
            layout.addWidget(widget)

        btns = QHBoxLayout()
        self.btn_add = QPushButton("Agregar")
        self.btn_edit = QPushButton("Editar")
        self.btn_del = QPushButton("Eliminar")
        self.btn_nuevo = QPushButton("Nuevo / Limpiar")
        self.btn_actualizar = QPushButton("Actualizar")
        for boton in (self.btn_add, self.btn_edit, self.btn_del, self.btn_nuevo, self.btn_actualizar):
            btns.addWidget(boton)
        layout.addLayout(btns)

        for label, callback in self.botones_extra:
            b = QPushButton(label)
            b.clicked.connect(callback)
            layout.addWidget(b)

        self.btn_reabastecimiento = None
        self.btn_ver_reabastecimiento = None
        if self.coleccion in ("epp", "consumibles", "pvc", "herramientas"):
            self.btn_reabastecimiento = QPushButton("Crear requerimiento")
            self.btn_ver_reabastecimiento = QPushButton("Ver requerimientos")
            self.layout().insertWidget(self.layout().count() - 1, self.btn_reabastecimiento)
            self.layout().insertWidget(self.layout().count() - 1, self.btn_ver_reabastecimiento)
            self.btn_reabastecimiento.clicked.connect(self._abrir_reabastecimiento)
            self.btn_ver_reabastecimiento.clicked.connect(self._abrir_informe_reabastecimiento)

        columnas = ["ID", "Nombre"]
        if self.tiene_stock:
            columnas.append("Cantidad")
        for campo in self.campos_extra:
            columnas.append(campo["label"])

        self.table = QTableWidget(0, len(columnas))
        self.table.setHorizontalHeaderLabels(columnas)
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
        self.table.itemSelectionChanged.connect(self.cargar_seleccion)
        admin_state.changed.connect(self.aplicar_modo_admin)

        self.limpiar()
        self.aplicar_modo_admin(admin_state.is_admin())

    def aplicar_modo_admin(self, activo):
        self.btn_del.setEnabled(activo)
        self.btn_edit.setEnabled(activo and self.editar_fn is not None)
        if activo:
            self.btn_del.setToolTip("")
            self.btn_edit.setToolTip("" if self.editar_fn else "Esta pagina no tiene funcion de edicion configurada.")
        else:
            self.btn_del.setToolTip("Solo el administrador puede eliminar registros.")
            self.btn_edit.setToolTip("Solo el administrador puede editar registros.")

    def validar_id(self):
        id_val = self.id_input.text().strip()
        if self.fila_seleccionada:
            self.id_status.setText("Registro seleccionado")
            self.btn_add.setEnabled(False)
            return
        if not id_val:
            self.id_status.setText("")
            self.btn_add.setEnabled(False)
            return
        existe = db[self.coleccion].find_one({"_id": id_val}, projection={"_id": 1}) is not None
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

        data = list(db[self.coleccion].find(filtro))
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for doc in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            valores = [doc.get("_id", ""), doc.get("nombre", "")]
            if self.tiene_stock:
                valores.append(doc.get("cantidad", 0))
            for campo in self.campos_extra:
                valores.append(doc.get(campo["name"], ""))
            for c, v in enumerate(valores):
                self.table.setItem(row, c, QTableWidgetItem(str(v)))
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()

    def cargar_seleccion(self):
        row = self.table.currentRow()
        if row < 0:
            return
        self.fila_seleccionada = True
        self.id_input.setReadOnly(True)
        self.id_input.setText(self.table.item(row, 0).text())
        self.nombre.setText(self.table.item(row, 1).text())
        col_offset = 2
        if self.tiene_stock:
            self.cantidad.setText(self.table.item(row, col_offset).text())
            col_offset += 1
        for campo in self.campos_extra:
            widget = self.extra_widgets[campo["name"]]
            value = self.table.item(row, col_offset).text()
            if isinstance(widget, QComboBox):
                idx = widget.findText(value)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
            else:
                widget.setText(value)
            col_offset += 1
        self.validar_id()

    def limpiar(self):
        self.fila_seleccionada = False
        self.id_input.setReadOnly(False)
        self.id_input.clear()
        self.nombre.clear()
        self.cantidad.clear()
        for widget in self.extra_widgets.values():
            if isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)
            else:
                widget.clear()
        self.table.clearSelection()
        self.validar_id()

    def _leer_datos_formulario(self):
        id_val = self.id_input.text().strip()
        nombre = self.nombre.text().strip()
        if not id_val:
            QMessageBox.warning(self, "Campo requerido", "El ID esta vacio.")
            return None
        if not nombre:
            QMessageBox.warning(self, "Campo requerido", "El nombre esta vacio.")
            return None
        cantidad = None
        if self.tiene_stock:
            cantidad = safe_int(self.cantidad.text(), None)
            if cantidad is None or cantidad < 0:
                QMessageBox.warning(self, "Cantidad invalida", "La cantidad debe ser un entero mayor o igual a 0.")
                return None
        extras = {}
        for campo in self.campos_extra:
            widget = self.extra_widgets[campo["name"]]
            if isinstance(widget, QComboBox):
                extras[campo["name"]] = widget.currentText().strip()
            else:
                extras[campo["name"]] = widget.text().strip()
        return id_val, nombre, cantidad, extras

    def agregar(self):
        if self.fila_seleccionada:
            QMessageBox.warning(self, "Registro seleccionado", "Presiona Nuevo / Limpiar para crear otro registro.")
            return
        datos = self._leer_datos_formulario()
        if not datos:
            return
        id_val, nombre, cantidad, extras = datos
        if self.tiene_stock:
            ok, msg = self.agregar_fn(id_val, nombre, cantidad, **extras) if extras else self.agregar_fn(id_val, nombre, cantidad)
        else:
            ok, msg = self.agregar_fn(id_val, nombre, **extras) if extras else self.agregar_fn(id_val, nombre)
        if not ok:
            QMessageBox.critical(self, "Error", msg)
            return
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Registro agregado", "El registro fue agregado correctamente.")

    def editar(self):
        if not admin_state.is_admin():
            QMessageBox.warning(self, "Acceso restringido", "Solo el administrador puede editar registros.")
            return
        if self.editar_fn is None:
            QMessageBox.warning(self, "Edicion no disponible", "Esta pagina no tiene una funcion de edicion configurada.")
            return
        if not self.fila_seleccionada:
            QMessageBox.warning(self, "Selecciona un registro", "Debes seleccionar un registro para editarlo.")
            return
        datos = self._leer_datos_formulario()
        if not datos:
            return
        id_val, nombre, cantidad, extras = datos
        respuesta = QMessageBox.question(
            self, "Confirmar edicion",
            f"¿Deseas guardar los cambios del registro {id_val}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if respuesta != QMessageBox.Yes:
            return
        if self.tiene_stock:
            ok, msg = self.editar_fn(id_val, nombre, cantidad, **extras) if extras else self.editar_fn(id_val, nombre, cantidad)
        else:
            ok, msg = self.editar_fn(id_val, nombre, **extras) if extras else self.editar_fn(id_val, nombre)
        if not ok:
            QMessageBox.critical(self, "Error", msg)
            return
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
        self.eliminar_fn(id_val)
        self.cargar()
        self.limpiar()
        QMessageBox.information(self, "Registro eliminado", "El registro fue eliminado correctamente.")

    def _tipo_inventario(self):
        return {
            "epp": "epp",
            "consumibles": "consumible",
            "pvc": "pvc",
            "herramientas": "herramienta",
            "carros": "carro",
        }.get(self.coleccion)

    def _abrir_reabastecimiento(self):
        if self.btn_reabastecimiento is None:
            return
        tipo = self._tipo_inventario()
        if not tipo:
            QMessageBox.information(self, "No aplica", "Esta pagina no usa requerimientos de reabastecimiento.")
            return
        from ui.pages.requerimiento_reabastecimiento_page import RequerimientoReabastecimientoPage
        self.ventana_req = RequerimientoReabastecimientoPage(tipo)
        self.ventana_req.show()

    def _abrir_informe_reabastecimiento(self):
        if self.btn_ver_reabastecimiento is None:
            return
        tipo = self._tipo_inventario()
        if not tipo:
            QMessageBox.information(self, "No aplica", "Esta pagina no usa requerimientos de reabastecimiento.")
            return
        from ui.pages.informe_reabastecimiento_page import InformeReabastecimientoPage
        self.ventana_inf = InformeReabastecimientoPage(tipo, callback_actualizar=self.cargar)
        self.ventana_inf.show()



