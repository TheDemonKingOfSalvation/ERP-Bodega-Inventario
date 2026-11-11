from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QCheckBox,
    QTableWidget, QTableWidgetItem, QMessageBox,
)

from config.db_mongo import db
from logic.logic_mongo import entregar_epp_trabajador


class TrabajadorEppAgregarPage(QWidget):
    def __init__(self, trabajador_id):
        super().__init__()
        self.trabajador_id = trabajador_id

        self.setWindowTitle("Agregar EPP al trabajador")
        self.resize(800, 500)

        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Seleccionar", "Codigo", "Nombre", "Stock", "Reposicion Si", "Reposicion No",
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.btn_entregar = QPushButton("Entregar seleccionados")
        self.btn_actualizar = QPushButton("Actualizar checklist")

        layout.addWidget(QLabel("Checklist de EPP disponibles"))
        layout.addWidget(self.table)
        layout.addWidget(self.btn_entregar)
        layout.addWidget(self.btn_actualizar)

        self.btn_entregar.clicked.connect(self.entregar)
        self.btn_actualizar.clicked.connect(self.cargar)

        self.cargar()

    def cargar(self):
        data = list(db.epp.find({"cantidad": {"$gt": 0}}, projection={"_id": 1, "nombre": 1, "cantidad": 1}))
        self.table.setRowCount(len(data))

        for row, epp in enumerate(data):
            chk = QCheckBox()
            repo_si = QCheckBox()
            repo_no = QCheckBox()
            repo_si.setEnabled(False)
            repo_no.setEnabled(False)

            chk.stateChanged.connect(
                lambda state, si=repo_si, no=repo_no: self.activar_reposicion(state, si, no)
            )
            repo_si.stateChanged.connect(
                lambda state, si=repo_si, no=repo_no: self.controlar_reposicion(state, si, no)
            )
            repo_no.stateChanged.connect(
                lambda state, no=repo_no, si=repo_si: self.controlar_reposicion(state, no, si)
            )

            self.table.setCellWidget(row, 0, chk)
            self.table.setItem(row, 1, QTableWidgetItem(str(epp.get("_id", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(epp.get("nombre", "")))
            self.table.setItem(row, 3, QTableWidgetItem(str(epp.get("cantidad", 0))))
            self.table.setCellWidget(row, 4, repo_si)
            self.table.setCellWidget(row, 5, repo_no)

        self.table.resizeColumnsToContents()

    def activar_reposicion(self, state, repo_si, repo_no):
        seleccionado = state == 2
        repo_si.setEnabled(seleccionado)
        repo_no.setEnabled(seleccionado)
        if not seleccionado:
            repo_si.setChecked(False)
            repo_no.setChecked(False)

    def controlar_reposicion(self, state, actual, otro):
        if state == 2:
            otro.setChecked(False)
            otro.setEnabled(False)
        else:
            otro.setEnabled(True)

    def entregar(self):
        epps = []
        for row in range(self.table.rowCount()):
            chk = self.table.cellWidget(row, 0)
            if chk and chk.isChecked():
                codigo = self.table.item(row, 1).text()
                repo_si = self.table.cellWidget(row, 4)
                repo_no = self.table.cellWidget(row, 5)
                if not repo_si.isChecked() and not repo_no.isChecked():
                    QMessageBox.warning(
                        self, "Error",
                        f"Selecciona reposicion Si o No para el EPP {codigo}",
                    )
                    return
                epps.append({
                    "codigo": codigo,
                    "reposicion": "Si" if repo_si.isChecked() else "No",
                })

        if not epps:
            QMessageBox.warning(self, "Error", "Selecciona al menos un EPP")
            return

        ok, msg = entregar_epp_trabajador(self.trabajador_id, epps)
        if not ok:
            QMessageBox.critical(self, "Error", msg)
            return
        QMessageBox.information(self, "OK", "EPP entregado correctamente")
        self.cargar()

