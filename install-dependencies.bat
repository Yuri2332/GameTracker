@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher nao encontrado. Instale Python 3.11 ou superior.
  exit /b 1
)
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js nao encontrado. Instale Node.js 20 ou superior.
  exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
  echo npm nao encontrado. Reinstale Node.js com npm.
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Criando ambiente Python...
  py -3 -m venv .venv
  if errorlevel 1 goto :failed
)

echo Instalando dependencias do backend...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
if errorlevel 1 goto :failed

if not exist ".env" (
  echo Criando .env a partir de .env.example...
  copy /y .env.example .env >nul
  if errorlevel 1 goto :failed
)

echo Instalando dependencias do frontend com npm ci...
pushd frontend
call npm ci
if errorlevel 1 (
  popd
  goto :failed
)
popd

echo Aplicando migracoes do banco...
".venv\Scripts\alembic.exe" -c backend\alembic.ini upgrade head
if errorlevel 1 goto :failed

echo.
echo Instalacao concluida.
echo Para iniciar, execute start-gametracker.bat.
echo Edite .env antes de publicar o projeto.
exit /b 0

:failed
echo.
echo A instalacao falhou. Confira a mensagem acima e tente novamente.
exit /b 1
