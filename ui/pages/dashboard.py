from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QInputDialog, QLineEdit,
)

from ui.admin_state import admin_state
from logic.logic_mongo import obtener_resumen_dashboard, obtener_alertas_admin


class DashboardPage(QWidget):
    def __init__(self, navegar_callback=None):
        super().__init__()
        self.navegar_callback = navegar_callback

        layout = QVBoxLayout(self)

        self.label = QLabel("")
        self.admin_label = QLabel("")
        self.alertas_label = QLabel("")
        self.btn = QPushButton("Actualizar dashboard")
        self.btn_admin = QPushButton("Activar modo administrador")
        self.btn_alertas = QPushButton("Ir a alertas")

        layout.addWidget(QLabel("Resumen general"))
        layout.addWidget(self.label)
        layout.addWidget(self.admin_label)
        layout.addWidget(self.alertas_label)
        layout.addWidget(self.btn)
        layout.addWidget(self.btn_admin)
        layout.addWidget(self.btn_alertas)
        layout.addStretch()

        self.btn.clicked.connect(self.cargar)
        self.btn_admin.clicked.connect(self.cambiar_modo_admin)
        self.btn_alertas.clicked.connect(self.ir_a_alertas)
        admin_state.changed.connect(self.actualizar_estado_admin)

        self.actualizar_estado_admin(admin_state.is_admin())

    def actualizar_estado_admin(self, activo):
        if activo:
            self.admin_label.setText("Modo administrador: ACTIVADO")
            self.btn_admin.setText("Desactivar modo administrador")
        else:
            self.admin_label.setText("Modo administrador: DESACTIVADO")
            self.btn_admin.setText("Activar modo administrador")
        self.cargar()

    def cambiar_modo_admin(self):
        if admin_state.is_admin():
            respuesta = QMessageBox.question(
                self,
                "Desactivar modo administrador",
                "¿Deseas desactivar el modo administrador?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if respuesta != QMessageBox.Yes:
                return
            admin_state.desactivar()
            QMessageBox.information(
                self,
                "Modo administrador",
                "El modo administrador fue desactivado.",
            )
            return

        usuario, ok = QInputDialog.getText(self, "Modo administrador", "Usuario:")
        if not ok:
            return
        password, ok = QInputDialog.getText(
            self, "Modo administrador", "Contrasena:", QLineEdit.Password,
        )
        if not ok:
            return
        if not admin_state.activar(usuario.strip(), password):
            QMessageBox.warning(
                self, "Acceso denegado", "Usuario o contrasena incorrectos.",
            )
            return
        QMessageBox.information(
            self, "Modo administrador", "El modo administrador fue activado.",
        )

    def ir_a_alertas(self):
        if self.navegar_callback:
            self.navegar_callback("alertas")

    def cargar(self):
        resumen = obtener_resumen_dashboard()
        self.label.setText(
            f"Maquinas en mantenimiento: {resumen['maquinas_mantenimiento']}\n"
            f"Trabajos activos: {resumen['trabajos_activos']}\n"
            f"Trabajos pendientes de devolucion: {resumen['trabajos_pendientes_devolucion']}\n"
            f"Requerimientos pendientes: {resumen['requerimientos_pendientes']}\n"
            f"EPP bajo stock: {resumen['bajo_stock_epp']}\n"
            f"Consumibles bajo stock: {resumen['bajo_stock_consumibles']}\n"
            f"PVC bajo stock: {resumen['bajo_stock_pvc']}"
        )
        if admin_state.is_admin():
            alertas = obtener_alertas_admin()
            c = alertas["conteo"]
            self.alertas_label.setText(
                f"Alertas -> Herramientas retenidas: {c['herramientas_pendientes']}  |  "
                f"Req. pendientes: {c['requerimientos_pendientes']}  |  "
                f"Mantenimientos activos: {c['mantenimientos_activos']}  |  "
                f"Aceite vencido: {c['aceite_vencidos']}  |  "
                f"Solicitudes aceite pendientes: {c['aceite_pendientes']}"
            )
        else:
            self.alertas_label.setText("")
