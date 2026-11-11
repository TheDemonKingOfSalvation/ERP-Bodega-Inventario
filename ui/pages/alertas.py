"""Panel de alertas para el modo administrador."""
from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QSizePolicy,
)
from PySide6.QtCore import QTimer

from logic.logic_mongo import obtener_alertas_admin
from ui.utils import abrir_archivo


def destino_reabastecimiento_para_tipo(tipo):
    tipo_texto = str(tipo or "").strip().lower()
    return {
        "herramienta": "herramientas",
        "herramientas": "herramientas",
        "epp": "epp",
        "consumible": "consumibles",
        "consumibles": "consumibles",
        "pvc": "pvc",
    }.get(tipo_texto, "informe_reabastecimiento")


class _BloqueAlerta(QFrame):
    def __init__(self, titulo, color):
        super().__init__()
        self.setObjectName("tarjetaAlerta")
        self.setStyleSheet(
            f"#tarjetaAlerta {{ background-color: {color}; border-radius: 12px; padding: 10px; }}"
        )
        layout = QVBoxLayout(self)
        self.titulo = QLabel(titulo)
        self.titulo.setStyleSheet("color: white; font-size: 13px; font-weight: 600;")
        self.numero = QLabel("0")
        self.numero.setStyleSheet("color: white; font-size: 26px; font-weight: 800;")
        layout.addWidget(self.titulo)
        layout.addWidget(self.numero)

    def set_numero(self, valor):
        self.numero.setText(str(valor))


class AlertasPage(QWidget):
    def __init__(self, navegar_callback=None, callback_actualizar=None):
        super().__init__()
        self.navegar_callback = navegar_callback
        self.callback_actualizar = callback_actualizar
        self.setWindowTitle("Alertas (admin)")

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        titulo = QLabel("Alertas del modo administrador")
        titulo.setStyleSheet("font-size: 22px; font-weight: 700;")
        self.btn_refrescar = QPushButton("Actualizar")
        header.addWidget(titulo)
        header.addStretch()
        header.addWidget(self.btn_refrescar)
        layout.addLayout(header)

        self.resumen = QLabel("")
        layout.addWidget(self.resumen)

        cards = QHBoxLayout()
        self.card_herramientas = _BloqueAlerta("Items no devueltos", "#8F3D3D")
        self.card_requerimientos = _BloqueAlerta("Requerimientos pendientes", "#9E932B")
        self.card_mantenimientos = _BloqueAlerta("Mantenimientos activos", "#26334A")
        self.card_aceite = _BloqueAlerta("Cambios de aceite vencidos", "#2F6B4F")
        self.card_aceite_pendientes = _BloqueAlerta("Solicitudes aceite pendientes", "#4B6A95")
        for card in (self.card_herramientas, self.card_requerimientos, self.card_mantenimientos, self.card_aceite, self.card_aceite_pendientes):
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            cards.addWidget(card)
        layout.addLayout(cards)

        self.seccion_label = QLabel("")
        self.seccion_label.setStyleSheet("font-size: 18px; font-weight: 700; padding-top: 6px;")
        layout.addWidget(self.seccion_label)

        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(["Item", "Detalle", "Cantidad / Km", "Origen", "Accion"])
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        layout.addWidget(self.tabla)

        self.btn_refrescar.clicked.connect(self.cargar)
        self._timer = QTimer(self)
        self._timer.setInterval(30000)
        self._timer.timeout.connect(self.cargar)

    def showEvent(self, event):
        super().showEvent(event)
        self.cargar()
        self._timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.cargar()

    def cargar(self):
        datos = obtener_alertas_admin()
        conteo = datos["conteo"]
        self.card_herramientas.set_numero(conteo["herramientas_pendientes"])
        self.card_requerimientos.set_numero(conteo["requerimientos_pendientes"])
        self.card_mantenimientos.set_numero(conteo["mantenimientos_activos"])
        self.card_aceite.set_numero(conteo["aceite_vencidos"])
        self.card_aceite_pendientes.set_numero(conteo["aceite_pendientes"])
        self.resumen.setText(
            f"Items no devueltos: {conteo['herramientas_pendientes']}  |  "
            f"Requerimientos pendientes: {conteo['requerimientos_pendientes']}  |  "
            f"Mantenimientos activos: {conteo['mantenimientos_activos']}  |  "
            f"Aceite vencido: {conteo['aceite_vencidos']}  |  "
            f"Solicitudes aceite pendientes: {conteo['aceite_pendientes']}  |  "
            f"Por vencer (10%): {conteo['aceite_por_vencer']}"
        )

        self._llenar_principal(datos)

    def _llenar_principal(self, datos):
        filas = []

        for item in datos["herramientas"]:
            label = "Herramienta no devuelta" if item.get("tipo") == "herramienta" else "Máquina no devuelta"
            filas.append((
                label,
                f"{item['item_id']} - {item['item_nombre']}",
                f"{item['pendientes']} ud(s)",
                f"Trabajo {item['trabajo_id']} - {item['punto']}",
                "trabajos",
                f"Trabajo {item['trabajo_id']}",
            ))

        for req in datos["requerimientos"]:
            proveedor = (req.get("proveedor") or {}).get("nombre", "")
            filas.append((
                f"Requerimiento de reabastecimiento ({req.get('tipo', '').upper()})",
                f"{proveedor} - {req.get('fecha', '')}",
                f"{len(req.get('items', []))} item(s)",
                str(req.get("_id", "")),
                destino_reabastecimiento_para_tipo(req.get("tipo")),
                "Ir al informe",
            ))

        for mant in datos["mantenimientos"]:
            filas.append((
                "Mantenimiento activo",
                f"{mant.get('codigo', '')} - {mant.get('nombre', '')}",
                str(mant.get("fecha", "")),
                str(mant.get("razon", "")),
                "informe_mantenimiento",
                "Ir al informe",
            ))

        for carro in datos["aceite_pendientes"]:
            pdf_rel = carro.get("solicitud_pdf_path", "") or ""
            accion = "Abrir PDF" if pdf_rel else "Ir al carro"
            destino = pdf_rel if pdf_rel else "carros"
            filas.append((
                "Solicitud de aceite pendiente",
                f"{carro['carro_id']} - {carro['carro_nombre']}",
                f"{carro['solicitud_aceite_km']} km ({carro['solicitud_aceite_fecha']})",
                f"Solicitada para: {carro['solicitud_aceite_fecha']}",
                destino,
                accion,
            ))

        for carro in datos["aceite"]:
            if not carro.get("vencido"):
                continue
            pdf_rel = carro.get("ultimo_pdf_path", "") or ""
            accion = "Abrir PDF" if pdf_rel else "Ir al carro"
            destino = pdf_rel if pdf_rel else "carros"
            filas.append((
                "Cambio de aceite vencido",
                f"{carro['carro_id']} - {carro['carro_nombre']}",
                f"+{carro['km_recorridos']} / {carro['intervalo']} km",
                f"Ultimo cambio: {carro['ultimo_cambio_km']} km ({carro['ultimo_cambio_fecha']})",
                destino,
                accion,
            ))

        self.tabla.setRowCount(len(filas))
        for row, (categoria, detalle, cantidad, origen, destino, accion) in enumerate(filas):
            self.tabla.setItem(row, 0, QTableWidgetItem(categoria))
            self.tabla.setItem(row, 1, QTableWidgetItem(detalle))
            self.tabla.setItem(row, 2, QTableWidgetItem(cantidad))
            self.tabla.setItem(row, 3, QTableWidgetItem(origen))
            btn = self._crear_boton_accion(destino, accion)
            self.tabla.setCellWidget(row, 4, btn)

        self.tabla.resizeColumnsToContents()
        if filas:
            self.seccion_label.setText(f"{len(filas)} alertas activas")
        else:
            self.seccion_label.setText("Sin alertas activas")

    def _crear_boton_accion(self, destino, accion):
        btn = QPushButton(accion)
        btn.setProperty("destino", destino)
        if self._es_ruta_archivo(destino):
            btn.clicked.connect(partial(self._abrir_pdf, destino))
        else:
            btn.clicked.connect(partial(self._ir_a, destino))
        return btn

    def _es_ruta_archivo(self, destino):
        destino = str(destino or "")
        return bool(destino) and (destino.endswith(".pdf") or "\\" in destino or "/" in destino)

    def _ir_a(self, destino):
        if self.navegar_callback:
            self.navegar_callback(destino)

    def _abrir_pdf(self, ruta):
        abrir_archivo(ruta, self)


def db_carros_aceite_ultimo(carro_id):
    """Helper local: trae el ultimo cambio de aceite con su pdf_path."""
    from config.db_mongo import db
    return db.carros_aceite.find_one(
        {"carro_id": str(carro_id)},
        projection={"km": 1, "fecha": 1, "pdf_path": 1, "estado": 1},
        sort=[("created_at", -1), ("fecha", -1), ("_id", -1)],
    )
