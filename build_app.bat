@echo off
echo ==========================================
echo      BUILDING PYOBD SUITE (2 APPS)
echo ==========================================

if exist ".venv\Scripts\activate.bat" (
    echo Activating Virtual Environment...
    call .venv\Scripts\activate.bat
) else (
    echo WARNING: .venv not found. Using global Python.
)

echo Checking dependencies...
pip install pyinstaller customtkinter obd pyserial matplotlib cryptography

REM 3. Clean up old builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

for /f "delims=" %%i in ('python -c "import customtkinter; print(customtkinter.__path__[0])"') do set CTK_PATH=%%i

echo.
echo ------------------------------------------
echo 1. BUILDING DASHBOARD (Standard User)
echo ------------------------------------------
pyinstaller --noconsole --onefile ^
    --name="PyOBD_Pro" ^
    --icon="app_icon.ico" ^
    --add-data "%CTK_PATH%;customtkinter/" ^
    --hidden-import "serial" ^
    --hidden-import "PIL._tkinter_finder" ^
    src/main.py

echo.
echo ------------------------------------------
echo 2. BUILDING CAN HACKER (Dev Tool)
echo ------------------------------------------
if exist "src/can_hacker.py" (
    pyinstaller --noconsole --onefile ^
        --name="PyCAN_Hacker" ^
        --icon="app_icon.ico" ^
        --add-data "%CTK_PATH%;customtkinter/" ^
        --hidden-import "serial" ^
        src/can_hacker.py
) else (
    echo Skipped CAN Hacker (Source file not found)
)

echo.
echo ==========================================
echo      ALL BUILDS COMPLETE!
echo ==========================================
echo Check 'dist' folder for your .exe files
pause