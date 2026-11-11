"""Helpers compartidos por todas las paginas."""
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox


# =========================================================
# RUTAS (desarrollo vs ejecutable PyInstaller)
# =========================================================

def ruta_recurso(ruta_relativa):
    """Resuelve una ruta tanto en desarrollo como empaquetada."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, ruta_relativa)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_dir, ruta_relativa)


def obtener_base_salida():
    """Carpeta base local donde se crean los PDFs generados cuando no hay compartida."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if exe_dir.parent.name.lower() == "dist":
            return str(exe_dir.parent.parent)
        if exe_dir.name.lower() == "dist":
            return str(exe_dir.parent)
        return str(exe_dir)
    return str(Path(__file__).resolve().parent.parent)


def obtener_base_pdf():
    """Carpeta base para guardar PDFs. Si hay carpeta compartida configurada la usa."""
    try:
        from config.config_manager import obtener_base_dir
        return obtener_base_dir()
    except Exception:
        return obtener_base_salida()


def normalizar_ruta_relativa(ruta):
    """Convierte una ruta absoluta en relativa a la base de PDFs (si esta dentro).

    Si la ruta no esta dentro de la base, la deja como esta (compatibilidad).
    """
    if not ruta:
        return ruta
    try:
        base = obtener_base_pdf()
        rel = os.path.relpath(ruta, base)
        if not rel.startswith(".."):
            return rel.replace("\\", "/")
    except Exception:
        return ruta
    return ruta


def resolver_ruta_relativa(ruta):
    """Si la ruta es relativa, la resuelve contra la base de PDFs configurada."""
    if not ruta:
        return ruta
    if os.path.isabs(ruta):
        return ruta
    return os.path.join(obtener_base_pdf(), ruta)


# =========================================================
# NOMBRES DE ARCHIVO
# =========================================================

_CARACTERES_INVALIDOS = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '#']


def limpiar_nombre_archivo(texto):
    texto_limpio = str(texto or "").strip()
    for caracter in _CARACTERES_INVALIDOS:
        texto_limpio = texto_limpio.replace(caracter, "-")
    return texto_limpio.replace(" ", "_")


def obtener_pdf_unico(carpeta, nombre_base):
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, nombre_base + ".pdf")
    if not os.path.exists(ruta):
        return ruta
    contador = 2
    while True:
        ruta = os.path.join(carpeta, f"{nombre_base}.{contador}.pdf")
        if not os.path.exists(ruta):
            return ruta
        contador += 1


# =========================================================
# APERTURA DE ARCHIVOS
# =========================================================

def abrir_archivo(ruta, parent=None):
    ruta_resuelta = resolver_ruta_relativa(ruta)
    ruta_resuelta = str(ruta_resuelta or "").strip()
    if not ruta_resuelta or not os.path.exists(ruta_resuelta):
        QMessageBox.warning(
            parent,
            "Archivo no encontrado",
            "No se encontro el archivo asociado al registro seleccionado.\n\n"
            "Verifica la ruta en la configuracion (config.ini -> storage).",
        )
        return
    try:
        if sys.platform.startswith("win"):
            os.startfile(ruta_resuelta)
        elif sys.platform == "darwin":
            subprocess.call(["open", ruta_resuelta])
        else:
            subprocess.call(["xdg-open", ruta_resuelta])
    except Exception as e:
        QMessageBox.warning(
            parent,
            "No se pudo abrir el archivo",
            f"No se pudo abrir el archivo:\n{e}",
        )


# =========================================================
# COLECCIONES POR TIPO
# =========================================================

COLECCION_POR_TIPO = {
    "trabajador": "trabajadores",
    "herramienta": "herramientas",
    "maquina": "maquinas",
    "consumible": "consumibles",
    "pvc": "pvc",
    "epp": "epp",
    "carro": "carros",
    "proveedor": "proveedores",
}


def coleccion_por_tipo(tipo):
    if tipo == "carro":
        return "carros"
    return COLECCION_POR_TIPO[tipo]


# =========================================================
# MODO ADMIN
# =========================================================

def aplicar_modo_admin(botones, admin_activo, tooltips=None):
    """Habilita/deshabilita un grupo de botones segun el modo administrador."""
    tooltips = tooltips or {}
    for nombre, boton in botones.items():
        solo_admin = nombre.startswith("admin_")
        habilitado = admin_activo if solo_admin else True
        boton.setEnabled(habilitado)
        if admin_activo:
            boton.setToolTip("")
        else:
            boton.setToolTip(tooltips.get(nombre, "Solo el administrador puede realizar esta accion."))


# =========================================================
# DEBOUNCE PARA BUSQUEDAS
# =========================================================

class BusquedaConDebounce:
    """Conecta un QLineEdit a un callable y espera un tiempo quieto antes de ejecutarlo."""

    def __init__(self, line_edit, callback, demora_ms=250):
        self.callback = callback
        self.timer = QTimer(line_edit)
        self.timer.setSingleShot(True)
        self.timer.setInterval(demora_ms)
        self.timer.timeout.connect(self._disparar)
        line_edit.textChanged.connect(self.timer.start)

    def _disparar(self):
        self.callback()

    def disparar_ahora(self):
        self.timer.stop()
        self.callback()

