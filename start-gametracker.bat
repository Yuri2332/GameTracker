@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Ambiente Python ausente. Execute install-dependencies.bat primeiro.
  exit /b 1
)
if not exist "frontend\node_modules" (
  echo Dependencias do frontend ausentes. Execute install-dependencies.bat primeiro.
  exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
  echo npm nao encontrado. Instale Node.js 20 ou superior.
  exit /b 1
)

if not exist ".env" (
  copy /y .env.example .env >nul
  if errorlevel 1 exit /b 1
)

echo Aplicando migracoes do banco...
".venv\Scripts\alembic.exe" -c backend\alembic.ini upgrade head
if errorlevel 1 (
  echo Falha ao preparar o banco. Confira .env e execute install-dependencies.bat.
  exit /b 1
)

echo Abrindo API e frontend em janelas separadas...
start "GameTracker API" /D "%~dp0" "%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
start "GameTracker Web" /D "%~dp0frontend" cmd /k "npm run dev -- --host 127.0.0.1"
timeout /t 2 /nobreak >nul
start "" "http://localhost:5173"
echo GameTracker: http://localhost:5173
echo API / OpenAPI: http://localhost:8000/docs
echo Feche as janelas GameTracker API e GameTracker Web para parar os servicos.
exit /b 0
