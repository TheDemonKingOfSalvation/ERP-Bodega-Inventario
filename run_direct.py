import sys
from PySide6.QtWidgets import QApplication
from ui.theme import aplicar_tema
from ui.main_window import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    aplicar_tema(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
