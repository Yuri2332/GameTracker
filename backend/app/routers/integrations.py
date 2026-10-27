import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Game, PlatformConnection, SteamOpenIDNonce, SyncLog, User, UserGame

router = APIRouter(prefix="/integrations", tags=["integrations"])
STEAM_OPENID = "https://steamcommunity.com/openid/login"
STEAM_OWNED_GAMES = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"


def frontend_result(kind: str, reason: str | None = None) -> str:
    query = {"steam": kind}
    if reason: query["reason"] = reason[:120]
    return f"{settings.frontend_origin.rstrip('/')}/integrations?{urlencode(query)}"


def finish_steam(kind: str, reason: str | None = None) -> RedirectResponse:
    redirect = RedirectResponse(frontend_result(kind, reason))
    redirect.delete_cookie("gametracker_steam_state", path="/api/integrations/steam/callback")
    return redirect


def get_connection(db: Session, user: User) -> PlatformConnection | None:
    return db.query(PlatformConnection).filter(PlatformConnection.user_id == user.id, PlatformConnection.provider == "steam").first()


@router.get("")
def list_integrations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    connection = get_connection(db, user)
    logs = []
    if connection:
        logs = [{"id": row.id, "started_at": row.started_at, "finished_at": row.finished_at,
                 "status": row.status, "message": row.message, "imported_count": row.imported_count,
                 "total_count": row.total_count}
                for row in db.query(SyncLog).filter(SyncLog.connection_id == connection.id).order_by(SyncLog.started_at.desc()).limit(10)]
    return {"items": [
        {"provider": "steam", "name": "Steam", "configured": bool(settings.steam_api_key),
         "connected": bool(connection and connection.status == "connected"),
         "account_id": connection.external_user_id if connection else None,
         "last_synced_at": connection.last_synced_at if connection else None,
         "note": "Importa jogos e o total de horas informado pela Steam. A visibilidade dos jogos do perfil precisa estar pública.",
         "logs": logs},
        {"provider": "xbox", "name": "Xbox", "configured": False, "connected": False,
         "note": "Uma conexão oficial autorizada ainda não está configurada."},
        {"provider": "playstation", "name": "PlayStation Network", "configured": False, "connected": False,
         "note": "Nenhuma interface autorizada está configurada."},
        {"provider": "discord", "name": "Discord", "configured": False, "connected": False,
         "note": "Presença requer autorização e permissões específicas do Discord."},
    ]}


@router.get("/steam/connect")
def steam_connect(response: Response, user: User = Depends(get_current_user)):
    if not settings.steam_api_key:
        raise HTTPException(status_code=503, detail="Steam não configurada: defina STEAM_API_KEY no backend")
    state = secrets.token_urlsafe(32)
    callback = f"{settings.steam_redirect_url}?state={state}"
    parsed = urlparse(settings.steam_redirect_url)
    realm = f"{parsed.scheme}://{parsed.netloc}/"
    params = {"openid.ns": "http://specs.openid.net/auth/2.0", "openid.mode": "checkid_setup",
              "openid.return_to": callback, "openid.realm": realm,
              "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
              "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select"}
    redirect = RedirectResponse(f"{STEAM_OPENID}?{urlencode(params)}", status_code=302)
    redirect.set_cookie("gametracker_steam_state", state, max_age=600, httponly=True,
                        secure=settings.cookie_secure, samesite="lax", path="/api/integrations/steam/callback")
    return redirect


@router.get("/steam/callback")
def steam_callback(request: Request, state: str | None = None,
                   gametracker_steam_state: str | None = Cookie(default=None),
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not settings.steam_api_key:
        return finish_steam("error", "Steam não está configurada no servidor.")
    if not state or not gametracker_steam_state or not secrets.compare_digest(state, gametracker_steam_state):
        return finish_steam("error", "A verificação de segurança expirou. Tente conectar novamente.")
    params = dict(request.query_params)
    claimed_id = params.get("openid.claimed_id", "")
    identity = params.get("openid.identity", "")
    match = re.fullmatch(r"https://steamcommunity\.com/openid/id/(\d{17})", claimed_id)
    expected_return = f"{settings.steam_redirect_url}?state={state}"
    nonce_value = params.get("openid.response_nonce", "")
    if params.get("openid.mode") != "id_res" or not match or identity != claimed_id or params.get("openid.op_endpoint") != STEAM_OPENID or params.get("openid.return_to") != expected_return:
        return finish_steam("error", "A Steam retornou uma identidade inválida.")
    try:
        nonce_time = datetime.fromisoformat(nonce_value[:20].replace("Z", "+00:00"))
        if nonce_time.tzinfo is None: nonce_time = nonce_time.replace(tzinfo=timezone.utc)
        nonce_age = (datetime.now(timezone.utc) - nonce_time.astimezone(timezone.utc)).total_seconds()
        if not nonce_value or nonce_age < -120 or nonce_age > 600:
            return finish_steam("error", "A resposta de autenticação da Steam expirou.")
    except ValueError:
        return finish_steam("error", "A resposta de autenticação da Steam é inválida.")
    check_params = params.copy()
    check_params["openid.mode"] = "check_authentication"
    try:
        verified = httpx.post(STEAM_OPENID, data=check_params, timeout=10)
        verified.raise_for_status()
        valid = "is_valid:true" in verified.text.replace("\r", "").lower()
    except httpx.HTTPError:
        valid = False
    if not valid:
        return finish_steam("error", "Não foi possível validar a resposta da Steam.")
    nonce_hash = hashlib.sha256(nonce_value.encode("utf-8")).hexdigest()
    if db.get(SteamOpenIDNonce, nonce_hash):
        return finish_steam("error", "Esta resposta de autenticação já foi usada.")
    db.query(SteamOpenIDNonce).filter(SteamOpenIDNonce.expires_at < datetime.now(timezone.utc)).delete()
    db.add(SteamOpenIDNonce(nonce_hash=nonce_hash, user_id=user.id,
                            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)))
    connection = get_connection(db, user)
    if not connection:
        connection = PlatformConnection(user_id=user.id, provider="steam")
        db.add(connection)
    connection.external_user_id = match.group(1)
    connection.status = "connected"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return finish_steam("error", "Esta resposta de autenticação já foi usada.")
    return finish_steam("connected")


@router.post("/steam/sync")
def steam_sync(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    connection = get_connection(db, user)
    if not connection or connection.status != "connected" or not connection.external_user_id:
        raise HTTPException(status_code=409, detail="Conecte sua conta Steam primeiro")
    if not settings.steam_api_key:
        raise HTTPException(status_code=503, detail="Steam não configurada no servidor")
    now = datetime.now(timezone.utc)
    last_synced = connection.last_synced_at
    if last_synced:
        if last_synced.tzinfo is None: last_synced = last_synced.replace(tzinfo=timezone.utc)
        if (now - last_synced).total_seconds() < 60:
            previous = db.query(SyncLog).filter(SyncLog.connection_id == connection.id, SyncLog.status == "success").order_by(SyncLog.started_at.desc()).first()
            return {"status": "cached", "cached": True, "imported": 0,
                    "total": previous.total_count if previous else 0, "last_synced_at": connection.last_synced_at}
    log = SyncLog(connection_id=connection.id, status="running", started_at=now)
    db.add(log)
    db.commit()
    try:
        result = httpx.get(STEAM_OWNED_GAMES, params={"key": settings.steam_api_key,
                            "steamid": connection.external_user_id, "include_appinfo": 1,
                            "include_played_free_games": 1}, timeout=15)
        if result.status_code in (401, 403):
            raise HTTPException(status_code=502, detail="A Steam recusou a chave ou o perfil está privado")
        if result.status_code == 429:
            raise HTTPException(status_code=429, detail="Limite temporário da Steam. Tente novamente mais tarde.")
        result.raise_for_status()
        payload = result.json().get("response", {})
        source_games = payload.get("games")
        if not isinstance(source_games, list):
            raise HTTPException(status_code=422, detail="A Steam não retornou a biblioteca; verifique a privacidade do perfil")
        imported = 0
        for item in source_games:
            if not isinstance(item, dict): continue
            appid = str(item.get("appid", ""))
            name = str(item.get("name", "")).strip()
            if not appid.isdigit() or not name: continue
            name = name[:160]
            minutes = max(0, int(item.get("playtime_forever", 0)))
            row = db.query(UserGame).filter(UserGame.user_id == user.id, UserGame.external_game_id == appid).first()
            if row:
                row.imported_playtime_minutes = minutes
                continue
            game = db.query(Game).filter(Game.name.ilike(name)).first()
            if not game:
                game = Game(name=name)
                db.add(game)
                db.flush()
            db.add(UserGame(user_id=user.id, game_id=game.id, platform="Steam", status="backlog",
                            external_game_id=appid, imported_playtime_minutes=minutes))
            imported += 1
        connection.last_synced_at = datetime.now(timezone.utc)
        log.status, log.finished_at, log.imported_count = "success", datetime.now(timezone.utc), imported
        log.total_count = len(source_games)
        log.message = f"Sincronização concluída: {imported} jogos novos; {len(source_games)} jogos avaliados."
        db.commit()
        return {"status": "success", "cached": False, "imported": imported, "total": len(source_games), "last_synced_at": connection.last_synced_at}
    except HTTPException as exc:
        db.rollback()
        log = db.get(SyncLog, log.id)
        if log:
            log.status, log.finished_at, log.message = "failed", datetime.now(timezone.utc), exc.detail
            db.commit()
        raise
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        db.rollback()
        log = db.get(SyncLog, log.id)
        if log:
            log.status, log.finished_at, log.message = "failed", datetime.now(timezone.utc), "Falha de rede ou resposta inválida da Steam."
            db.commit()
        raise HTTPException(status_code=502, detail="Falha ao sincronizar com a Steam") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        log = db.get(SyncLog, log.id)
        if log:
            log.status, log.finished_at, log.message = "failed", datetime.now(timezone.utc), "Falha ao salvar dados importados da Steam."
            db.commit()
        raise HTTPException(status_code=500, detail="Não foi possível salvar a sincronização da Steam") from exc


@router.delete("/steam", status_code=204)
def steam_disconnect(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    connection = get_connection(db, user)
    if connection:
        connection.status = "disconnected"
        connection.external_user_id = None
        connection.last_synced_at = None
        db.commit()
