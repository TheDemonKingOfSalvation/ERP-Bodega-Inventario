from ui.pages.inventario_base import InventarioBasePage
from logic.logic_mongo import agregar_epp, editar_epp, eliminar_epp


class EppPage(InventarioBasePage):
    def __init__(self, navegar_callback=None):
        super().__init__("EPP", "epp", agregar_epp, editar_epp, eliminar_epp, navegar_callback=navegar_callback)
