from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem,
)

from logic.logic_mongo import obtener_detalle_epp_trabajador


class TrabajadorEppInformePage(QWidget):
    def __init__(self, trabajador_id):
        super().__init__()
        self.trabajador_id = trabajador_id

        self.setWindowTitle("Informe EPP del trabajador")
        self.resize(750, 450)

        layout = QVBoxLayout(self)

        self.filtro_nombre = QLineEdit()
        self.filtro_nombre.setPlaceholderText("Filtrar por nombre de EPP")
        self.filtro_fecha = QLineEdit()
        self.filtro_fecha.setPlaceholderText("Filtrar por fecha YYYY-MM-DD")
        self.filtro_reposicion = QComboBox()
        self.filtro_reposicion.addItems(["Todos", "Si", "No"])
        self.btn_filtrar = QPushButton("Filtrar")
        self.btn_limpiar = QPushButton("Limpiar filtros")

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Codigo", "EPP", "Fecha de entrega", "Reposicion"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(QLabel("Filtro por nombre"))
        layout.addWidget(self.filtro_nombre)
        layout.addWidget(QLabel("Filtro por fecha"))
        layout.addWidget(self.filtro_fecha)
        layout.addWidget(QLabel("Filtro por reposicion"))
        layout.addWidget(self.filtro_reposicion)
        layout.addWidget(self.btn_filtrar)
        layout.addWidget(self.btn_limpiar)
        layout.addWidget(self.table)

        self.btn_filtrar.clicked.connect(self.cargar)
        self.btn_limpiar.clicked.connect(self.limpiar_filtros)

        self.cargar()

    def limpiar_filtros(self):
        self.filtro_nombre.clear()
        self.filtro_fecha.clear()
        self.filtro_reposicion.setCurrentIndex(0)
        self.cargar()

    def cargar(self):
        data = obtener_detalle_epp_trabajador(self.trabajador_id)
        filtro_nombre = self.filtro_nombre.text().strip().lower()
        filtro_fecha = self.filtro_fecha.text().strip()
        filtro_reposicion = self.filtro_reposicion.currentText()

        filtrado = []
        for item in data:
            nombre = item.get("nombre", "")
            fecha = item.get("fecha_entrega", "")
            reposicion = item.get("reposicion", "No")
            if filtro_nombre and filtro_nombre not in nombre.lower():
                continue
            if filtro_fecha and filtro_fecha != fecha:
                continue
            if filtro_reposicion != "Todos" and reposicion != filtro_reposicion:
                continue
            filtrado.append(item)

        self.table.setRowCount(len(filtrado))
        for row, item in enumerate(filtrado):
            self.table.setItem(row, 0, QTableWidgetItem(item.get("codigo", "")))
            self.table.setItem(row, 1, QTableWidgetItem(item.get("nombre", "")))
            self.table.setItem(row, 2, QTableWidgetItem(item.get("fecha_entrega", "")))
            self.table.setItem(row, 3, QTableWidgetItem(item.get("reposicion", "No")))
        self.table.resizeColumnsToContents()

