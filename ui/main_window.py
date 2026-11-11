"""Ventana principal con carga perezosa de paginas.

Cada pagina se construye solo la primera vez que se muestra. Esto evita
que el sistema ejecute 10+ consultas a MongoDB antes de mostrar la ventana.
"""
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QStackedWidget


# Cada entrada: (titulo, modulo, clase, destino, solo_admin, acepta_navegar).
# - destino: nombre logico para que las alertas naveguen.
# - solo_admin: True si solo se muestra cuando admin esta activo.
# - acepta_navegar: True si la pagina recibe un navegar_callback en su constructor.
PAGINAS = [
    ("Dashboard",        "ui.pages.dashboard",                            "DashboardPage",            "alertas",                  False, True),
    ("Alertas",          "ui.pages.alertas",                              "AlertasPage",              "alertas",                  True,  True),
    ("Maquinas",         "ui.pages.maquinas",                             "MaquinasPage",             "informe_mantenimiento",    False, True),
    ("Herramientas",     "ui.pages.herramientas",                         "HerramientasPage",         "herramientas",             False, True),
    ("EPP",              "ui.pages.epp",                                  "EppPage",                  "epp",                      False, True),
    ("Consumibles",      "ui.pages.consumibles",                          "ConsumiblesPage",          "consumibles",              False, True),
    ("PVC",              "ui.pages.pvc",                                  "PvcPage",                  "pvc",                      False, True),
    ("Trabajos",         "ui.pages.trabajos",                             "TrabajosPage",             "trabajos",                 False, True),
    ("Trabajadores",     "ui.pages.trabajadores",                         "TrabajadoresPage",         "trabajadores",             False, True),
    ("Carros",           "ui.pages.carros",                               "CarrosPage",               "carros",                   False, True),
    ("Proveedores",      "ui.pages.proveedor",                            "ProveedorPage",            "proveedores",              False, True),
]


def construir_mapeo_destinos(paginas):
    mapeo = {}
    for index, (_, _, _, destino, _, _) in enumerate(paginas):
        if destino:
            mapeo[destino] = index
    return mapeo


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ERP Inventario MongoDB")
        self.resize(1200, 700)

        main = QWidget()
        self.setCentralWidget(main)

        layout = QHBoxLayout(main)
        self.sidebar = QVBoxLayout()
        self.stack = QStackedWidget()

        self.pages = [None] * len(PAGINAS)
        self.page_factories = []
        self.buttons = []
        self.button_destinos = construir_mapeo_destinos(PAGINAS)
        self.indice_alertas = None

        from ui.admin_state import admin_state
        self._admin_state = admin_state

        for index, (titulo, modulo, clase, destino, solo_admin, acepta_navegar) in enumerate(PAGINAS):
            btn = QPushButton(titulo)
            btn.clicked.connect(lambda _, x=index: self.cambiar_pagina(x))
            if solo_admin:
                self.indice_alertas = index
                btn.setVisible(False)
            self.sidebar.addWidget(btn)
            self.stack.addWidget(QWidget())
            self.buttons.append(btn)
            self.page_factories.append((modulo, clase, solo_admin, acepta_navegar))

        self.sidebar.addStretch()
        layout.addLayout(self.sidebar, 1)
        layout.addWidget(self.stack, 4)

        self._admin_state.changed.connect(self._actualizar_visibilidad_admin)
        self._actualizar_visibilidad_admin(self._admin_state.is_admin())

        self.cambiar_pagina(0)

    def _actualizar_visibilidad_admin(self, activo):
        if self.indice_alertas is None:
            return
        btn = self.buttons[self.indice_alertas]
        btn.setVisible(activo)

    def _cargar_pagina(self, index):
        if self.pages[index] is not None:
            return self.pages[index]
        _, _, solo_admin, acepta_navegar = self.page_factories[index]
        if solo_admin and not self._admin_state.is_admin():
            return None
        modulo, clase, _, _ = self.page_factories[index]
        import importlib
        try:
            modulo_obj = importlib.import_module(modulo)
        except ModuleNotFoundError:
            # Cuando se empaqueta con PyInstaller u otro congelador, las importaciones
            # dinámicas pueden no detectarse. Usar un registro estático que importa
            # explícitamente los módulos para que el congelador los incluya.
            from ui.page_registry import import_page
            modulo_obj = import_page(modulo)
        if acepta_navegar:
            pagina = getattr(modulo_obj, clase)(navegar_callback=self._navegar_a_destino)
        else:
            pagina = getattr(modulo_obj, clase)()
        placeholder = self.stack.widget(index)
        self.stack.removeWidget(placeholder)
        placeholder.deleteLater()
        self.stack.insertWidget(index, pagina)
        self.pages[index] = pagina
        return pagina

    def cambiar_pagina(self, index):
        _, _, solo_admin, _ = self.page_factories[index]
        if solo_admin and not self._admin_state.is_admin():
            return
        pagina = self._cargar_pagina(index)
        if pagina is None:
            return
        self.stack.setCurrentWidget(pagina)
        if hasattr(pagina, "cargar"):
            pagina.cargar()

    def _navegar_a_destino(self, destino):
        if destino not in self.button_destinos:
            return
        self.cambiar_pagina(self.button_destinos[destino])
