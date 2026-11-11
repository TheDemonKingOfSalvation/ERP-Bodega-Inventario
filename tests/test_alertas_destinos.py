from ui.main_window import PAGINAS, construir_mapeo_destinos
from ui.pages.alertas import destino_reabastecimiento_para_tipo


def test_destino_reabastecimiento_para_tipo():
    assert destino_reabastecimiento_para_tipo("herramienta") == "herramientas"
    assert destino_reabastecimiento_para_tipo("epp") == "epp"
    assert destino_reabastecimiento_para_tipo("consumible") == "consumibles"
    assert destino_reabastecimiento_para_tipo("pvc") == "pvc"
    assert destino_reabastecimiento_para_tipo("desconocido") == "informe_reabastecimiento"


def test_mapeo_destinos_usa_la_ultima_coincidencia():
    mapeo = construir_mapeo_destinos(PAGINAS)
    assert mapeo["alertas"] == 1
    assert mapeo["herramientas"] == 3
    assert mapeo["consumibles"] == 5
