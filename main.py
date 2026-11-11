import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ui.main_window import MainWindow
from ui.theme import aplicar_tema
from config import respaldo

print("MAIN INICIADO")

# 1. Crear la aplicación Qt
app = QApplication(sys.argv)

# 2. Aplicar estilos y configuración
aplicar_tema(app)

# 3. Inicializar el respaldo automático
print('Iniciando respaldo automático (si aplica)')
respaldo.iniciar_respaldo_automatico()  # <-- Activado con éxito
print('Respaldo iniciado (thread o skip)')

# 4. Crear y mostrar la ventana principal
print('Creando MainWindow')
win = MainWindow()

print('Mostrando ventana')
win.show()

try:
    # Asegurar que la ventana aparezca activa y en primer plano al iniciar
    win.showNormal()
    win.raise_()
    win.activateWindow()
    win.setWindowState((win.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
    print('Ventana posicionada en primer plano')
except Exception as e:
    print('No se pudo forzar primer plano:', e)

print('Llamando app.exec()')
sys.exit(app.exec())