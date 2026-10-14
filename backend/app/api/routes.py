from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api")


async def body(request: Request):
    try:
        return await request.json(), True
    except Exception:
        return None, False


def response(result):
    status, payload = result
    return JSONResponse(payload, status_code=status)


@router.post("/sessions")
async def create_session(request: Request):
    raw, parsed = await body(request)
    return response(request.app.state.store.create(raw, parsed))


@router.get("/sessions/{session_id}/state")
def get_state(session_id: str, request: Request):
    return response(request.app.state.store.read(session_id, request.headers.get("X-Session-Token")))


@router.post("/sessions/{session_id}/actions")
async def perform_action(session_id: str, request: Request):
    raw, parsed = await body(request)
    return response(request.app.state.store.action(session_id, request.headers.get("X-Session-Token"), raw, parsed))


@router.post("/sessions/{session_id}/save")
async def save_session(session_id: str, request: Request):
    raw, parsed = await body(request)
    return response(request.app.state.store.control(session_id, request.headers.get("X-Session-Token"), "save", raw, parsed))


@router.post("/sessions/{session_id}/reset")
async def reset_session(session_id: str, request: Request):
    raw, parsed = await body(request)
    return response(request.app.state.store.control(session_id, request.headers.get("X-Session-Token"), "reset", raw, parsed))


@router.post("/sessions/{session_id}/restore")
async def restore_session(session_id: str, request: Request):
    raw, parsed = await body(request)
    return response(request.app.state.store.control(session_id, request.headers.get("X-Session-Token"), "restore", raw, parsed))


@router.get("/sessions/{session_id}/saves")
def list_session_saves(session_id: str, request: Request):
    return response(request.app.state.store.list_saves(session_id, request.headers.get("X-Session-Token")))


@router.post("/sessions/{session_id}/saves")
async def create_session_save(session_id: str, request: Request):
    raw, parsed = await body(request)
    return response(request.app.state.store.create_save(session_id, request.headers.get("X-Session-Token"), raw, parsed))


@router.post("/sessions/{session_id}/saves/{save_id}/restore")
async def restore_selected_save(session_id: str, save_id: str, request: Request):
    raw, parsed = await body(request)
    return response(request.app.state.store.restore_save(session_id, request.headers.get("X-Session-Token"), save_id, raw, parsed))


@router.post("/sessions/{session_id}/saves/{save_id}/delete")
async def delete_selected_save(session_id: str, save_id: str, request: Request):
    raw, parsed = await body(request)
    return response(request.app.state.store.delete_save(session_id, request.headers.get("X-Session-Token"), save_id, raw, parsed))


@router.post("/sessions/{session_id}/ai/turns")
async def ai_turn(session_id: str, request: Request):
    import asyncio
    from ..ai.runtime import create_request_runtime, validate_request_selection
    from ..ai.types import TurnStart
    from ..storage.sqlite import new_id
    raw, parsed = await body(request)
    store = request.app.state.store
    token = request.headers.get("X-Session-Token")
    providers = request.headers.getlist("X-AI-Provider")
    keys = request.headers.getlist("X-AI-Api-Key")
    provider_name = providers[0] if providers else None
    api_key = keys[0] if keys else None
    selection_error = ("AI 设置格式不正确，请重新输入。" if len(providers) > 1 or len(keys) > 1
                       else validate_request_selection(provider_name, api_key))
    if selection_error is not None:
        # Authenticate normally, but reject settings before reserving an AI turn.
        # Headers and the request body never enter this rejection event.
        with store.transaction() as connection:
            state = store.authenticate(connection, session_id, token)
            if state is None:
                return response(store.failure(connection, new_id(), None, "ai_turn", "FORBIDDEN_SESSION", "无权访问该会话。", expose=False))
            return response(store.failure(connection, new_id(), session_id, "ai_turn", "BAD_ARGUMENT", selection_error, state, expose=False))
    if api_key and isinstance(raw, dict) and isinstance(raw.get("message"), str):
        # A credential accidentally pasted into chat must not reach persistence,
        # history, trace, responses or model messages. Do not mutate the body.
        raw = {**raw, "message": raw["message"].replace(api_key, "[REDACTED]")}
    started = store.begin_ai(session_id, token, raw, parsed)
    if not isinstance(started[0], TurnStart):
        return response(started)
    start, callbacks = started
    try:
        runtime = request.app.state.ai_runtime
        if provider_name is not None:
            # Construct only for a new reservation: replays never call providers.
            runtime = create_request_runtime(runtime, provider_name, api_key)
        result = await runtime.run(start, callbacks)
        return response(store.finish_ai(session_id, start.turn_id, result))
    except asyncio.CancelledError:
        store.abandon_ai(session_id, start.turn_id)
        raise
    except Exception:
        # Unknown upstream/runtime outcome is durable and cannot be charged again.
        store.abandon_ai(session_id, start.turn_id)
        with store.transaction() as connection:
            state = store.authenticate(connection, session_id, token)
            return response(store.failure(connection, new_id(), session_id, "ai_turn", "MODEL_UNAVAILABLE", "该轮次结果未知，进度已保留；同一请求不会重新调用模型。", state, {"turn_id": start.turn_id}))


@router.post("/sessions/{session_id}/proposals/{proposal_id}/confirm")
async def confirm_proposal(session_id: str, proposal_id: str, request: Request):
    raw, parsed = await body(request)
    return response(request.app.state.store.proposal_operation(session_id, request.headers.get("X-Session-Token"), proposal_id, "confirm", raw, parsed))


@router.post("/sessions/{session_id}/proposals/{proposal_id}/cancel")
async def cancel_proposal(session_id: str, proposal_id: str, request: Request):
    raw, parsed = await body(request)
    return response(request.app.state.store.proposal_operation(session_id, request.headers.get("X-Session-Token"), proposal_id, "cancel", raw, parsed))
