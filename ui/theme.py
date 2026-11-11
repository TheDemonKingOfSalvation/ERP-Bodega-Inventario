"""Tema visual de la aplicacion SOLMET GE&TO."""
from PySide6.QtGui import QIcon
import os

from ui.utils import ruta_recurso


# =========================
# COLORES SOLMET GE&TO
# =========================

COLOR_FONDO = "#151819"
COLOR_PANEL = "#202426"
COLOR_PANEL_2 = "#252A2D"
COLOR_BORDE = "#343A40"

COLOR_TEXTO = "#F2F2F2"
COLOR_TEXTO_SECUNDARIO = "#BFC4C8"
COLOR_TEXTO_APAGADO = "#7D858B"

COLOR_ACENTO = "#D6C83A"
COLOR_ACENTO_HOVER = "#E8D94C"
COLOR_ACENTO_OSCURO = "#9E932B"

COLOR_VERDE = "#2F6B4F"
COLOR_VERDE_HOVER = "#3C805F"

COLOR_AZUL_GRIS = "#26334A"
COLOR_ERROR = "#C74B4B"


def obtener_estilo_global():
    return f"""
    QMainWindow {{
        background-color: {COLOR_FONDO};
    }}

    QWidget {{
        background-color: {COLOR_FONDO};
        color: {COLOR_TEXTO};
        font-family: Segoe UI;
        font-size: 14px;
    }}

    QLabel {{
        color: {COLOR_TEXTO};
        background: transparent;
    }}

    QLabel#tituloPagina {{
        color: {COLOR_TEXTO};
        font-size: 26px;
        font-weight: 700;
        padding: 8px 0px;
    }}

    QLabel#subtitulo {{
        color: {COLOR_TEXTO_SECUNDARIO};
        font-size: 14px;
    }}

    QLabel#estadoOk {{
        color: {COLOR_ACENTO};
        font-weight: 600;
    }}

    QLabel#estadoError {{
        color: {COLOR_ERROR};
        font-weight: 600;
    }}

    QLineEdit, QSpinBox, QComboBox, QDateEdit, QTextEdit {{
        background-color: {COLOR_PANEL};
        color: {COLOR_TEXTO};
        border: 1px solid {COLOR_BORDE};
        border-radius: 8px;
        padding: 8px 10px;
        selection-background-color: {COLOR_ACENTO_OSCURO};
    }}

    QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {{
        border: 1px solid {COLOR_ACENTO};
        background-color: {COLOR_PANEL_2};
    }}

    QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{
        background-color: #1B1F21;
        color: {COLOR_TEXTO_APAGADO};
        border: 1px solid #2A2F32;
    }}

    QPushButton {{
        background-color: {COLOR_VERDE};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 9px 14px;
        font-weight: 600;
    }}

    QPushButton:hover {{
        background-color: {COLOR_VERDE_HOVER};
    }}

    QPushButton:pressed {{
        background-color: {COLOR_ACENTO_OSCURO};
    }}

    QPushButton:disabled {{
        background-color: #2B3033;
        color: {COLOR_TEXTO_APAGADO};
    }}

    QPushButton#botonPrincipal {{
        background-color: {COLOR_ACENTO};
        color: #151819;
        font-weight: 700;
    }}

    QPushButton#botonPrincipal:hover {{
        background-color: {COLOR_ACENTO_HOVER};
    }}

    QPushButton#botonPeligro {{
        background-color: #8F3D3D;
        color: white;
    }}

    QPushButton#botonPeligro:hover {{
        background-color: {COLOR_ERROR};
    }}

    QPushButton#botonMenu {{
        background-color: transparent;
        color: {COLOR_TEXTO_SECUNDARIO};
        border-radius: 8px;
        padding: 12px 14px;
        text-align: left;
        font-size: 14px;
        font-weight: 600;
    }}

    QPushButton#botonMenu:hover {{
        background-color: {COLOR_PANEL_2};
        color: {COLOR_TEXTO};
    }}

    QPushButton#botonMenuActivo {{
        background-color: {COLOR_ACENTO};
        color: #151819;
        border-radius: 8px;
        padding: 12px 14px;
        text-align: left;
        font-size: 14px;
        font-weight: 700;
    }}

    QTableWidget {{
        background-color: {COLOR_PANEL};
        alternate-background-color: #1B1F21;
        color: {COLOR_TEXTO};
        gridline-color: {COLOR_BORDE};
        border: 1px solid {COLOR_BORDE};
        border-radius: 10px;
        selection-background-color: {COLOR_AZUL_GRIS};
        selection-color: {COLOR_TEXTO};
    }}

    QTableWidget::item {{
        padding: 0px;
        border-bottom: 1px solid #2A2F32;
    }}

    QTableWidget::item:selected {{
        background-color: {COLOR_AZUL_GRIS};
        color: white;
    }}

    QHeaderView::section {{
        background-color: #111415;
        color: {COLOR_ACENTO};
        padding: 9px;
        border: none;
        border-right: 1px solid {COLOR_BORDE};
        font-weight: 700;
    }}

    QScrollBar:vertical {{
        background-color: {COLOR_FONDO};
        width: 12px;
        margin: 0px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {COLOR_BORDE};
        border-radius: 6px;
        min-height: 25px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {COLOR_ACENTO_OSCURO};
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: {COLOR_FONDO};
        height: 12px;
        margin: 0px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {COLOR_BORDE};
        border-radius: 6px;
        min-width: 25px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {COLOR_ACENTO_OSCURO};
    }}

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    QFrame#tarjeta {{
        background-color: {COLOR_PANEL};
        border: 1px solid {COLOR_BORDE};
        border-radius: 14px;
    }}

    QLabel#tarjetaTitulo {{
        color: {COLOR_TEXTO_SECUNDARIO};
        font-size: 13px;
        font-weight: 600;
    }}

    QLabel#tarjetaNumero {{
        color: {COLOR_ACENTO};
        font-size: 28px;
        font-weight: 800;
    }}

    QMessageBox {{
        background-color: {COLOR_FONDO};
    }}

    QMessageBox QLabel {{
        color: {COLOR_TEXTO};
    }}

    QInputDialog {{
        background-color: {COLOR_FONDO};
    }}
    """


def aplicar_tema(app):
    app.setStyleSheet(obtener_estilo_global())

    icono = ruta_recurso(os.path.join("ui", "assets", "solmet_icon.ico"))
    logo_png = ruta_recurso(os.path.join("ui", "assets", "solmet_logo.png"))
    logo_jpg = ruta_recurso(os.path.join("ui", "assets", "solmet_logo.jpg"))

    if os.path.exists(icono):
        app.setWindowIcon(QIcon(icono))
    elif os.path.exists(logo_png):
        app.setWindowIcon(QIcon(logo_png))
    elif os.path.exists(logo_jpg):
        app.setWindowIcon(QIcon(logo_jpg))
