from ui.pages.inventario_base import InventarioBasePage
from logic.logic_mongo import agregar_consumible, editar_consumible, eliminar_consumible


class ConsumiblesPage(InventarioBasePage):
    def __init__(self, navegar_callback=None):
        super().__init__("Consumibles", "consumibles", agregar_consumible, editar_consumible, eliminar_consumible, navegar_callback=navegar_callback)
