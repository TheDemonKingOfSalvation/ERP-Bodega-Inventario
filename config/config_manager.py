"""Carga y guarda la configuracion del aplicativo (config.ini)."""
from __future__ import annotations

import os
import shutil
from configparser import ConfigParser


_PLANTILLA_INI = """[DEFAULT]

[admin]
usuario = admin
password =

[mongo]
uri = mongodb://localhost:27017/
base = inventario

[storage]
modo = local
ruta =

[empresa]
; Nombre que se muestra en la cabecera de los PDFs de requerimientos.
nombre = Solmet Industrial

[respaldo]
uri =
retencion_dias = 30
intervalo_horas = 24
"""


def _ruta_config():
    from ui.utils import ruta_recurso
    return ruta_recurso("config/config.ini")


def existe_config():
    return os.path.exists(_ruta_config())


def crear_config_si_no_existe():
    if existe_config():
        return _ruta_config()
    ruta = _ruta_config()
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(_PLANTILLA_INI)
    return ruta


def cargar_config():
    crear_config_si_no_existe()
    parser = ConfigParser()
    parser.read(_ruta_config(), encoding="utf-8")
    return parser


def obtener_mongo_uri():
    cfg = cargar_config()
    return cfg.get("mongo", "uri", fallback="mongodb://localhost:27017/").strip() or "mongodb://localhost:27017/"


def obtener_mongo_base():
    cfg = cargar_config()
    return cfg.get("mongo", "base", fallback="inventario").strip() or "inventario"


def obtener_base_dir():
    """Carpeta base donde se guardan los PDFs generados.

    Si `storage.modo = local` o `storage.ruta` esta vacia, usa la carpeta del ejecutable.
    Si `storage.modo = compartida`, usa la ruta indicada (idealmente una carpeta de red).
    """
    cfg = cargar_config()
    modo = cfg.get("storage", "modo", fallback="local").strip().lower()
    ruta = cfg.get("storage", "ruta", fallback="").strip()

    if modo == "compartida" and ruta:
        os.makedirs(ruta, exist_ok=True)
        return ruta
    
    # Resuelve base local sin importar ui.utils para evitar circular imports
    from pathlib import Path
    import sys
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if exe_dir.parent.name.lower() == "dist":
            return str(exe_dir.parent.parent)
        if exe_dir.name.lower() == "dist":
            return str(exe_dir.parent)
        return str(exe_dir)
    return str(Path(__file__).resolve().parent.parent)


def obtener_nombre_empresa():
    """Nombre comercial mostrado en la cabecera de los PDFs de requerimientos."""
    try:
        cfg = cargar_config()
    except Exception:
        return "Solmet Industrial"
    return cfg.get("empresa", "nombre", fallback="Solmet Industrial").strip() or "Solmet Industrial"


def obtener_config_respaldo():
    cfg = cargar_config()
    uri = cfg.get("respaldo", "uri", fallback="").strip()
    if not uri:
        uri = obtener_mongo_uri()
    try:
        retencion = int(cfg.get("respaldo", "retencion_dias", fallback="30"))
    except (TypeError, ValueError):
        retencion = 30
    try:
        intervalo = int(cfg.get("respaldo", "intervalo_horas", fallback="24"))
    except (TypeError, ValueError):
        intervalo = 24
    return uri, retencion, intervalo

