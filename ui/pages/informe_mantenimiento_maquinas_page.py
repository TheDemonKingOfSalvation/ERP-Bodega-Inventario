from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
)
from PySide6.QtCore import Qt

from ui.utils import abrir_archivo, BusquedaConDebounce
from logic.logic_mongo import (
    obtener_requerimientos_maquinas, terminar_mantenimiento_maquina,
)


class InformeMantenimientoMaquinasPage(QWidget):
    def __init__(self, callback_actualizar=None, navegar_callback=None):
        super().__init__()

        self.callback_actualizar = callback_actualizar
        self.navegar_callback = navegar_callback
        self.requerimientos = []
        self.requerimientos_filtrados = []

        self.setWindowTitle("Informe de mantenimiento de maquinas")
        self.resize(1100, 540)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Informe de mantenimiento de maquinas"))

        self.resumen_label = QLabel("")
        layout.addWidget(self.resumen_label)

        filtros_layout = QHBoxLayout()
        self.filtro_texto = QLineEdit()
        self.filtro_texto.setPlaceholderText("Buscar por codigo, nombre, razon, fecha o PDF")
        self.filtro_estado = QComboBox()
        self.filtro_estado.addItems(["Todos", "en mantenimiento", "terminado"])
        filtros_layout.addWidget(QLabel("Filtro"))
        filtros_layout.addWidget(self.filtro_texto)
        filtros_layout.addWidget(QLabel("Estado"))
        filtros_layout.addWidget(self.filtro_estado)
        layout.addLayout(filtros_layout)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Codigo", "Nombre", "Fecha", "Razon",
            "Estado", "Fecha terminado", "PDF",
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        botones_layout = QHBoxLayout()
        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_limpiar_filtros = QPushButton("Limpiar filtros")
        self.btn_abrir_pdf = QPushButton("Abrir PDF")
        self.btn_terminar = QPushButton("Termino mantenimiento")
        for b in (self.btn_actualizar, self.btn_limpiar_filtros, self.btn_abrir_pdf, self.btn_terminar):
            botones_layout.addWidget(b)
        layout.addLayout(botones_layout)

        self.btn_actualizar.clicked.connect(self.cargar_datos)
        self.btn_limpiar_filtros.clicked.connect(self.limpiar_filtros)
        self.btn_abrir_pdf.clicked.connect(self.abrir_pdf_seleccionado)
        self.btn_terminar.clicked.connect(self.terminar_mantenimiento)
        self.table.itemSelectionChanged.connect(self.actualizar_botones)
        self.filtro_texto.textChanged.connect(self.aplicar_filtros)
        self.filtro_estado.currentTextChanged.connect(self.aplicar_filtros)

        self.cargar_datos()

    def limpiar_filtros(self):
        self.filtro_texto.clear()
        self.filtro_estado.setCurrentIndex(0)
        self.aplicar_filtros()

    def cargar_datos(self):
        self.requerimientos = obtener_requerimientos_maquinas()
        self.aplicar_filtros()

    def cumple_filtro(self, req):
        texto = self.filtro_texto.text().strip().lower()
        estado_filtro = self.filtro_estado.currentText().strip().lower()
        estado = str(req.get("estado", "")).strip().lower()
        if estado_filtro != "todos" and estado != estado_filtro:
            return False
        if not texto:
            return True
        campos = [
            req.get("codigo", ""), req.get("nombre", ""), req.get("fecha", ""),
            req.get("razon", ""), req.get("estado", ""),
            req.get("fecha_terminado", ""), req.get("pdf_path", ""),
        ]
        return texto in " ".join(str(c).lower() for c in campos)

    def aplicar_filtros(self):
        self.requerimientos_filtrados = [r for r in self.requerimientos if self.cumple_filtro(r)]
        self.llenar_tabla()

    def llenar_tabla(self):
        self.table.setRowCount(0)
        pendientes = sum(1 for r in self.requerimientos if str(r.get("estado", "")) != "terminado")
        terminados = len(self.requerimientos) - pendientes

        for req in self.requerimientos_filtrados:
            row = self.table.rowCount()
            self.table.insertRow(row)
            estado = str(req.get("estado", ""))
            item_codigo = QTableWidgetItem(str(req.get("codigo", "")))
            item_codigo.setData(Qt.UserRole, str(req.get("_id", "")))
            self.table.setItem(row, 0, item_codigo)
            self.table.setItem(row, 1, QTableWidgetItem(str(req.get("nombre", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(req.get("fecha", ""))))
            self.table.setItem(row, 3, QTableWidgetItem(str(req.get("razon", ""))))
            self.table.setItem(row, 4, QTableWidgetItem(estado))
            self.table.setItem(row, 5, QTableWidgetItem(str(req.get("fecha_terminado", ""))))
            self.table.setItem(row, 6, QTableWidgetItem(str(req.get("pdf_path", ""))))

        self.resumen_label.setText(
            f"Pendientes: {pendientes} | Terminados: {terminados} | "
            f"Mostrando: {len(self.requerimientos_filtrados)} de {len(self.requerimientos)}"
        )
        self.table.resizeColumnsToContents()
        self.actualizar_botones()

    def actualizar_botones(self):
        fila = self.table.currentRow()
        hay = fila >= 0
        self.btn_abrir_pdf.setEnabled(hay)
        if not hay:
            self.btn_terminar.setEnabled(False)
            return
        item_estado = self.table.item(fila, 4)
        estado = item_estado.text().strip().lower() if item_estado else ""
        self.btn_terminar.setEnabled(estado != "terminado")

    def abrir_pdf_seleccionado(self):
        fila = self.table.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Selecciona un mantenimiento", "Debes seleccionar un mantenimiento para abrir su PDF.")
            return
        item_pdf = self.table.item(fila, 6)
        ruta_pdf = item_pdf.text() if item_pdf else ""
        abrir_archivo(ruta_pdf, self)

    def obtener_id_requerimiento_fila(self, fila):
        item_codigo = self.table.item(fila, 0)
        if not item_codigo:
            return ""
        return str(item_codigo.data(Qt.UserRole) or "")

    def terminar_mantenimiento(self):
        fila = self.table.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Selecciona un mantenimiento", "Debes seleccionar un mantenimiento.")
            return
        requerimiento_id = self.obtener_id_requerimiento_fila(fila)
        codigo = self.table.item(fila, 0).text()
        nombre = self.table.item(fila, 1).text()
        estado = self.table.item(fila, 4).text().strip().lower()

        if not requerimiento_id:
            QMessageBox.warning(self, "Error", "No se pudo leer el identificador interno del mantenimiento seleccionado.")
            return
        if estado == "terminado":
            QMessageBox.information(self, "Ya terminado", "Este mantenimiento ya fue marcado como terminado.")
            self.actualizar_botones()
            return

        respuesta = QMessageBox.question(
            self, "Terminar mantenimiento",
            f"¿Confirmas que termino el mantenimiento de esta maquina?\n\n"
            f"Codigo: {codigo}\nNombre: {nombre}\n\n"
            "La maquina volvera a estar disponible.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if respuesta != QMessageBox.Yes:
            return

        self.btn_terminar.setEnabled(False)
        try:
            ok, mensaje = terminar_mantenimiento_maquina(requerimiento_id)
            if ok:
                QMessageBox.information(self, "Mantenimiento terminado", mensaje)
                self.cargar_datos()
                if self.callback_actualizar:
                    self.callback_actualizar()
            else:
                QMessageBox.warning(self, "No se pudo terminar", mensaje)
        finally:
            self.actualizar_botones()



