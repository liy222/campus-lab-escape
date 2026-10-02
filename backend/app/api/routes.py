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
