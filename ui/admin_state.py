from PySide6.QtCore import QObject, Signal
from config.config_manager import cargar_config


ADMIN_USUARIO = "admin"


class _AdminState(QObject):
    changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self._activo = False

    def is_admin(self):
        return self._activo

    def activar(self, usuario, password):
        cfg = cargar_config()
        usuario_configurado = cfg.get("admin", "usuario", fallback=ADMIN_USUARIO)
        password_configurado = cfg.get("admin", "password", fallback="", raw=True)
        if password_configurado and usuario == usuario_configurado and password == password_configurado:
            self._activo = True
            self.changed.emit(True)
            return True
        return False

    def desactivar(self):
        self._activo = False
        self.changed.emit(False)


admin_state = _AdminState()
