from configparser import ConfigParser
from unittest.mock import patch

from ui.admin_state import _AdminState


def test_admin_usa_credenciales_de_configuracion():
    cfg = ConfigParser()
    cfg.read_dict({"admin": {"usuario": "operador_prueba", "password": "solo-para-test"}})
    with patch("ui.admin_state.cargar_config", return_value=cfg):
        estado = _AdminState()
        assert estado.activar("operador_prueba", "solo-para-test")
        assert estado.is_admin()


def test_admin_sin_password_configurado_no_permite_entrada():
    cfg = ConfigParser()
    cfg.read_dict({"admin": {"usuario": "admin", "password": ""}})
    with patch("ui.admin_state.cargar_config", return_value=cfg):
        estado = _AdminState()
        assert not estado.activar("admin", "")
        assert not estado.is_admin()
