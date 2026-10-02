export type Tool = 'inspect' | 'get_inventory' | 'take' | 'use_item' | 'submit_code' | 'move';
export type Args = Record<string, string>;
export interface Affordance { tool: Tool; label: string; arguments: Args; requires_code: boolean }
export interface GameObject { object_id: string; name: string; kind: 'clue' | 'container' | 'door' | 'device' | 'item'; description: string; actions: Affordance[] }
export interface VisibleState {
  schema_version: string; level_version: string; session_id: string; revision: number; generation: string; status: 'playing' | 'won';
  room: { room_id: string; name: string; description: string };
  objects: GameObject[];
  inventory: { item_id: string; name: string; description: string; usable_targets: string[] }[];
  clues: { clue_id: string; object_id: string; title: string; text: string }[];
  exits: { destination_id: string; name: string; unlocked: boolean }[];
  progress: { power_on: boolean; check_done: boolean };
  save: null | { schema_version: string; level_version: string; saved_at: string; source_revision: number; source_generation: string };
}
export interface Session { session_id: string; token: string }
interface ActionData { receipt: { event_id: string; message: string; observation: string | null; changed: boolean }; replayed: boolean; proposal: unknown | null; visible_state: VisibleState }
interface ControlData { request_id: string; replayed: boolean; message: string; visible_state: VisibleState }
export class ApiError extends Error {
  constructor(public code: string, message: string, public visibleState: VisibleState | null = null) { super(message); }
}
const STORAGE_KEY = 'campus-lab-session-v1';
export function readSession(): Session | null {
  try { const value = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null'); return value && typeof value.session_id === 'string' && typeof value.token === 'string' ? value : null; } catch { return null; }
}
export function storeSession(session: Session | null) {
  if (session) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session)); else sessionStorage.removeItem(STORAGE_KEY);
}
async function request<T>(path: string, session: Session | null, body?: object): Promise<{ ok: true; event_id: string; data: T }> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(path, { method: body === undefined ? 'GET' : 'POST', headers: { ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...(session ? { 'X-Session-Token': session.token } : {}) }, body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal });
    let value;
    try { value = await response.json(); } catch { throw new ApiError('SERVICE_UNAVAILABLE', '服务暂不可用，请检查本地服务后再试。'); }
    if (value?.ok === false && value.error && typeof value.error.message === 'string') throw new ApiError(value.error.code, value.error.message, value.visible_state ?? null);
    if (!response.ok || value?.ok !== true || !value.data?.visible_state) throw new ApiError('SERVICE_UNAVAILABLE', '此功能暂不可用，请确认后端版本或稍后再试。');
    return value;
  } catch (error) { if (error instanceof ApiError) throw error; throw new ApiError('NETWORK_ERROR', '连接中断或请求超时。请检查本地服务，再点击“同步进度”。'); }
  finally { window.clearTimeout(timeout); }
}
const path = (session: Session) => `/api/sessions/${encodeURIComponent(session.session_id)}`;
const version = (state: VisibleState) => ({ request_id: crypto.randomUUID(), revision: state.revision, generation: state.generation });
export const api = {
  create: () => request<Session & { visible_state: VisibleState }>('/api/sessions', null, {}),
  state: (session: Session) => request<{ visible_state: VisibleState }>(`${path(session)}/state`, session),
  action: (session: Session, state: VisibleState, tool: Tool, args: Args) => request<ActionData>(`${path(session)}/actions`, session, { ...version(state), tool, arguments: args }),
  control: (session: Session, state: VisibleState, operation: 'reset' | 'save' | 'restore') => request<ControlData>(`${path(session)}/${operation}`, session, version(state)),
};
