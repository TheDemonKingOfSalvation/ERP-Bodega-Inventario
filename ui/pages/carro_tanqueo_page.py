from PySide6.QtWidgets import *
from PySide6.QtGui import QDoubleValidator
from config.db_mongo import db
from datetime import datetime
import calendar

class CarroTanqueoPage(QWidget):
    def __init__(self, carro_id):
        super().__init__()
        self.carro_id = carro_id
        self.setWindowTitle(f"Tanqueo - {carro_id}")
        self.resize(1100, 800)
        self.setMinimumSize(1000, 700)

        layout = QVBoxLayout(self)

        header = QLabel(f"Registro de tanqueo (combustible) - Carro: {carro_id}")
        layout.addWidget(header)

        controls = QHBoxLayout()
        self.month_combo = QComboBox()
        meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
        self.month_combo.addItems(meses)
        self.year_label = QLabel(str(datetime.now().year))
        self.year = datetime.now().year
        controls.addWidget(QLabel("Mes"))
        controls.addWidget(self.month_combo)
        controls.addWidget(QLabel("Año"))
        controls.addWidget(self.year_label)
        controls.addStretch()

        layout.addLayout(controls)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Día", "Litros tanqueados"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setMinimumWidth(1000)
        layout.addWidget(self.table)

        botones = QHBoxLayout()
        self.btn_calcular = QPushButton("Calcular totales")
        self.btn_guardar = QPushButton("Guardar")
        botones.addWidget(self.btn_calcular)
        botones.addWidget(self.btn_guardar)
        botones.addStretch()
        layout.addLayout(botones)

        self.totales_label = QLabel("")
        layout.addWidget(self.totales_label)

        # mapping day -> widget
        self.day_widgets = {}

        self.month_combo.currentIndexChanged.connect(self.cargar_dias)
        self.btn_guardar.clicked.connect(self.guardar)
        self.btn_calcular.clicked.connect(self.calcular_totales)

        # set default month to current
        self.month_combo.setCurrentIndex(datetime.now().month - 1)
        self.cargar_dias()

    def cargar_dias(self):
        month_index = self.month_combo.currentIndex() + 1
        year = self.year
        _, dias = calendar.monthrange(year, month_index)

        self.table.setRowCount(0)
        self.day_widgets = {}

        # Try to load existing data
        doc = db.carros_tanqueo.find_one({"carro_id": self.carro_id, "year": year, "month": month_index})
        days_data = doc.get("days", {}) if doc else {}

        hoy = datetime.now()
        es_mes_actual = (year == hoy.year and month_index == hoy.month)

        for d in range(1, dias + 1):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(d)))

            le = QLineEdit()
            le.setValidator(QDoubleValidator(0, 1000, 2))
            le.setText(str(days_data.get(str(d), 0)))

            editable = (es_mes_actual and d <= hoy.day)
            if not editable:
                le.setReadOnly(True)
                le.setStyleSheet("background-color: #2A2F32; color: #7D858B;")
            else:
                le.setStyleSheet("background-color: #202426;")

            self.table.setCellWidget(row, 1, le)
            self.day_widgets[d] = le

        # Ajustar tamaño de columnas
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        self.table.resizeColumnsToContents()
        self.totales_label.setText("")

    def guardar(self):
        month_index = self.month_combo.currentIndex() + 1
        year = self.year
        hoy = datetime.now()
        es_mes_actual = (year == hoy.year and month_index == hoy.month)

        if not es_mes_actual:
            QMessageBox.warning(self, "Mes inválido", "Solo puedes guardar tanqueo del mes actual.")
            return

        days = {}
        for d, le in self.day_widgets.items():
            if d > hoy.day:
                continue
            texto = le.text().strip()
            if not texto:
                continue
            try:
                valor = float(texto)
            except ValueError:
                continue
            days[str(d)] = valor

        db.carros_tanqueo.update_one(
            {"carro_id": self.carro_id, "year": year, "month": month_index},
            {"$set": {"days": days}},
            upsert=True
        )

        QMessageBox.information(self, "Guardado", "Tanqueo guardado correctamente.")

    def calcular_totales(self):
        # simple weekly grouping: 1-7,8-14,15-21,22-28,29-end
        dias = sorted(self.day_widgets.keys())
        values = [float(self.day_widgets[d].text() or 0) for d in dias]

        semanas = []
        i = 0
        while i < len(dias):
            semana_vals = values[i:i+7]
            semanas.append(sum(semana_vals))
            i += 7

        total_mes = sum(values)
        
        # Calcular promedios
        promedio_semana = total_mes / len(semanas) if semanas else 0
        promedio_dia = total_mes / len(values) if values else 0

        text = []
        for idx, val in enumerate(semanas, start=1):
            text.append(f"Semana {idx}: {val:.2f} L")
        text.append(f"Total mes: {total_mes:.2f} L")
        text.append(f"Promedio por semana: {promedio_semana:.2f} L")
        text.append(f"Promedio diario: {promedio_dia:.2f} L")

        self.totales_label.setText(" | ".join(text))
