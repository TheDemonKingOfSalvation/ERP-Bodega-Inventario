# ERP Bodega Inventario

Aplicación de escritorio en Python y PySide6 para gestionar inventario de
máquinas, herramientas, EPP, consumibles y PVC, además de trabajos,
trabajadores, carros y proveedores. Utiliza MongoDB y genera documentos PDF.

## Requisitos

- Python 3.10 o posterior.
- MongoDB instalado y en ejecución, compatible con el sistema operativo.

## Instalación en Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements
cp config/config.example.ini config/config.ini
```

Edita `config/config.ini` para configurar MongoDB, el nombre de la empresa
y tu contraseña de administrador en `[admin]`. Sin contraseña configurada,
el modo administrador permanece deshabilitado. Este control es para el modo
administrador de la interfaz; no sustituye la autenticación de MongoDB.

```bash
python main.py
```

## Seguridad y datos locales

- No publiques `config/config.ini`, archivos `.env`, claves ni tokens.
- Las credenciales se configuran solo en archivos locales excluidos de Git.
- Los respaldos de MongoDB, documentos generados, entornos virtuales y
  ejecutables compilados no forman parte del repositorio.
- Usa credenciales propias y configura los permisos de MongoDB según tu entorno.
- La plantilla privada `ui/requerimiento/Hoja_de_Bodega.pdf` no se distribuye
  porque contiene datos personales. Para usar funciones que la requieren,
  coloca allí tu propia plantilla local.

## Pruebas

```bash
pip install pytest
python -m pytest
```
