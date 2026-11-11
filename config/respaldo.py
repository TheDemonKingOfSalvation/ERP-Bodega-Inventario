"""Respaldo automático de MongoDB.

Realiza un dump con mongodump y conserva los últimos N respaldos.
Pensado para correr en background al iniciar la aplicación una vez por día.
"""

import os
import shutil
import subprocess
import threading
import time
from datetime import datetime

_RESPALDO_DIR_NAME = "respaldos_mongo"
_LOCK = threading.Lock()
_HILO = None
_ULTIMO_RESUMEN = None


def _base_dir():
    from ui.utils import obtener_base_salida
    return obtener_base_salida()


def _carpeta_respaldos():
    ruta = os.path.join(_base_dir(), _RESPALDO_DIR_NAME)
    os.makedirs(ruta, exist_ok=True)
    return ruta


def _nombre_respaldo():
    return datetime.now().strftime("respaldo_%Y-%m-%d_%H-%M-%S")


def _config():
    uri, retencion, intervalo = "mongodb://localhost:27017/", 30, 24
    try:
        from config.config_manager import obtener_config_respaldo
        uri, retencion, intervalo = obtener_config_respaldo()
    except Exception:
        pass
    return uri, retencion, intervalo


def _binario_mongodump():
    candidatos = [
        shutil.which("mongodump"),
        r"C:\Program Files\MongoDB\Tools\100\bin\mongodump.exe",
        r"C:\Program Files\MongoDB\Tools\Server\5.0\bin\mongodump.exe",
        r"C:\Program Files\MongoDB\Server\7.0\bin\mongodump.exe",
        r"C:\Program Files\MongoDB\Server\6.0\bin\mongodump.exe",
        r"C:\Program Files\MongoDB\Server\5.0\bin\mongodump.exe",
    ]

    for ruta in candidatos:
        if ruta and os.path.exists(ruta):
            return ruta

    return None


def _purgar_antiguos(max_respaldos):
    """Conserva estrictamente los últimos N respaldos ordenados por nombre/fecha."""
    carpeta = _carpeta_respaldos()
    
    # Filtrar solo carpetas válidas de respaldo
    respaldos = [
        nombre for nombre in os.listdir(carpeta)
        if os.path.isdir(os.path.join(carpeta, nombre)) and nombre.startswith("respaldo_")
    ]
    
    # Al estar nombrados con formato YYYY-MM-DD, el orden alfabético coincide con el cronológico
    respaldos.sort()
    
    # Si excedemos el número máximo permitido, eliminamos los más antiguos
    while len(respaldos) > max_respaldos:
        antiguo = respaldos.pop(0)
        shutil.rmtree(os.path.join(carpeta, antiguo), ignore_errors=True)


def _ultimo_respaldo_fecha():
    carpeta = _carpeta_respaldos()
    fechas = []

    for nombre in os.listdir(carpeta):
        ruta = os.path.join(carpeta, nombre)
        if not (os.path.isdir(ruta) and nombre.startswith("respaldo_")):
            continue

        try:
            fechas.append(
                datetime.strptime(nombre, "respaldo_%Y-%m-%d_%H-%M-%S").date()
            )
        except ValueError:
            pass

    return max(fechas) if fechas else None


def _ejecutar_dump():
    binario = _binario_mongodump()
    if not binario:
        return False, "mongodump no encontrado."

    uri, retencion, _ = _config()
    carpeta = _carpeta_respaldos()
    destino = os.path.join(carpeta, _nombre_respaldo())

    os.makedirs(destino, exist_ok=True)

    try:
        resultado = subprocess.run(
            [binario, "--uri", uri, "--out", destino],
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return False, "Tiempo de espera agotado."
    except Exception as e:
        return False, str(e)

    if resultado.returncode != 0:
        return False, (resultado.stderr or resultado.stdout or "Error desconocido")

    # Purgar manteniendo los últimos N respaldos configurados
    _purgar_antiguos(retencion)

    return True, destino


def ejecutar_respaldo():
    global _ULTIMO_RESUMEN

    with _LOCK:
        ok, mensaje = _ejecutar_dump()

        _ULTIMO_RESUMEN = {
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "ok": ok,
            "mensaje": mensaje,
        }

        return ok, mensaje


def obtener_ultimo_resumen():
    return _ULTIMO_RESUMEN


def _loop_continuo():
    """Despierta periódicamente cada 15 minutos para verificar si corresponde respaldar."""
    global _ULTIMO_RESUMEN

    while True:
        try:
            # Comprobamos si hoy ya se cuenta con un respaldo exitoso
            if _ultimo_respaldo_fecha() != datetime.now().date():
                ejecutar_respaldo()
        except Exception as e:
            _ULTIMO_RESUMEN = {
                "fecha": datetime.now().isoformat(timespec="seconds"),
                "ok": False,
                "mensaje": f"Error en bucle: {e}",
            }
        
        # Dormir 15 minutos antes de volver a verificar la fecha
        time.sleep(15 * 60)


def iniciar_respaldo_automatico():
    """Inicia el hilo de respaldo sin bloquear la interfaz."""
    global _HILO

    with _LOCK:
        if _HILO and _HILO.is_alive():
            return _HILO

        _, retencion, _ = _config()
        _purgar_antiguos(retencion)

        # Ya no pasamos el intervalo como argumento ya que el bucle revisa inteligentemente por fecha
        _HILO = threading.Thread(
            target=_loop_continuo,
            daemon=True,
            name="RespaldoAutomatico"
        )
        _HILO.start()

        return _HILO