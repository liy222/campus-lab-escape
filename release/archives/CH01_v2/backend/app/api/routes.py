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


@router.post("/sessions/{session_id}/ai/turns")
async def ai_turn(session_id: str, request: Request):
    import asyncio
    from ..ai.types import TurnStart
    from ..storage.sqlite import new_id
    raw, parsed = await body(request)
    store = request.app.state.store
    token = request.headers.get("X-Session-Token")
    started = store.begin_ai(session_id, token, raw, parsed)
    if not isinstance(started[0], TurnStart):
        return response(started)
    start, callbacks = started
    try:
        result = await request.app.state.ai_runtime.run(start, callbacks)
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
