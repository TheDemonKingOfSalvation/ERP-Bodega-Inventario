from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QGroupBox,
    QPushButton, QTableWidget, QTableWidgetItem, QSpinBox, QMessageBox, QInputDialog,
)
import os
from ui.admin_state import admin_state, ADMIN_USUARIO
from ui.utils import abrir_archivo, BusquedaConDebounce
from logic.logic_mongo import (
    obtener_requerimientos_reabastecimiento,
    aceptar_requerimiento_reabastecimiento,
    cancelar_requerimiento_reabastecimiento,
    guardar_factura_reabastecimiento,
    obtener_historial_requerimiento,
)


class InformeReabastecimientoPage(QWidget):
    def __init__(self, tipo, callback_actualizar=None, navegar_callback=None):
        super().__init__()

        self.tipo = tipo
        self.callback_actualizar = callback_actualizar
        self.navegar_callback = navegar_callback
        self.requerimientos = []
        self.requerimientos_filtrados = []
        self.requerimiento_actual = None
        self.items_actuales = []

        self.setWindowTitle(f"Requerimientos de reabastecimiento - {tipo.upper()}")
        self.resize(1150, 700)

        layout = QVBoxLayout(self)

        titulo = QLabel(f"Requerimientos - {tipo.upper()} (mostrando pendientes al abrir)")
        layout.addWidget(titulo)

        self.resumen_label = QLabel("")
        layout.addWidget(self.resumen_label)

        filtros_req_layout = QHBoxLayout()
        self.filtro_requisicion = QLineEdit()
        self.filtro_requisicion.setPlaceholderText("Buscar requisicion por ID, fecha, estado o PDF")
        self.filtro_estado = QComboBox()
        self.filtro_estado.addItems(["Todos", "pendiente", "aceptado", "cancelado"])
        self.filtro_estado.setCurrentIndex(1)

        filtros_req_layout.addWidget(QLabel("Filtro requisicion"))
        filtros_req_layout.addWidget(self.filtro_requisicion)
        filtros_req_layout.addWidget(QLabel("Estado"))
        filtros_req_layout.addWidget(self.filtro_estado)
        layout.addLayout(filtros_req_layout)

        self.table_requerimientos = QTableWidget(0, 8)
        self.table_requerimientos.setHorizontalHeaderLabels([
            "ID", "Fecha", "Tipo", "Estado", "Proveedor",
            "Precio", "N. de factura", "PDF",
        ])
        self.table_requerimientos.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_requerimientos.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_requerimientos.setAlternatingRowColors(True)
        layout.addWidget(self.table_requerimientos)

        layout.addWidget(QLabel("Detalle de la requisicion"))

        filtros_items_layout = QHBoxLayout()
        self.filtro_item = QLineEdit()
        self.filtro_item.setPlaceholderText("Buscar item por codigo o nombre")
        filtros_items_layout.addWidget(QLabel("Filtro items"))
        filtros_items_layout.addWidget(self.filtro_item)
        layout.addLayout(filtros_items_layout)

        self.table_items = QTableWidget(0, 5)
        self.table_items.setHorizontalHeaderLabels([
            "Codigo", "Nombre", "Disponibles", "Cantidad solicitada", "Cantidad aceptada",
        ])
        self.table_items.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_items.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_items.setAlternatingRowColors(True)
        layout.addWidget(self.table_items)

        botones_layout = QHBoxLayout()
        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_limpiar_filtros = QPushButton("Limpiar filtros")
        self.btn_abrir_pdf = QPushButton("Abrir PDF")
        self.btn_historial = QPushButton("Ver historial")
        self.btn_factura = QPushButton("Guardar N. de factura")
        self.btn_aceptar = QPushButton("Aceptar requisicion")
        self.btn_cancelar = QPushButton("Cancelar requisicion")
        for b in (self.btn_actualizar, self.btn_limpiar_filtros, self.btn_abrir_pdf,
                  self.btn_historial, self.btn_factura, self.btn_aceptar, self.btn_cancelar):
            botones_layout.addWidget(b)
        layout.addLayout(botones_layout)

        self.historial_group = QGroupBox("Historial de la requisicion")
        historial_layout = QVBoxLayout(self.historial_group)
        self.table_historial = QTableWidget(0, 4)
        self.table_historial.setHorizontalHeaderLabels(["Fecha", "Accion", "Usuario", "Detalle"])
        self.table_historial.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_historial.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_historial.setAlternatingRowColors(True)
        historial_layout.addWidget(self.table_historial)
        self.historial_group.setVisible(False)
        layout.addWidget(self.historial_group)

        self.btn_actualizar.clicked.connect(self.cargar_datos)
        self.btn_limpiar_filtros.clicked.connect(self.limpiar_filtros)
        self.btn_abrir_pdf.clicked.connect(self.abrir_pdf_seleccionado)
        self.btn_historial.clicked.connect(self.mostrar_historial)
        self.btn_factura.clicked.connect(self.guardar_factura)
        self.btn_aceptar.clicked.connect(self.aceptar_requerimiento)
        self.btn_cancelar.clicked.connect(self.cancelar_requerimiento)
        admin_state.changed.connect(self.aplicar_modo_admin)

        self.busqueda_req = BusquedaConDebounce(self.filtro_requisicion, self.aplicar_filtros_requisiciones)
        self.filtro_estado.currentTextChanged.connect(self.aplicar_filtros_requisiciones)
        self.busqueda_item = BusquedaConDebounce(self.filtro_item, self.llenar_tabla_items_filtrada)
        self.table_requerimientos.itemSelectionChanged.connect(self.cargar_items_requerimiento)

        self.cargar_datos()

    def aplicar_modo_admin(self, _=None):
        es_admin = admin_state.is_admin()
        self.btn_aceptar.setEnabled(es_admin)
        self.btn_cancelar.setEnabled(es_admin)
        if es_admin:
            self.btn_aceptar.setToolTip("")
            self.btn_cancelar.setToolTip("")
        else:
            self.btn_aceptar.setToolTip("Solo el administrador puede aceptar requisiciones.")
            self.btn_cancelar.setToolTip("Solo el administrador puede cancelar requisiciones.")
        self.actualizar_botones()

    def limpiar_filtros(self):
        self.filtro_requisicion.clear()
        self.filtro_estado.setCurrentIndex(1)
        self.filtro_item.clear()
        self.aplicar_filtros_requisiciones()

    def cargar_datos(self):
        self.requerimiento_actual = None
        self.items_actuales = []
        self.table_items.setRowCount(0)
        self.requerimientos = obtener_requerimientos_reabastecimiento(self.tipo)
        self.aplicar_filtros_requisiciones()

    def cumple_filtro_requisicion(self, req):
        texto = self.filtro_requisicion.text().strip().lower()
        estado_filtro = self.filtro_estado.currentText().strip().lower()
        estado = str(req.get("estado", "pendiente")).strip().lower()
        if estado_filtro != "todos" and estado != estado_filtro:
            return False
        if not texto:
            return True
        campos = [
            req.get("_id", ""), req.get("fecha", ""), req.get("tipo", ""), req.get("estado", ""),
            (req.get("proveedor", {}) or {}).get("nombre", ""),
            (req.get("proveedor", {}) or {}).get("telefono", ""),
            req.get("precio", ""), req.get("numero_factura", ""), req.get("pdf_path", ""),
        ]
        return texto in " ".join(str(c).lower() for c in campos)

    def aplicar_filtros_requisiciones(self):
        self.requerimientos_filtrados = [r for r in self.requerimientos if self.cumple_filtro_requisicion(r)]
        self.llenar_tabla_requerimientos()

    def llenar_tabla_requerimientos(self):
        self.table_requerimientos.setRowCount(0)
        self.requerimiento_actual = None
        self.items_actuales = []
        self.table_items.setRowCount(0)

        for req in self.requerimientos_filtrados:
            row = self.table_requerimientos.rowCount()
            self.table_requerimientos.insertRow(row)
            estado = str(req.get("estado", "pendiente"))
            proveedor = req.get("proveedor", {}) or {}
            valores = [
                str(req.get("_id", "")),
                str(req.get("fecha", "")),
                str(req.get("tipo", "")),
                estado,
                str(proveedor.get("nombre", "")),
                str(req.get("precio", "")),
                str(req.get("numero_factura", "")),
                str(req.get("pdf_path", "")),
            ]
            for c, v in enumerate(valores):
                self.table_requerimientos.setItem(row, c, QTableWidgetItem(v))

        self.resumen_label.setText(
            f"Requisiciones: {len(self.requerimientos)} | Mostrando: {len(self.requerimientos_filtrados)}"
        )
        self.table_requerimientos.resizeColumnsToContents()
        self.actualizar_botones()

    def actualizar_botones(self):
        hay = self.table_requerimientos.currentRow() >= 0
        self.btn_abrir_pdf.setEnabled(hay)
        self.btn_historial.setEnabled(hay)
        req = self.obtener_requerimiento_seleccionado() if hay else None
        factura_bloqueada = bool(req and (req.get("factura_editada") or str(req.get("numero_factura", "")).strip()))
        self.btn_factura.setEnabled(hay and not factura_bloqueada)
        self.btn_aceptar.setEnabled(hay and admin_state.is_admin() and req.get("estado") == "pendiente" if req else False)
        self.btn_cancelar.setEnabled(hay and admin_state.is_admin() and req.get("estado") == "pendiente" if req else False)

    def obtener_requerimiento_seleccionado(self):
        fila = self.table_requerimientos.currentRow()
        if fila < 0:
            return None
        item = self.table_requerimientos.item(fila, 0)
        if item is None:
            return None
        requerimiento_id = item.text()
        for req in self.requerimientos_filtrados:
            if str(req.get("_id", "")) == requerimiento_id:
                return req
        return None

    def abrir_pdf_seleccionado(self):
        req = self.obtener_requerimiento_seleccionado()
        if not req:
            QMessageBox.warning(self, "Selecciona una requisicion", "Debes seleccionar una requisicion para abrir su PDF.")
            return
        abrir_archivo(req.get("pdf_path", ""), self)

    def guardar_factura(self):
        req = self.obtener_requerimiento_seleccionado()
        if not req:
            QMessageBox.warning(self, "Selecciona una requisicion", "Debes seleccionar una requisicion para registrar su factura.")
            return
        if req.get("factura_editada") or str(req.get("numero_factura", "")).strip():
            QMessageBox.warning(self, "Factura bloqueada", "El numero de factura ya fue registrado y no puede editarse otra vez.")
            return
        numero, ok = QInputDialog.getText(self, "N. de factura", "Ingresa el numero de factura:")
        if not ok:
            return
        ok_guardado, mensaje = guardar_factura_reabastecimiento(str(req.get("_id", "")), numero)
        if ok_guardado:
            QMessageBox.information(self, "Factura guardada", mensaje)
            self.cargar_datos()
        else:
            QMessageBox.warning(self, "No se pudo guardar", mensaje)

    def cargar_items_requerimiento(self):
        self.requerimiento_actual = self.obtener_requerimiento_seleccionado()
        self.table_items.setRowCount(0)
        self.items_actuales = []
        if not self.requerimiento_actual:
            self.actualizar_botones()
            return
        self.items_actuales = self.requerimiento_actual.get("items", [])
        self.llenar_tabla_items_filtrada()
        self.actualizar_botones()

    def cumple_filtro_item(self, item):
        texto = self.filtro_item.text().strip().lower()
        if not texto:
            return True
        return texto in str(item.get("codigo", "")).lower() or texto in str(item.get("nombre", "")).lower()

    def llenar_tabla_items_filtrada(self):
        self.table_items.setRowCount(0)
        for item in self.items_actuales:
            if not self.cumple_filtro_item(item):
                continue
            row = self.table_items.rowCount()
            self.table_items.insertRow(row)
            codigo = str(item.get("codigo", ""))
            nombre = str(item.get("nombre", ""))
            disponibles = int(item.get("disponibles", 0))
            cantidad_solicitada = int(item.get("cantidad_solicitada", 0))
            spinbox = QSpinBox()
            spinbox.setMinimum(0)
            spinbox.setMaximum(999999)
            spinbox.setValue(cantidad_solicitada)
            self.table_items.setItem(row, 0, QTableWidgetItem(codigo))
            self.table_items.setItem(row, 1, QTableWidgetItem(nombre))
            self.table_items.setItem(row, 2, QTableWidgetItem(str(disponibles)))
            self.table_items.setItem(row, 3, QTableWidgetItem(str(cantidad_solicitada)))
            self.table_items.setCellWidget(row, 4, spinbox)
        self.table_items.resizeColumnsToContents()

    def obtener_items_ajustados(self):
        items = []
        for row in range(self.table_items.rowCount()):
            codigo = self.table_items.item(row, 0)
            nombre = self.table_items.item(row, 1)
            disponibles = self.table_items.item(row, 2)
            solicitada = self.table_items.item(row, 3)
            spinbox = self.table_items.cellWidget(row, 4)
            if None in (codigo, nombre, disponibles, solicitada, spinbox):
                continue
            items.append({
                "codigo": codigo.text(),
                "nombre": nombre.text(),
                "disponibles": int(disponibles.text()),
                "cantidad_solicitada": int(solicitada.text()),
                "cantidad_aceptada": spinbox.value(),
            })
        return items

    def mostrar_historial(self):
        req = self.obtener_requerimiento_seleccionado()
        if not req:
            QMessageBox.warning(self, "Selecciona una requisicion", "Debes seleccionar una requisicion.")
            return
        eventos = obtener_historial_requerimiento(str(req.get("_id", "")))
        self.table_historial.setRowCount(0)
        for evento in eventos:
            row = self.table_historial.rowCount()
            self.table_historial.insertRow(row)
            self.table_historial.setItem(row, 0, QTableWidgetItem(str(evento.get("fecha_texto", ""))))
            self.table_historial.setItem(row, 1, QTableWidgetItem(str(evento.get("accion", ""))))
            self.table_historial.setItem(row, 2, QTableWidgetItem(str(evento.get("usuario", ""))))
            self.table_historial.setItem(row, 3, QTableWidgetItem(str(evento.get("detalle", ""))))
        self.table_historial.resizeColumnsToContents()
        self.historial_group.setVisible(True)

    def aceptar_requerimiento(self):
        if not admin_state.is_admin():
            QMessageBox.warning(self, "Acceso restringido", "Solo el administrador puede aceptar requisiciones.")
            return
        if not self.requerimiento_actual:
            self.cargar_items_requerimiento()
        if not self.requerimiento_actual:
            QMessageBox.warning(self, "Selecciona una requisicion", "Debes seleccionar una requisicion para aceptarla.")
            return

        requerimiento_id = str(self.requerimiento_actual.get("_id", ""))
        estado = str(self.requerimiento_actual.get("estado", "")).strip().lower()
        tipo = str(self.requerimiento_actual.get("tipo", self.tipo)).upper()
        fecha = str(self.requerimiento_actual.get("fecha", ""))

        if estado == "aceptado":
            QMessageBox.information(self, "Ya aceptado", "Este requerimiento ya fue aceptado.")
            return
        if estado == "cancelado":
            QMessageBox.warning(self, "Requisicion cancelada", "No se puede aceptar una requisicion cancelada.")
            return

        items_ajustados = self.obtener_items_ajustados()
        total_aceptado = sum(int(item.get("cantidad_aceptada", 0)) for item in items_ajustados)
        if total_aceptado <= 0:
            QMessageBox.warning(self, "Cantidad invalida", "Debes aceptar al menos una cantidad mayor a 0.")
            return

        respuesta = QMessageBox.question(
            self, "Aceptar requisicion",
            f"¿Deseas aceptar la requisicion de {tipo} del {fecha}?\n\n"
            f"Se sumara un total de {total_aceptado} unidad(es) al inventario.\n"
            "El PDF original no sera modificado.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if respuesta != QMessageBox.Yes:
            return

        self.btn_aceptar.setEnabled(False)
        self.btn_cancelar.setEnabled(False)
        try:
            usuario_actual = ADMIN_USUARIO if admin_state.is_admin() else ""
            ok, mensaje = aceptar_requerimiento_reabastecimiento(requerimiento_id, items_ajustados, usuario_actual)
            if ok:
                QMessageBox.information(self, "Requisicion aceptada", mensaje)
                self.cargar_datos()
                if self.callback_actualizar:
                    self.callback_actualizar()
            else:
                QMessageBox.warning(self, "No se pudo aceptar", mensaje)
        finally:
            self.actualizar_botones()

    def cancelar_requerimiento(self):
        if not admin_state.is_admin():
            QMessageBox.warning(self, "Acceso restringido", "Solo el administrador puede cancelar requisiciones.")
            return
        if not self.requerimiento_actual:
            self.cargar_items_requerimiento()
        if not self.requerimiento_actual:
            QMessageBox.warning(self, "Selecciona una requisicion", "Debes seleccionar una requisicion para cancelarla.")
            return

        requerimiento_id = str(self.requerimiento_actual.get("_id", ""))
        estado = str(self.requerimiento_actual.get("estado", "")).strip().lower()
        tipo = str(self.requerimiento_actual.get("tipo", self.tipo)).upper()
        fecha = str(self.requerimiento_actual.get("fecha", ""))

        if estado == "aceptado":
            QMessageBox.warning(self, "Requisicion aceptada", "No se puede cancelar una requisicion que ya fue aceptada.")
            return
        if estado == "cancelado":
            QMessageBox.information(self, "Requisicion cancelada", "Esta requisicion ya fue cancelada.")
            return

        respuesta = QMessageBox.question(
            self, "Cancelar requisicion",
            f"¿Deseas cancelar la requisicion de {tipo} del {fecha}?\n\n"
            "El registro no sera eliminado, el PDF se conservara y el inventario no sera modificado.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if respuesta != QMessageBox.Yes:
            return

        self.btn_cancelar.setEnabled(False)
        self.btn_aceptar.setEnabled(False)
        try:
            usuario_actual = ADMIN_USUARIO if admin_state.is_admin() else ""
            ok, mensaje = cancelar_requerimiento_reabastecimiento(requerimiento_id, usuario_actual)
            if ok:
                QMessageBox.information(self, "Requisicion cancelada", mensaje)
                self.cargar_datos()
                if self.callback_actualizar:
                    self.callback_actualizar()
            else:
                QMessageBox.warning(self, "No se pudo cancelar", mensaje)
        finally:
            self.actualizar_botones()


