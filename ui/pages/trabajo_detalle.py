from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QCheckBox, QMessageBox,
)
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
from io import BytesIO
from datetime import datetime
import os

from config.db_mongo import db
from ui.admin_state import admin_state
from ui.utils import (
    obtener_base_pdf, ruta_recurso, obtener_pdf_unico, coleccion_por_tipo,
)
from logic.logic_mongo import guardar_detalle_trabajo, obtener_stock


class SelectorRecursoDialog(QDialog):
    def __init__(self, tipo, parent=None):
        super().__init__(parent)
        self.tipo = tipo
        self.recursos_seleccionados = []
        self.datos = []
        self.setWindowTitle("Seleccionar " + str(tipo))
        self.resize(750, 450)
        layout = QVBoxLayout(self)
        self.buscar_input = QLineEdit()
        self.buscar_input.setPlaceholderText("Buscar por ID o nombre")
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        if self.tipo in ["herramienta", "consumible", "pvc"]:
            self.table.setSelectionMode(QTableWidget.MultiSelection)
        else:
            self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.btn_seleccionar = QPushButton("Seleccionar")
        self.btn_cancelar = QPushButton("Cancelar")
        botones = QHBoxLayout()
        botones.addWidget(self.btn_seleccionar)
        botones.addWidget(self.btn_cancelar)
        layout.addWidget(QLabel("Listado de " + str(tipo)))
        layout.addWidget(self.buscar_input)
        layout.addWidget(self.table)
        layout.addLayout(botones)
        self.buscar_input.textChanged.connect(self.filtrar)
        self.btn_seleccionar.clicked.connect(self.seleccionar)
        self.btn_cancelar.clicked.connect(self.reject)
        self.table.cellDoubleClicked.connect(self.seleccionar)
        self.cargar_datos()

    def cargar_datos(self):
        self.datos = list(db[coleccion_por_tipo(self.tipo)].find())
        self.llenar_tabla(self.datos)

    def _obtener_nombre_carro(self, doc):
        return str(doc.get("placa") or doc.get("nombre") or doc.get("_id", ""))

    def _obtener_disponibilidad_carro(self, doc):
        valor = str(doc.get("disponibilidad", "")).strip().upper()
        if valor in {"NO", "N", "FALSE", "0", "OCUPADO", "NO DISPONIBLE", "EN USO"}:
            return "No disponible"
        if valor in {"SI", "S", "TRUE", "1", "DISPONIBLE", "LIBRE"}:
            return "Disponible"

        estatus = str(doc.get("estatus", "")).strip().lower()
        if estatus in {"ocupado", "trabajando", "mantenimiento", "en mantenimiento", "no disponible", "no_disponible"}:
            return "No disponible"
        if estatus in {"disponible", "libre", "activo"}:
            return "Disponible"

        carro_id = str(doc.get("_id", "")).strip()
        if carro_id:
            trabajo = db.trabajos.find_one(
                {"carro_id": carro_id, "estatus": {"$ne": "finalizado"}},
                projection={"_id": 1},
            )
            if trabajo:
                return "No disponible"
        return "Disponible"

    def llenar_tabla(self, datos):
        if self.tipo in ["herramienta", "consumible", "pvc"]:
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Cantidad"])
        elif self.tipo == "maquina":
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Disponibilidad"])
        elif self.tipo == "carro":
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["ID", "Placa / Nombre", "Descripcion", "Disponibilidad"])
        else:
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Tipo"])
        self.table.setRowCount(0)
        for doc in datos:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(doc.get("_id", ""))))
            if self.tipo == "carro":
                nombre_mostrar = self._obtener_nombre_carro(doc)
                disponibilidad_text = self._obtener_disponibilidad_carro(doc)
                self.table.setItem(row, 1, QTableWidgetItem(str(nombre_mostrar)))
                self.table.setItem(row, 2, QTableWidgetItem(str(doc.get("descripcion", ""))))
                self.table.setItem(row, 3, QTableWidgetItem(disponibilidad_text))
            else:
                self.table.setItem(row, 1, QTableWidgetItem(str(doc.get("nombre", ""))))
                if self.tipo == "maquina":
                    self.table.setItem(row, 2, QTableWidgetItem(str(doc.get("disponibilidad", ""))))
                elif self.tipo in ["herramienta", "consumible", "pvc"]:
                    self.table.setItem(row, 2, QTableWidgetItem(str(doc.get("cantidad", ""))))
                else:
                    self.table.setItem(row, 2, QTableWidgetItem(str(doc.get("tipo", ""))))
        self.table.resizeColumnsToContents()

    def filtrar(self):
        texto = self.buscar_input.text().strip().lower()
        if not texto:
            self.llenar_tabla(self.datos)
            return
        filtrados = []
        for d in self.datos:
            blob = " ".join([
                str(d.get("_id", "")), str(d.get("nombre", "")),
                str(d.get("placa", "")), str(d.get("descripcion", "")),
                self._obtener_nombre_carro(d), self._obtener_disponibilidad_carro(d),
            ]).lower()
            if texto in blob:
                filtrados.append(d)
        self.llenar_tabla(filtrados)

    def seleccionar(self):
        filas = sorted({idx.row() for idx in self.table.selectedIndexes()})
        if not filas and self.table.currentRow() >= 0:
            filas = [self.table.currentRow()]
        if not filas:
            QMessageBox.warning(self, "Sin seleccion", "Selecciona al menos un item.")
            return
        self.recursos_seleccionados = []
        for row in filas:
            id_item = self.table.item(row, 0)
            if id_item is None:
                continue
            nombre_item = self.table.item(row, 1) if self.table.columnCount() > 1 else None
            disponibilidad_item = self.table.item(row, 3) if self.table.columnCount() > 3 else None
            self.recursos_seleccionados.append({
                "id": id_item.text(),
                "nombre": nombre_item.text() if nombre_item else "",
                "placa": nombre_item.text() if nombre_item else "",
                "disponibilidad": disponibilidad_item.text() if disponibilidad_item else "",
            })
        self.accept()


class TrabajoDetallePage(QWidget):
    def __init__(self, trabajo_id):
        super().__init__()
        self.trabajo_id = trabajo_id
        self._cache_nombres_local = {}
        self.setWindowTitle("Detalle Trabajo")
        self.resize(1100, 650)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Detalle del trabajo"))
        self.info_label = QLabel("")
        layout.addWidget(self.info_label)
        b1 = QHBoxLayout()
        self.btn_trabajador = QPushButton("Trabajadores")
        self.btn_h = QPushButton("Herramientas")
        self.btn_m = QPushButton("Maquinas")
        self.btn_c = QPushButton("Consumibles")
        self.btn_pvc = QPushButton("PVC")
        for b in (self.btn_trabajador, self.btn_h, self.btn_m, self.btn_c, self.btn_pvc):
            b1.addWidget(b)
        layout.addLayout(b1)
        b2 = QHBoxLayout()
        self.btn_carro = QPushButton("Seleccionar carro")
        self.btn_supervisor = QPushButton("Marcar supervisor")
        self.btn_salida_bodega = QPushButton("Generar hoja salida bodega")
        self.btn_informe_no_devueltos = QPushButton("Generar informe no devueltos")
        for b in (self.btn_carro, self.btn_supervisor, self.btn_salida_bodega, self.btn_informe_no_devueltos):
            b2.addWidget(b)
        layout.addLayout(b2)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Tipo", "ID", "Nombre", "Cantidad", "Devuelto", "Usado", "Volvio"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        b3 = QHBoxLayout()
        self.btn_guardar = QPushButton("Guardar checklist")
        self.btn_eliminar = QPushButton("Eliminar seleccionado")
        self.btn_recargar = QPushButton("Recargar")
        for b in (self.btn_guardar, self.btn_eliminar, self.btn_recargar):
            b3.addWidget(b)
        layout.addLayout(b3)
        self.btn_trabajador.clicked.connect(lambda: self.abrir_selector("trabajador"))
        self.btn_h.clicked.connect(lambda: self.abrir_selector("herramienta"))
        self.btn_m.clicked.connect(lambda: self.abrir_selector("maquina"))
        self.btn_c.clicked.connect(lambda: self.abrir_selector("consumible"))
        self.btn_pvc.clicked.connect(lambda: self.abrir_selector("pvc"))
        self.btn_carro.clicked.connect(self.seleccionar_carro)
        self.btn_supervisor.clicked.connect(self.marcar_supervisor)
        self.btn_salida_bodega.clicked.connect(self.generar_hoja_salida_bodega)
        self.btn_informe_no_devueltos.clicked.connect(self.generar_informe_no_devueltos)
        self.btn_guardar.clicked.connect(self.guardar)
        self.btn_eliminar.clicked.connect(self.eliminar_fila)
        self.btn_recargar.clicked.connect(self.cargar)
        admin_state.changed.connect(self.aplicar_modo_admin)
        self.aplicar_modo_admin(admin_state.is_admin())
        self.cargar()

    def aplicar_modo_admin(self, activo):
        self.btn_eliminar.setEnabled(activo)
        self.btn_eliminar.setToolTip("" if activo else "Solo el administrador puede eliminar filas del detalle.")

    def abrir_selector(self, tipo):
        d = SelectorRecursoDialog(tipo, self)
        if d.exec() == QDialog.Accepted:
            for r in d.recursos_seleccionados:
                self.add_row(tipo=tipo, id_val=r["id"], cantidad=1)

    def seleccionar_carro(self):
        d = SelectorRecursoDialog("carro", self)
        if d.exec() == QDialog.Accepted and d.recursos_seleccionados:
            c = d.recursos_seleccionados[0]
            nombre_carro = c.get("nombre", "") or c.get("placa", "") or c.get("id", "")
            db.trabajos.update_one(
                {"_id": self.trabajo_id},
                {"$set": {"carro_id": c.get("id", ""), "carro_nombre": nombre_carro}},
            )
            QMessageBox.information(self, "Carro seleccionado", "Carro: " + str(nombre_carro))
            self.actualizar_info_trabajo()

    def get_collection(self, tipo):
        return coleccion_por_tipo(tipo)

    def get_nombre(self, tipo, id_val):
        clave = (tipo, id_val)
        if clave in self._cache_nombres_local:
            return self._cache_nombres_local[clave]
        doc = db[self.get_collection(tipo)].find_one({"_id": id_val}, projection={"nombre": 1})
        nombre = doc["nombre"] if doc else "NO EXISTE"
        self._cache_nombres_local[clave] = nombre
        return nombre

    def existe(self, tipo, id_val):
        return db[self.get_collection(tipo)].find_one({"_id": id_val}, projection={"_id": 1}) is not None

    def get_stock(self, tipo, id_val):
        return obtener_stock(tipo, id_val)

    def buscar_fila_existente(self, tipo, id_val):
        for row in range(self.table.rowCount()):
            it_tipo = self.table.item(row, 0)
            it_id = self.table.item(row, 1)
            if it_tipo and it_id and it_tipo.text() == tipo and it_id.text() == id_val:
                return row
        return -1

    def crear_fila_base(self, row, tipo, id_val, nombre, cantidad):
        self.table.setItem(row, 0, QTableWidgetItem(tipo))
        self.table.setItem(row, 1, QTableWidgetItem(id_val))
        self.table.setItem(row, 2, QTableWidgetItem(nombre))
        self.table.setItem(row, 3, QTableWidgetItem(str(cantidad)))
        self.table.setCellWidget(row, 4, QCheckBox())
        if tipo in ["consumible", "pvc"]:
            self.table.setCellWidget(row, 5, QLineEdit("0"))
            self.table.setCellWidget(row, 6, QLineEdit("0"))
        elif tipo == "herramienta":
            self.table.setCellWidget(row, 5, QLabel("-"))
            self.table.setCellWidget(row, 6, QLineEdit("0"))
        else:
            self.table.setCellWidget(row, 5, QLabel("-"))
            self.table.setCellWidget(row, 6, QLabel("-"))

    def actualizar_info_trabajo(self):
        trabajo = db.trabajos.find_one(
            {"_id": self.trabajo_id},
            projection={"supervisor_nombre": 1, "chofer_nombre": 1, "carro_nombre": 1},
        )
        if not trabajo:
            self.info_label.setText("Trabajo no encontrado")
            return
        self.info_label.setText(
            "Supervisor: " + str(trabajo.get("supervisor_nombre", "Sin supervisor")) +
            " | Chofer: " + str(trabajo.get("chofer_nombre", "Sin chofer")) +
            " | Carro: " + str(trabajo.get("carro_nombre", "Sin carro"))
        )

    def stack_row(self, tipo, id_val):
        fila = self.buscar_fila_existente(tipo, id_val)
        if fila == -1:
            return False
        item_cantidad = self.table.item(fila, 3)
        if item_cantidad is None:
            return False
        try:
            cantidad_actual = int(item_cantidad.text())
        except ValueError:
            cantidad_actual = 0
        if tipo in ["herramienta", "consumible", "pvc"]:
            if cantidad_actual + 1 > self.get_stock(tipo, id_val):
                QMessageBox.warning(self, "Stock insuficiente", "No hay suficiente cantidad disponible.")
                return True
        if tipo == "maquina":
            QMessageBox.warning(self, "Maquina repetida", "La maquina ya fue agregada a esta planta.")
            return True
        if tipo == "trabajador":
            QMessageBox.warning(self, "Trabajador repetido", "El trabajador ya fue agregado a esta planta.")
            return True
        item_cantidad.setText(str(cantidad_actual + 1))
        if tipo in ["consumible", "pvc"]:
            for col in (5, 6):
                w = self.table.cellWidget(fila, col)
                if isinstance(w, QLineEdit):
                    try:
                        actual = int(w.text())
                    except ValueError:
                        actual = 0
                    w.setText(str(min(actual, cantidad_actual + 1)))
        elif tipo == "herramienta":
            w = self.table.cellWidget(fila, 6)
            if isinstance(w, QLineEdit):
                try:
                    actual = int(w.text())
                except ValueError:
                    actual = 0
                w.setText(str(min(actual, cantidad_actual + 1)))
        return True

    def add_row(self, tipo, id_val, cantidad=1):
        id_val = id_val.strip()
        if not id_val:
            QMessageBox.warning(self, "Error", "ID vacio.")
            return
        if not self.existe(tipo, id_val):
            QMessageBox.critical(self, "Error", str(tipo) + " no existe.")
            return
        if tipo in ["herramienta", "consumible", "pvc"] and self.get_stock(tipo, id_val) < 1:
            QMessageBox.warning(self, "Sin stock", "Ese recurso no tiene stock disponible.")
            return
        if tipo == "maquina":
            maq = db.maquinas.find_one({"_id": id_val}, projection={"disponibilidad": 1})
            if not maq:
                QMessageBox.warning(self, "Error", "La maquina no existe.")
                return
            if maq.get("disponibilidad") == "NO":
                QMessageBox.warning(self, "Maquina no disponible", "La maquina ya esta retenida, trabajando o en mantenimiento.")
                return
        if self.stack_row(tipo, id_val):
            return
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.crear_fila_base(row=row, tipo=tipo, id_val=id_val, nombre=self.get_nombre(tipo, id_val), cantidad=cantidad)
        if tipo == "trabajador":
            self.verificar_chofer_automatico(id_val)
        self.table.resizeColumnsToContents()

    def eliminar_fila(self):
        if not admin_state.is_admin():
            QMessageBox.warning(self, "Acceso restringido", "Solo el administrador puede eliminar filas del detalle.")
            return
        fila = self.table.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Selecciona una fila", "Debes seleccionar una fila para eliminar.")
            return
        self.table.removeRow(fila)

    def marcar_supervisor(self):
        fila = self.table.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Selecciona trabajador", "Debes seleccionar un trabajador en la tabla.")
            return
        item_tipo = self.table.item(fila, 0)
        item_id = self.table.item(fila, 1)
        item_nombre = self.table.item(fila, 2)
        if not item_tipo or not item_id or not item_nombre:
            QMessageBox.warning(self, "Error", "Fila invalida.")
            return
        if item_tipo.text() != "trabajador":
            QMessageBox.warning(self, "Error", "Solo puedes marcar como supervisor a un trabajador.")
            return
        tid = item_id.text()
        tnombre = item_nombre.text().replace(" [SUPERVISOR]", "")
        for row in range(self.table.rowCount()):
            tr = self.table.item(row, 0)
            nr = self.table.item(row, 2)
            if tr and nr and tr.text() == "trabajador":
                nr.setText(nr.text().replace(" [SUPERVISOR]", ""))
        self.table.item(fila, 2).setText(tnombre + " [SUPERVISOR]")
        db.trabajos.update_one(
            {"_id": self.trabajo_id},
            {"$set": {"supervisor_id": tid, "supervisor_nombre": tnombre}},
        )
        QMessageBox.information(self, "Supervisor asignado", "Supervisor: " + str(tnombre))
        self.actualizar_info_trabajo()

    def verificar_chofer_automatico(self, trabajador_id):
        t = db.trabajadores.find_one({"_id": trabajador_id}, projection={"tipo": 1, "nombre": 1})
        if not t or str(t.get("tipo", "")).strip().lower() != "conductor":
            return
        trabajo = db.trabajos.find_one({"_id": self.trabajo_id}, projection={"chofer_id": 1})
        if trabajo and trabajo.get("chofer_id"):
            return
        db.trabajos.update_one(
            {"_id": self.trabajo_id},
            {"$set": {"chofer_id": trabajador_id, "chofer_nombre": t.get("nombre", "")}},
        )
        QMessageBox.information(self, "Chofer asignado", "Chofer automatico: " + str(t.get("nombre", "")))
        self.actualizar_info_trabajo()

    def guardar(self):
        detalles = []
        for row in range(self.table.rowCount()):
            try:
                it_tipo = self.table.item(row, 0)
                it_id = self.table.item(row, 1)
                it_nombre = self.table.item(row, 2)
                it_cantidad = self.table.item(row, 3)
                if not all([it_tipo, it_id, it_nombre, it_cantidad]):
                    QMessageBox.critical(self, "Error", "Hay una fila incompleta.")
                    return
                tipo = it_tipo.text()
                id_val = it_id.text()
                nombre = it_nombre.text().replace(" [SUPERVISOR]", "")
                cantidad = int(it_cantidad.text())
                chk = self.table.cellWidget(row, 4)
                devuelto = chk.isChecked() if isinstance(chk, QCheckBox) else False
                usado = 0
                vuelto = 0
                if tipo in ["consumible", "pvc"]:
                    uw = self.table.cellWidget(row, 5)
                    vw = self.table.cellWidget(row, 6)
                    try:
                        usado = int(uw.text()) if isinstance(uw, QLineEdit) else 0
                        vuelto = int(vw.text()) if isinstance(vw, QLineEdit) else 0
                    except ValueError:
                        QMessageBox.critical(self, "Error", "Usado/Volvio invalido en " + str(tipo) + ".")
                        return
                    if usado < 0 or vuelto < 0:
                        QMessageBox.critical(self, "Error", "Usado/Volvio no puede ser negativo en " + str(tipo) + ".")
                        return
                    if usado + vuelto > cantidad:
                        QMessageBox.critical(self, "Error", "Usado + volvio supera la cantidad en " + str(tipo) + ".")
                        return
                elif tipo == "herramienta":
                    vw = self.table.cellWidget(row, 6)
                    try:
                        vuelto = int(vw.text()) if isinstance(vw, QLineEdit) else 0
                    except ValueError:
                        QMessageBox.critical(self, "Error", "Volvio invalido en herramienta.")
                        return
                    if vuelto < 0:
                        QMessageBox.critical(self, "Error", "Volvio no puede ser negativo.")
                        return
                    if vuelto > cantidad:
                        QMessageBox.critical(self, "Error", "Volvio supera la cantidad enviada.")
                        return
                detalles.append({
                    "tipo": tipo, "id": id_val, "nombre": nombre,
                    "cantidad": cantidad, "devuelto": devuelto,
                    "usado": usado, "vuelto": vuelto,
                })
            except Exception as e:
                QMessageBox.critical(self, "Error", "Datos invalidos en la tabla:\n" + str(e))
                return
        ok, msg = guardar_detalle_trabajo(self.trabajo_id, detalles)
        if not ok:
            QMessageBox.critical(self, "Error", msg)
            return
        self.cargar()
        QMessageBox.information(self, "OK", "Checklist guardado correctamente.")

    def _generar_pdf_plantilla(self, plantilla_relativa, carpeta_relativa, nombre_base,
                               campos_header, lineas_items, salida_btn, dir_nombre, campo_salida):
        import os
        plantilla_pdf = ruta_recurso(os.path.join("ui", "requerimiento", plantilla_relativa))
        if not os.path.exists(plantilla_pdf):
            QMessageBox.critical(self, "Plantilla no encontrada", "No se encontro la plantilla:\n" + str(plantilla_pdf))
            return
        carpeta = os.path.join(obtener_base_pdf(), "requerimientos", carpeta_relativa)
        salida_pdf = obtener_pdf_unico(carpeta, nombre_base)
        salida_btn.setEnabled(False)
        try:
            plantilla = PdfReader(plantilla_pdf)
            writer = PdfWriter()
            pagina_base = plantilla.pages[0]
            ancho = float(pagina_base.mediabox.width)
            alto = float(pagina_base.mediabox.height)
            packet = BytesIO()
            c = canvas.Canvas(packet, pagesize=(ancho, alto))
            for x, y, texto in campos_header:
                c.setFont("Helvetica-Bold", 9)
                c.drawString(x, y, texto)
            y = lineas_items["start_y"]
            c.setFont("Helvetica", 8)
            for fila in lineas_items["filas"]():
                for x, texto in fila:
                    c.drawString(x, y, texto)
                y -= lineas_items["step_y"]
            c.save()
            packet.seek(0)
            overlay = PdfReader(packet)
            for i in range(len(overlay.pages)):
                if i == 0:
                    pagina = plantilla.pages[0]
                    pagina.merge_page(overlay.pages[i])
                    writer.add_page(pagina)
                else:
                    writer.add_page(overlay.pages[i])
            with open(salida_pdf, "wb") as f:
                writer.write(f)
        except Exception as e:
            QMessageBox.critical(self, "Error al generar PDF", "No se pudo generar el PDF de " + dir_nombre + ":\n" + str(e))
            return
        finally:
            salida_btn.setEnabled(True)
        db.trabajos.update_one({"_id": self.trabajo_id}, {"$set": {campo_salida: salida_pdf}})
        QMessageBox.information(self, "PDF generado", dir_nombre + " generada correctamente:\n" + str(salida_pdf))



    def generar_hoja_salida_bodega(self):
        self.guardar()
        trabajo = db.trabajos.find_one(
            {"_id": self.trabajo_id},
            projection={"nombre": 1, "supervisor_nombre": 1, "chofer_nombre": 1, "carro_nombre": 1, "detalle": 1},
        )
        if not trabajo:
            QMessageBox.warning(self, "Trabajo no encontrado", "No se encontro el trabajo seleccionado en la base de datos.")
            return
        fecha = datetime.now().strftime("%Y-%m-%d")
        supervisor = trabajo.get("supervisor_nombre", "")
        chofer = trabajo.get("chofer_nombre", "")
        carro = trabajo.get("carro_nombre", "")
        if not supervisor:
            QMessageBox.warning(self, "Supervisor requerido", "Debe seleccionar un supervisor antes de generar la hoja de salida.")
            return
        if not chofer:
            QMessageBox.warning(self, "Conductor requerido", "Debe asignar un conductor antes de generar la hoja de salida.")
            return
        if not carro:
            QMessageBox.warning(self, "Transporte requerido", "Debe seleccionar un carro antes de generar la hoja de salida.")
            return
        recursos = [item for item in trabajo.get("detalle", []) if item.get("tipo") in ["herramienta", "maquina", "pvc", "consumible"]]
        if not recursos:
            QMessageBox.warning(self, "Sin recursos", "No hay herramientas, maquinas, PVC o consumibles agregados.")
            return
        if QMessageBox.question(self, "Confirmar generacion", "¿Deseas generar la hoja de salida de bodega?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self._generar_pdf_plantilla(
            plantilla_relativa="Hoja_de_Bodega.pdf",
            carpeta_relativa="salidas_bodega",
            nombre_base="Salida_bodega_" + str(self.trabajo_id) + "_" + str(fecha),
            campos_header=[
                # --- FILA SUPERIOR DE LA CABECERA (Y=555) ---
                # "Ingreso" (Fecha): Centrado en su casilla
                (135, 612, fecha),
                # "Responsable" (Supervisor)
                (255, 612, str(supervisor)[:30]),
                # "Destino" (Trabajo)
                (430, 622, trabajo.get("nombre", "")[:25]),
                
                # --- FILA MEDIAL (Y=528) ---
                # "Chofer"
                (430, 595, str(chofer)[:25]),
                
                # --- FILA INFERIOR DE CABECERA (Y=500) ---
                # "Placa de carro"
                (430, 570, str(carro)[:20]),
            ],
            lineas_items={
                # "start_y": Subido a 465 para que empiece exactamente abajo de las cabeceras naranjas
                "start_y": 465,
                "step_y": 20,
                "filas": lambda: [
                    [
                        (65, str(item.get("id", ""))[:15]),       # Columna "Item."
                        (160, str(item.get("cantidad", ""))),     # Columna "Cant."
                        (310, str(item.get("nombre", ""))[:45]),  # Columna "Descripción"
                    ] for item in recursos
                ],
            },
            salida_btn=self.btn_salida_bodega,
            dir_nombre="Hoja de salida de bodega",
            campo_salida="pdf_salida_bodega",
        )   


    def generar_informe_no_devueltos(self):
        self.guardar()
        trabajo = db.trabajos.find_one(
            {"_id": self.trabajo_id},
            projection={"nombre": 1, "supervisor_nombre": 1, "detalle": 1},
        )
        if not trabajo:
            QMessageBox.warning(self, "Trabajo no encontrado", "No se encontro el trabajo seleccionado en la base de datos.")
            return
        fecha = datetime.now().strftime("%Y-%m-%d")
        if not trabajo.get("supervisor_nombre", ""):
            QMessageBox.warning(self, "Supervisor requerido", "Debe seleccionar un supervisor antes de generar el informe.")
            return
        no_devueltos = []
        for item in trabajo.get("detalle", []):
            tipo = item.get("tipo")
            cantidad = int(item.get("cantidad", 0))
            usado = int(item.get("usado", 0))
            vuelto = int(item.get("vuelto", 0))
            devuelto = bool(item.get("devuelto", False))
            if tipo == "herramienta":
                f = cantidad - vuelto
                if f > 0:
                    no_devueltos.append({"tipo": tipo, "id": item.get("id", ""), "nombre": item.get("nombre", ""), "cantidad": f})
            elif tipo == "maquina":
                if not devuelto:
                    no_devueltos.append({"tipo": tipo, "id": item.get("id", ""), "nombre": item.get("nombre", ""), "cantidad": 1})
            elif tipo in ["pvc", "consumible"]:
                f = cantidad - usado - vuelto
                if f > 0:
                    no_devueltos.append({"tipo": tipo, "id": item.get("id", ""), "nombre": item.get("nombre", ""), "cantidad": f})
        if not no_devueltos:
            QMessageBox.information(self, "Sin items pendientes", "No hay items pendientes de devolucion.")
            return
        if QMessageBox.question(self, "Confirmar generacion", "¿Deseas generar el informe de items no devueltos?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self._generar_pdf_plantilla(
            plantilla_relativa="Informe.pdf",
            carpeta_relativa="informes_no_devueltos",
            nombre_base="No_devueltos_" + str(self.trabajo_id) + "_" + str(fecha),
            campos_header=[
                (150, 534, trabajo.get("nombre", "")[:45]),
                (90, 493, fecha),
            ],
            lineas_items={
                "start_y": 450,
                "step_y": 18,
                "filas": lambda: [
                    [
                        (45, str(item.get("tipo", ""))[:12]),
                        (125, str(item.get("id", ""))[:18]),
                        (240, str(item.get("nombre", ""))[:38]),
                        (500, str(item.get("cantidad", ""))),
                    ] for item in no_devueltos
                ],
            },
            salida_btn=self.btn_informe_no_devueltos,
            dir_nombre="Informe de items no devueltos",
            campo_salida="pdf_no_devueltos",
        )

    def cargar(self):
        self.table.setRowCount(0)
        self._cache_nombres_local = {}
        trabajo = db.trabajos.find_one({"_id": self.trabajo_id}, projection={"detalle": 1, "supervisor_id": 1})
        data = trabajo.get("detalle", []) if trabajo else []
        supervisor_id = trabajo.get("supervisor_id", "") if trabajo else ""
        for d in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            tipo = d.get("tipo", "")
            id_val = d.get("id", "")
            nombre = d.get("nombre", "")
            if tipo == "trabajador" and id_val == supervisor_id:
                nombre = nombre.replace(" [SUPERVISOR]", "") + " [SUPERVISOR]"
            self.table.setItem(row, 0, QTableWidgetItem(tipo))
            self.table.setItem(row, 1, QTableWidgetItem(id_val))
            self.table.setItem(row, 2, QTableWidgetItem(nombre))
            self.table.setItem(row, 3, QTableWidgetItem(str(d.get("cantidad", 0))))
            chk = QCheckBox()
            chk.setChecked(d.get("devuelto", False))
            self.table.setCellWidget(row, 4, chk)
            if tipo in ["consumible", "pvc"]:
                self.table.setCellWidget(row, 5, QLineEdit(str(d.get("usado", 0))))
                self.table.setCellWidget(row, 6, QLineEdit(str(d.get("vuelto", 0))))
            elif tipo == "herramienta":
                self.table.setCellWidget(row, 5, QLabel("-"))
                self.table.setCellWidget(row, 6, QLineEdit(str(d.get("vuelto", 0))))
            else:
                self.table.setCellWidget(row, 5, QLabel("-"))
                self.table.setCellWidget(row, 6, QLabel("-"))
        self.table.resizeColumnsToContents()
        self.actualizar_info_trabajo()


