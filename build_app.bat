@echo off
setlocal enabledelayedexpansion

:: Force the script to run from the project folder
cd /d "%~dp0"

echo ==========================================
echo      BUILDING PYOBD SUITE (2 APPS)
echo ==========================================

:: 1. Virtual Environment Check
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating Virtual Environment...
    call .venv\Scripts\activate.bat
)

:: 2. Dependencies
echo [INFO] Checking dependencies...
pip install pyinstaller customtkinter obd pyserial matplotlib cryptography pillow

:: 3. Clean up
echo [INFO] Cleaning workspace...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

:: Get CustomTkinter path
for /f "delims=" %%i in ('python -c "import customtkinter; print(customtkinter.__path__[0])"') do set CTK_PATH=%%i

echo.
echo ------------------------------------------
echo 1. BUILDING DASHBOARD (PyOBD_Pro)
echo ------------------------------------------
pyinstaller --noconsole --onefile ^
    --name="PyOBD_Pro" ^
    --icon="app_icon.ico" ^
    --add-data "%CTK_PATH%;customtkinter/" ^
    --add-data "data;data" ^
    --collect-all matplotlib ^
    --hidden-import "serial" ^
    --hidden-import "PIL._tkinter_finder" ^
    src/main.py

echo.
echo ------------------------------------------
echo 2. BUILDING CAN SNIFFER (PyCAN_Hacker)
echo ------------------------------------------
:: Using the correct filename found in your src directory: sniffer_main.py
if exist "src/sniffer_main.py" (
    pyinstaller --noconsole --onefile ^
        --name="PyCAN_Hacker" ^
        --icon="app_icon.ico" ^
        --add-data "%CTK_PATH%;customtkinter/" ^
        --hidden-import "serial" ^
        src/sniffer_main.py
) else (
    echo [ERROR] Expected src/sniffer_main.py not found!
)

echo.
echo ==========================================
echo      ALL BUILDS COMPLETE
echo ==========================================
echo Check the 'dist' folder for your files.
pause