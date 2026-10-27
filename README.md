# GameTracker

Central pessoal para biblioteca, sessões, metas e atividade de jogos. O MVP usa React/Vite no frontend e FastAPI/SQLAlchemy no backend; a aplicação funciona sem integrações externas.

## Estrutura

```text
backend/
  app/              API, modelos, validação, autenticação e serviços
  alembic/          migrações versionadas
  tests/            testes de API e regras de negócio
frontend/
  src/              páginas, componentes, cliente HTTP e estilos
```

## Requisitos

- Python 3.11 ou superior (3.13 também funciona)
- Node.js 20 ou superior e npm

## Windows

Atalho recomendado:

```bat
install-dependencies.bat
start-gametracker.bat
```

O primeiro script cria `.venv`, instala backend e frontend, cria `.env` e aplica as migrações. O segundo abre API e frontend em janelas separadas e abre o navegador. Feche as janelas dos serviços para interrompê-los.

Instalação manual:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
alembic -c backend\alembic.ini upgrade head
uvicorn app.main:app --app-dir backend --reload
```

Em outro terminal:

```powershell
cd frontend
npm install
npm run dev
```

## Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
cp .env.example .env
alembic -c backend/alembic.ini upgrade head
uvicorn app.main:app --app-dir backend --reload
```

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend: <http://localhost:5173>. API e OpenAPI: <http://localhost:8000/docs>.

## Configuração

Edite `.env` antes de publicar. `SECRET_KEY` precisa ser uma chave aleatória longa. SQLite é o padrão local. Para PostgreSQL, configure `DATABASE_URL` com um driver async compatível, por exemplo `postgresql+psycopg://...` (a API usa engine síncrona; use `postgresql+psycopg2://...` e instale o driver correspondente) ou `postgresql://...`.

`COOKIE_SECURE=false` serve apenas para desenvolvimento em HTTP local. Em produção, use HTTPS, `COOKIE_SECURE=true`, uma origem explícita em `CORS_ORIGINS` e um banco PostgreSQL.

## Migrações e demonstração

```powershell
alembic -c backend\alembic.ini upgrade head
py -3 backend\app\seed_demo.py
```

```bash
alembic -c backend/alembic.ini upgrade head
python backend/app/seed_demo.py
```

O usuário demonstrativo é `demo@gametracker.local` / `GameTracker-demo-2026`. Os registros têm origem local e não representam integrações reais. O seed é idempotente.

Para criar os dados de demonstração manualmente, execute `py -3 backend\app\seed_demo.py` no Windows ou `python backend/app/seed_demo.py` no Linux/macOS. O seed recusa execução quando `ENVIRONMENT=production`.

## Steam

1. Obtenha uma Steam Web API key para o servidor e coloque-a em `STEAM_API_KEY` no `.env`; ela nunca vai para o navegador.
2. Em desenvolvimento, mantenha `STEAM_REDIRECT_URL=http://localhost:8000/api/integrations/steam/callback` e abra o frontend em `http://localhost:5173`.
3. Em Docker local, use `http://localhost:8080/api/integrations/steam/callback`. Em produção, use a URL HTTPS pública correspondente e o mesmo domínio no callback e no frontend.
4. Entre no GameTracker, abra **Conexões**, autorize a identidade Steam e sincronize. A Steam só fornece jogos e tempo total quando os detalhes dos jogos estão visíveis para a chave/API. Horas históricas importadas não viram sessões datadas.
5. Sincronizações repetidas em menos de um minuto usam o resultado salvo; respostas 429, falhas de rede, chave recusada e perfil privado são registradas no histórico.

O método `GetOwnedGames` exige uma chave Web API no backend e pode não retornar jogos privados; veja a [referência oficial IPlayerService](https://partner.steamgames.com/doc/webapi/IPlayerService). A autenticação de identidade usa Steam OpenID, conforme a documentação para desenvolvedores em [Steam Community](https://steamcommunity.com/dev).

## Testes

```bash
pytest backend/tests -q
cd frontend
npm test
```

Os testes do frontend usam o runner nativo do Node para validar a renderização dos estados vazios e de erro sem adicionar dependências externas de teste. Não há testes de ponta a ponta de navegador nesta fase.

## Rotas principais

| Área | Endpoints |
| --- | --- |
| Autenticação | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `GET /api/auth/csrf`, `POST /api/auth/logout` |
| Perfil | `GET|PATCH|DELETE /api/profile` |
| Biblioteca | `GET|POST /api/games`, `GET|PATCH|DELETE /api/games/{game_id}` |
| Sessões | `GET|POST /api/sessions`, `PATCH|DELETE /api/sessions/{session_id}`, `POST /api/sessions/active/{start|pause|resume|stop}` |
| Metas | `GET|POST /api/goals`, `PATCH|DELETE /api/goals/{goal_id}` |
| Resumo | `GET /api/dashboard`, `GET /api/statistics?days=30`, `GET /api/export?format=json|csv` |
| Preferências | `GET|PATCH /api/settings` |
| Integrações | `GET /api/integrations`, `GET /api/integrations/steam/connect`, `GET /api/integrations/steam/callback`, `POST /api/integrations/steam/sync`, `DELETE /api/integrations/steam` |
| Serviço | `GET /health`, `GET /docs`, `GET /openapi.json` |

Os parâmetros e modelos de entrada/saída também aparecem no OpenAPI do FastAPI.

## Integrações

A integração Steam usa OpenID para verificar a identidade e mantém a chave Web API somente no backend. A importação depende de uma chave configurada e da visibilidade da biblioteca na Steam; consulte a seção [Steam](#steam) para ativação. As demais plataformas aparecem como indisponíveis até haver uma interface oficial autorizada.

## Build

```bash
cd frontend
npm run build
```

## Docker

Copie `.env.example` para `.env`, substitua `SECRET_KEY` e `POSTGRES_PASSWORD` e configure a origem pública antes de disponibilizar o serviço. Para desenvolvimento local:

```bash
docker compose up --build
```

A aplicação ficará em <http://localhost:8080>; a API em <http://localhost:8080/docs>. O volume `gametracker-data` mantém o PostgreSQL entre reinicializações. Para deploy, coloque TLS em um proxy reverso, ajuste `FRONTEND_ORIGIN`, `CORS_ORIGINS`, `STEAM_REDIRECT_URL` e defina `COOKIE_SECURE=true`.

No Windows, use os mesmos comandos no PowerShell com Docker Desktop e o plugin `docker compose`.
