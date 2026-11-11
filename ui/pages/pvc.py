from ui.pages.inventario_base import InventarioBasePage
from logic.logic_mongo import agregar_pvc as _agregar_pvc, editar_pvc as _editar_pvc, eliminar_pvc


def agregar_pvc_wrap(id_val, nombre, cantidad, stock_minimo=3, tipo="roscable"):
    return _agregar_pvc(id_val, nombre, cantidad, tipo, stock_minimo)


def editar_pvc_wrap(id_val, nombre, cantidad, stock_minimo=3, tipo="roscable"):
    return _editar_pvc(id_val, nombre, cantidad, tipo, stock_minimo)


class PvcPage(InventarioBasePage):
    def __init__(self, navegar_callback=None):
        super().__init__(
            "PVC",
            "pvc",
            agregar_pvc_wrap,
            editar_pvc_wrap,
            eliminar_pvc,
            campos_extra=[{"name": "tipo", "label": "Tipo", "type": "combo", "items": ["roscable", "pegable"]}],
            navegar_callback=navegar_callback,
        )
