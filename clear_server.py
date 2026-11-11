import sys
try:
    from PySide6.QtNetwork import QLocalServer
except Exception as e:
    print('PySide6 import error:', e)
    sys.exit(1)

APP_ID = "ERP_INVENTARIO_MONGO_UNICA_INSTANCIA"
try:
    QLocalServer.removeServer(APP_ID)
    print('Removed QLocalServer:', APP_ID)
except Exception as e:
    print('Error removing server:', e)
    sys.exit(1)
