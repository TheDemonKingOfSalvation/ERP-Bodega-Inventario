from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QInputDialog, QDialog,
    QFrame,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QIntValidator
from config.db_mongo import db
from datetime import datetime, timedelta
import calendar

from logic.logic_mongo import (
    registrar_cambio_aceite, aceptar_cambio_aceite, obtener_historial_aceite, obtener_ultimo_cambio_aceite,
    _obtener_km_actual_carro,
)
from ui.admin_state import admin_state
from ui.utils import abrir_archivo


class _BannerCambioAceite(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bannerCambioAceite")
        self.setStyleSheet(
            "#bannerCambioAceite { background-color: #C74B4B; border-radius: 10px; padding: 12px; }"
            "#bannerCambioAceite QLabel { color: white; font-weight: 700; }"
        )
        layout = QVBoxLayout(self)
        self.titulo = QLabel("Es necesario generar el cambio de aceite")
        self.titulo.setStyleSheet("font-size: 14px;")
        self.detalle = QLabel("")
        self.detalle.setStyleSheet("font-weight: 400; font-size: 12px;")
        self.detalle.setWordWrap(True)
        layout.addWidget(self.titulo)
        layout.addWidget(self.detalle)
        self.setVisible(False)

    def actualizar(self, km_actual, km_ultimo, intervalo):
        if not intervalo or intervalo <= 0:
            self.setVisible(False)
            return
        recorrido = max((km_actual or 0) - (km_ultimo or 0), 0)
        if recorrido >= intervalo:
            restante_para_cumplir = recorrido - intervalo + 1
            self.detalle.setText(
                "El carro ya recorrio " + str(recorrido) + " km desde el ultimo cambio "
                "(km " + str(km_ultimo or 0) + " -> km " + str(km_actual or 0) + "). "
                "Intervalo: " + str(intervalo) + " km. "
                "Registra el cambio para aprobar y notificar a la alerta."
            )
            self.setVisible(True)
        else:
            self.setVisible(False)


class CarroKilometrajePage(QWidget):
    def __init__(self, carro_id):
        super().__init__()
        self.carro_id = str(carro_id)
        self.setWindowTitle("Kilometraje - " + self.carro_id)
        self.resize(1100, 900)
        self.setMinimumSize(1000, 800)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Registro de kilometraje - Carro: " + self.carro_id))

        self.banner_aceite = _BannerCambioAceite(self)
        layout.addWidget(self.banner_aceite)

        info_layout = QHBoxLayout()
        self.lbl_km_actual = QLabel("Kilometraje actual: -")
        self.lbl_km_actual.setStyleSheet("font-weight: 700;")
        self.lbl_km_ultimo_aceite = QLabel("Ultimo cambio de aceite: -")
        self.lbl_intervalo = QLabel("Intervalo: -")
        info_layout.addWidget(self.lbl_km_actual)
        info_layout.addSpacing(20)
        info_layout.addWidget(self.lbl_km_ultimo_aceite)
        info_layout.addSpacing(20)
        info_layout.addWidget(self.lbl_intervalo)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        controls = QHBoxLayout()
        self.month_combo = QComboBox()
        meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
        self.month_combo.addItems(meses)
        self.year_label = QLabel(str(datetime.now().year))
        self.year = datetime.now().year
        controls.addWidget(QLabel("Mes"))
        controls.addWidget(self.month_combo)
        controls.addWidget(QLabel("Anio"))
        controls.addWidget(self.year_label)
        self.btn_hoy = QPushButton("Ir al dia de hoy")
        controls.addWidget(self.btn_hoy)
        controls.addStretch()
        layout.addLayout(controls)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Dia", "Kilometraje"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setMinimumWidth(1000)
        layout.addWidget(self.table)

        botones = QHBoxLayout()
        self.btn_calcular = QPushButton("Calcular totales")
        self.btn_guardar = QPushButton("Guardar kilometraje")
        self.btn_cambio_aceite = QPushButton("Registrar cambio de aceite")
        self.btn_historial_aceite = QPushButton("Historial de aceite")
        botones.addWidget(self.btn_calcular)
        botones.addWidget(self.btn_guardar)
        botones.addWidget(self.btn_cambio_aceite)
        botones.addWidget(self.btn_historial_aceite)
        botones.addStretch()
        layout.addLayout(botones)

        self.totales_label = QLabel("")
        layout.addWidget(self.totales_label)

        self._carro = db.carros.find_one({"_id": self.carro_id}) or {}
        self._intervalo = int(self._carro.get("km_cambio_intervalo", 0) or 0)

        self.day_widgets = {}
        self._dia_hoy = datetime.now().day

        self.month_combo.currentIndexChanged.connect(self.cargar_dias)
        self.btn_guardar.clicked.connect(self.guardar)
        self.btn_calcular.clicked.connect(self.calcular_totales)
        self.btn_cambio_aceite.clicked.connect(self.registrar_cambio_aceite)
        self.btn_historial_aceite.clicked.connect(self.ver_historial_aceite)
        self.btn_hoy.clicked.connect(self._ir_a_hoy)
        admin_state.changed.connect(self._actualizar_estado_admin)

        self.month_combo.setCurrentIndex(datetime.now().month - 1)
        self.cargar_dias()

    def _ir_a_hoy(self):
        self.year = datetime.now().year
        self.year_label.setText(str(self.year))
        self.month_combo.setCurrentIndex(datetime.now().month - 1)

    def _actualizar_estado_admin(self, activo):
        return

    def cargar_dias(self):
        month_index = self.month_combo.currentIndex() + 1
        year = self.year
        _, dias_del_mes = calendar.monthrange(year, month_index)

        doc = db.carros_kilometraje.find_one({"carro_id": self.carro_id, "year": year, "month": month_index})
        days_data = doc.get("days", {}) if doc else {}

        hoy = datetime.now()
        es_mes_actual = (year == hoy.year and month_index == hoy.month)

        self.table.setRowCount(0)
        self.day_widgets = {}

        for d in range(1, dias_del_mes + 1):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(d)))

            valor_previo = days_data.get(str(d), 0) or 0
            le = QLineEdit()
            le.setValidator(QIntValidator(0, 1000000))
            le.setText(str(valor_previo))

            editable = (es_mes_actual and d <= self._dia_hoy)
            if not editable:
                le.setReadOnly(True)
                le.setStyleSheet("background-color: #2A2F32; color: #7D858B;")
            else:
                le.setStyleSheet("background-color: #202426;")

            self.table.setCellWidget(row, 1, le)
            self.day_widgets[d] = le

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.resizeColumnsToContents()
        self.totales_label.setText("")

        self._actualizar_info()

    def guardar(self):
        month_index = self.month_combo.currentIndex() + 1
        year = self.year
        hoy = datetime.now()
        if not (year == hoy.year and month_index == hoy.month):
            QMessageBox.warning(self, "Mes invalido", "Solo puedes guardar kilometraje del mes actual.")
            return

        days = {}
        for d, le in self.day_widgets.items():
            if d > self._dia_hoy:
                continue
            texto = le.text().strip()
            if not texto:
                continue
            try:
                valor = int(texto)
            except ValueError:
                continue
            if valor < 0:
                QMessageBox.warning(self, "Valor invalido", "El kilometraje no puede ser negativo.")
                return
            days[str(d)] = valor

        if not days:
            QMessageBox.information(self, "Sin cambios", "No hay valores para guardar en los dias disponibles.")
            return

        db.carros_kilometraje.update_one(
            {"carro_id": self.carro_id, "year": year, "month": month_index},
            {"$set": {"days": days}},
            upsert=True,
        )
        QMessageBox.information(self, "Guardado", "Kilometraje guardado correctamente.")
        self.cargar_dias()

    def calcular_totales(self):
        dias = sorted(self.day_widgets.keys())
        values = [int(le.text() or 0) for le in self.day_widgets.values()]
        semanas = []
        i = 0
        while i < len(dias):
            semana_vals = values[i:i+7]
            semanas.append(sum(semana_vals))
            i += 7
        total_mes = sum(values)
        text = []
        for idx, val in enumerate(semanas, start=1):
            text.append("Semana " + str(idx) + ": " + str(val) + " km")
        text.append("Total mes: " + str(total_mes) + " km")
        self.totales_label.setText(" | ".join(text))

    def _actualizar_info(self):
        km_actual = _obtener_km_actual_carro(self.carro_id)
        self._carro = db.carros.find_one({"_id": self.carro_id}) or self._carro
        ultimo = obtener_ultimo_cambio_aceite(self.carro_id)
        km_ultimo = int(ultimo.get("km", 0) or 0)
        fecha_ultimo = ultimo.get("fecha", "") or ""

        self.lbl_km_actual.setText("Kilometraje actual: " + (str(km_actual) if km_actual is not None else "-"))
        if fecha_ultimo:
            self.lbl_km_ultimo_aceite.setText("Ultimo cambio de aceite: " + str(km_ultimo) + " km (" + str(fecha_ultimo) + ")")
        else:
            self.lbl_km_ultimo_aceite.setText("Ultimo cambio de aceite: sin registros")
        self.lbl_intervalo.setText("Intervalo: " + str(self._intervalo) + " km")

        self.banner_aceite.actualizar(km_actual, km_ultimo, self._intervalo)

    def _hay_solicitud_aceite_pendiente(self):
        return db.carros_aceite.find_one(
            {"carro_id": self.carro_id, "estado": "pendiente"},
            projection={"_id": 1},
        ) is not None

    def registrar_cambio_aceite(self):
        km_actual = _obtener_km_actual_carro(self.carro_id)
        km_ultimo_doc = db.carros_aceite.find_one(
            {"carro_id": self.carro_id, "estado": {"$ne": "pendiente"}},
            projection={"km": 1},
            sort=[("updated_at", -1), ("created_at", -1), ("fecha", -1), ("_id", -1)],
        )
        km_ultimo = int(km_ultimo_doc["km"]) if km_ultimo_doc else int(self._carro.get("ultimo_cambio_aceite_km", 0) or 0)

        sugerido = ""
        if km_actual is not None and km_actual > km_ultimo:
            sugerido = str(km_actual)

        texto, ok = QInputDialog.getText(
            self,
            "Cambio de aceite",
            "Kilometraje al cambio (ultimo registrado: " + str(km_ultimo) + "):",
            text=sugerido,
        )
        if not ok:
            return
        try:
            km = int(texto)
        except ValueError:
            QMessageBox.warning(self, "Km invalido", "Ingresa un numero entero.")
            return

        obs, _ = QInputDialog.getText(self, "Cambio de aceite", "Observacion (opcional):")
        ok, mensaje = registrar_cambio_aceite(self.carro_id, km, observacion=obs)
        if not ok:
            QMessageBox.warning(self, "No se pudo registrar", mensaje)
            return
        QMessageBox.information(self, "Solicitud enviada", mensaje)
        self._actualizar_info()

    def ver_historial_aceite(self):
        historial = obtener_historial_aceite(self.carro_id)
        ventana = HistorialAceiteWindow(self.carro_id, historial, self)
        ventana.exec()


class HistorialAceiteWindow(QDialog):
    def __init__(self, carro_id, historial, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Historial de aceite - " + str(carro_id))
        self.resize(920, 460)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Carro: " + str(carro_id)))
        if not historial:
            layout.addWidget(QLabel("Sin cambios de aceite registrados."))
        else:
            tabla = QTableWidget(len(historial), 5)
            tabla.setHorizontalHeaderLabels(["Fecha", "Kilometraje", "Observacion", "Estado", "Acciones"])
            tabla.setEditTriggers(QTableWidget.NoEditTriggers)
            tabla.verticalHeader().setVisible(False)
            for fila, item in enumerate(historial):
                tabla.setItem(fila, 0, QTableWidgetItem(str(item.get("fecha", ""))))
                tabla.setItem(fila, 1, QTableWidgetItem(str(item.get("km", ""))))
                tabla.setItem(fila, 2, QTableWidgetItem(str(item.get("observacion", ""))))
                tabla.setItem(fila, 3, QTableWidgetItem(str(item.get("estado", "aceptado"))))

                contenedor = QHBoxLayout()
                contenedor.setContentsMargins(0, 0, 0, 0)
                contenedor.setSpacing(6)

                btn_pdf = QPushButton("Abrir PDF")
                ruta_pdf = item.get("pdf_path", "") or ""
                btn_pdf.setEnabled(bool(ruta_pdf))
                btn_pdf.clicked.connect(lambda _, r=ruta_pdf: abrir_archivo(r, self))
                contenedor.addWidget(btn_pdf)

                if str(item.get("estado", "")) == "pendiente" and admin_state.is_admin():
                    btn_aceptar = QPushButton("Aceptar cambio")
                    btn_aceptar.clicked.connect(lambda _, doc=item: self._aceptar_solicitud(doc))
                    contenedor.addWidget(btn_aceptar)

                widget_acciones = QWidget(self)
                widget_acciones.setLayout(contenedor)
                tabla.setCellWidget(fila, 4, widget_acciones)
            tabla.resizeColumnsToContents()
            layout.addWidget(tabla)
        botones = QHBoxLayout()
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        botones.addStretch()
        botones.addWidget(btn_cerrar)
        layout.addLayout(botones)

    def _aceptar_solicitud(self, item):
        if not admin_state.is_admin():
            QMessageBox.warning(self, "Permiso denegado", "Solo el administrador puede aceptar el cambio de aceite.")
            return
        solicitud_id = item.get("_id")
        if not solicitud_id:
            return
        respuesta = QMessageBox.question(
            self,
            "Aceptar cambio de aceite",
            f"¿Aceptar la solicitud de cambio de aceite en {item.get('km', '')} km?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if respuesta != QMessageBox.Yes:
            return
        ok, mensaje = aceptar_cambio_aceite(str(solicitud_id))
        if not ok:
            QMessageBox.warning(self, "No se pudo aceptar", mensaje)
            return
        QMessageBox.information(self, "Cambio aceptado", mensaje)
        self._refrescar_alertas_y_historial()
        self.accept()

    def _refrescar_alertas_y_historial(self):
        ventana = self.parentWidget()
        if ventana is None:
            return
        if hasattr(ventana, "_actualizar_info"):
            ventana._actualizar_info()
        main_window = ventana.window()
        if main_window is None:
            return
        for pagina in getattr(main_window, "pages", []) or []:
            if pagina is not None and hasattr(pagina, "cargar") and getattr(pagina.__class__, "__name__", "") == "AlertasPage":
                pagina.cargar()
