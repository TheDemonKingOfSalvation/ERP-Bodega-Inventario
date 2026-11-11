from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem,
)

from config.db_mongo import db
from ui.utils import BusquedaConDebounce
from logic.logic_mongo import (
    agregar_proveedor, editar_proveedor, eliminar_proveedor,
)
from ui.pages.inventario_base import InventarioBasePage


class HistorialProveedoresPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Historial de requerimientos por proveedor")
        self.resize(1100, 650)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Historial de requerimientos"))

        filtros_layout = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar por proveedor, requisicion, tipo, factura o estado")
        self.estado = QComboBox()
        self.estado.addItems(["Todos", "pendiente", "aceptado", "cancelado"])
        self.btn_actualizar = QPushButton("Actualizar")

        filtros_layout.addWidget(QLabel("Buscar"))
        filtros_layout.addWidget(self.search)
        filtros_layout.addWidget(QLabel("Estado"))
        filtros_layout.addWidget(self.estado)
        filtros_layout.addWidget(self.btn_actualizar)
        layout.addLayout(filtros_layout)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Fecha", "Tipo", "Estado", "Proveedor",
            "Telefono", "Precio", "N. de factura", "PDF",
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        self.busqueda = BusquedaConDebounce(self.search, self.cargar)
        self.estado.currentTextChanged.connect(self.cargar)
        self.btn_actualizar.clicked.connect(self.cargar)

    def cargar(self):
        texto = self.search.text().strip().lower()
        estado_filtro = self.estado.currentText().strip().lower()

        requerimientos = list(
            db.requerimientos_reabastecimiento
              .find({}, projection={"fecha": 1, "tipo": 1, "estado": 1, "proveedor": 1, "precio": 1, "numero_factura": 1, "pdf_path": 1})
              .sort("fecha", -1)
        )

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for req in requerimientos:
            proveedor = req.get("proveedor", {}) or {}
            estado = str(req.get("estado", "pendiente"))

            valores = [
                str(req.get("_id", "")),
                str(req.get("fecha", "")),
                str(req.get("tipo", "")),
                estado,
                str(proveedor.get("nombre", "")),
                str(proveedor.get("telefono", "")),
                str(req.get("precio", "")),
                str(req.get("numero_factura", "")),
                str(req.get("pdf_path", "")),
            ]

            if estado_filtro != "todos" and estado.lower() != estado_filtro:
                continue
            if texto and texto not in " ".join(v.lower() for v in valores):
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, valor in enumerate(valores):
                self.table.setItem(row, col, QTableWidgetItem(valor))

        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()


class ProveedorPage(InventarioBasePage):
    def __init__(self, navegar_callback=None):
        super().__init__(
            "Proveedores",
            "proveedores",
            agregar_proveedor,
            editar_proveedor,
            eliminar_proveedor,
            campos_extra=[{"name": "telefono", "label": "Telefono"}],
            tiene_stock=False,
            navegar_callback=navegar_callback,
        )

        self.btn_historial = QPushButton("Historial de requerimientos")
        self.layout().insertWidget(self.layout().count() - 1, self.btn_historial)
        self.btn_historial.clicked.connect(self.abrir_historial)

    def abrir_historial(self):
        self.ventana_historial = HistorialProveedoresPage()
        self.ventana_historial.show()


