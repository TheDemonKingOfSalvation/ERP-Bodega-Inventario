"""Registro estático de módulos de páginas.

Este archivo importa explícitamente los módulos de ui.pages para que herramientas de
congelado (PyInstaller, Nuitka, etc.) detecten las dependencias incluso cuando el
código usa import dinámico (importlib.import_module).

No cambiar la API: exporta import_page(mod_name) que devuelve el módulo correspondiente
cuando se le pasa una cadena como "ui.pages.dashboard".
"""

# Importar explícito de los módulos de la carpeta ui/pages
from ui.pages import (
    dashboard,
    alertas,
    maquinas,
    herramientas,
    epp,
    consumibles,
    pvc,
    trabajos,
    trabajadores,
    carros,
    proveedor,
    inventario_base,
    informe_reabastecimiento_page,
    informe_mantenimiento_maquinas_page,
    requerimiento_mantenimiento_page,
    requerimiento_reabastecimiento_page,
    trabajo_detalle,
    trabajador_epp_informe,
    trabajador_epp_agregar,
)

# Mapeo nombre de paquete -> módulo importado
PAGES = {
    "ui.pages.dashboard": dashboard,
    "ui.pages.alertas": alertas,
    "ui.pages.maquinas": maquinas,
    "ui.pages.herramientas": herramientas,
    "ui.pages.epp": epp,
    "ui.pages.consumibles": consumibles,
    "ui.pages.pvc": pvc,
    "ui.pages.trabajos": trabajos,
    "ui.pages.trabajadores": trabajadores,
    "ui.pages.carros": carros,
    "ui.pages.proveedor": proveedor,
    "ui.pages.inventario_base": inventario_base,
    "ui.pages.informe_reabastecimiento_page": informe_reabastecimiento_page,
    "ui.pages.informe_mantenimiento_maquinas_page": informe_mantenimiento_maquinas_page,
    "ui.pages.requerimiento_mantenimiento_page": requerimiento_mantenimiento_page,
    "ui.pages.requerimiento_reabastecimiento_page": requerimiento_reabastecimiento_page,
    "ui.pages.trabajo_detalle": trabajo_detalle,
    "ui.pages.trabajador_epp_informe": trabajador_epp_informe,
    "ui.pages.trabajador_epp_agregar": trabajador_epp_agregar,
}


def import_page(mod_name: str):
    """Devuelve el módulo correspondiente al nombre completo de paquete.

    Lanza ModuleNotFoundError si no existe el módulo en el registro para mantener
    compatibilidad con el comportamiento estándar de importlib.import_module.
    """
    try:
        return PAGES[mod_name]
    except KeyError:
        raise ModuleNotFoundError(f"No se encuentra el módulo en el registro: {mod_name}")
