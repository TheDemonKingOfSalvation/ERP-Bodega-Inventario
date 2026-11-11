@echo off
echo ================================
echo Limpiando compilacion anterior...
echo ================================

rmdir /s /q build
rmdir /s /q dist

echo.
echo ================================
echo Compilando sistema...
echo ================================

python -m PyInstaller --onedir main.py ^
--add-data "ui/requerimiento;ui/requerimiento" ^
--add-data "ui/assets;ui/assets" ^
--icon "ui/assets/solmet_icon.ico" ^
--noconsole

echo.
echo ================================
echo Compilacion terminada.
echo Abre el programa desde dist\main\main.exe
echo ================================

pause