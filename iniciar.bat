@echo off
title Sistema Docentes IA - Iniciador
echo ========================================================
echo   Iniciando Sistema de Evaluacion Docente con IA
echo ========================================================
echo.

:: Verificar que Python este instalado
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo Por favor instala Python 3.9+ e intentalo de nuevo.
    pause
    exit /b
)

:: Verificar que Node este instalado
node --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js no esta instalado o no esta en el PATH.
    echo Por favor instala Node.js e intentalo de nuevo.
    pause
    exit /b
)

:: Verificar que el archivo .env exista
IF NOT EXIST "backend\.env" (
    echo [ERROR] No se encontro el archivo backend\.env
    echo Copiando backend\.env.example a backend\.env...
    copy backend\.env.example backend\.env
    echo.
    echo [ATENCION] Abre la carpeta 'backend', edita el archivo '.env' 
    echo y asegurate de poner tu clave GEMINI_API_KEY.
    echo Luego de poner la clave, vuelve a ejecutar este script.
    pause
    exit /b
)

echo [1/3] Preparando el Backend (Python/FastAPI)...
cd backend
IF NOT EXIST "venv\" (
    echo Creando entorno virtual...
    python -m venv venv
)
call venv\Scripts\activate
echo Instalando dependencias del backend...
pip install -r requirements.txt >nul
cd ..

echo [2/3] Preparando el Frontend (React/Vite)...
cd frontend
echo Instalando dependencias del frontend...
call npm install >nul
cd ..

echo.
echo [3/3] Iniciando Servidores...
echo.
echo - El BACKEND correra en la ventana minimizada.
echo - El FRONTEND se abrira en tu navegador por defecto.
echo.

:: Iniciar Backend en una nueva ventana minimizada
start /min cmd /c "cd backend && call venv\Scripts\activate && uvicorn main:app --reload"

:: Iniciar Frontend y abrir el navegador
cd frontend
echo Arrancando interfaz visual...
call npm run dev -- --open

pause
