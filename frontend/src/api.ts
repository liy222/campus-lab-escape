export type Tool = 'inspect' | 'get_inventory' | 'take' | 'use_item' | 'submit_code' | 'submit_login' | 'move' | 'interact' | 'rotate_circuit' | 'submit_circuit' | 'submit_sequence';
export type Args = Record<string, string>;
export type ActionArguments = Record<string, string | string[]>;
export interface Affordance { tool: Tool; label: string; arguments: Args; requires_code: boolean }
export interface GameObject { object_id: string; name: string; kind: 'clue' | 'container' | 'door' | 'device' | 'item'; description: string; actions: Affordance[] }
export interface DeviceStates {
  cabinet: 'LOCKED' | 'CODE_ACCEPTED' | 'OPEN' | 'ITEM_TAKEN';
  powerbox: 'CLOSED' | 'OPEN' | 'MISSING_FUSE' | 'FUSE_INSTALLED' | 'CIRCUIT_READY' | 'POWER_ON';
  computer: 'OFF' | 'BOOTING' | 'LOGIN_LOCKED' | 'UNLOCKED' | 'DATA_READ';
  exit: 'LOCKED' | 'CARD_ACCEPTED' | 'FINAL_CHECK' | 'UNLOCKED' | 'OPEN';
}
export interface PuzzleStates {
  microscope: 'EMPTY' | 'SLIDE_PLACED';
  panel: 'EMPTY' | 'STRIP_INSERTED';
}
export interface CircuitModule { module_id: string; row: number; column: number; shape: 'I' | 'L'; rotation: 0 | 1 | 2 | 3 }
export interface CircuitPuzzle {
  target_id: string; rows: 3; columns: 3;
  source: { module_id: string; side: 'N' | 'E' | 'S' | 'W' };
  sink: { module_id: string; side: 'N' | 'E' | 'S' | 'W' };
  modules: CircuitModule[]; status: 'editing' | 'completed';
}
export interface SequenceDevice { device_id: string; label: string; symbol: string }
export interface SequencePuzzle { target_id: string; devices: SequenceDevice[]; length: 4; status: 'editing' | 'completed' }
export interface VisibleState {
  schema_version: string; level_version: string; session_id: string; revision: number; generation: string; status: 'playing' | 'won';
  room: { room_id: string; name: string; description: string };
  objects: GameObject[];
  device_states?: DeviceStates;
  puzzle_states?: PuzzleStates;
  minigames?: { circuit: CircuitPuzzle | null; sequence: SequencePuzzle | null };
  observed_object_ids?: string[];
  inventory: { item_id: string; name: string; description: string; usable_targets: string[] }[];
  clues: { clue_id: string; object_id: string; title: string; text: string }[];
  exits: { destination_id: string; name: string; unlocked: boolean }[];
  progress: { power_on: boolean; check_done: boolean };
  statistics?: { started_at: string; finished_at: string | null; current_hint_level: 1 | 2 | 3; hint_count: number; mistake_count: number; clues_found: number; clues_total: 10; hidden_found: number; hidden_total: 2 };
  settlement?: null | { elapsed_seconds: number; clues_found: number; clues_total: 10; hint_count: number; mistake_count: number; hidden_found: number; hidden_total: 2; rating: 'S' | 'A' | 'B' | 'C' };
  save: null | { schema_version: string; level_version: string; saved_at: string; source_revision: number; source_generation: string };
}
export interface Session { session_id: string; token: string }
export type AiSettings = { provider: 'mock' } | { provider: 'deepseek'; apiKey: string };
export type ProgressTool = Exclude<Tool, 'inspect' | 'get_inventory' | 'interact' | 'submit_login' | 'rotate_circuit' | 'submit_circuit' | 'submit_sequence'>;
export interface Proposal { proposal_id: string; tool: ProgressTool; arguments: Args; revision: number; generation: string; expires_at: string; status: 'pending' | 'committed' | 'cancelled' | 'expired' | 'invalidated' | 'rejected'; clue_refs: string[]; summary: string }
export interface Receipt { request_id: string; event_id: string; tool: Tool; arguments: ActionArguments; generation: string; revision_before: number; revision_after: number; changed: boolean; message: string; observation: string | null; new_clue_ids: string[]; consumed_item_ids: string[] }
export interface AiTurnData { turn_id: string; answer: string; clue_refs: string[]; proposal: Proposal | null; status: 'completed' | 'no_suggestion' | 'stopped'; stop_reason: 'MODEL_TIMEOUT' | 'MODEL_UNAVAILABLE' | 'MODEL_INVALID_OUTPUT' | 'AI_LIMIT_REACHED' | 'STALE_STATE' | null; usage: { provider: string; model: string | null; input_tokens: number | null; output_tokens: number | null; model_calls: number; read_tool_calls: number }; visible_state: VisibleState }
interface ActionData { receipt: Receipt; replayed: boolean; proposal: Proposal | null; visible_state: VisibleState }
interface ControlData { request_id: string; replayed: boolean; message: string; visible_state: VisibleState }
export class ApiError extends Error {
  constructor(public code: string, message: string, public visibleState: VisibleState | null = null, public eventId: string | null = null) { super(message); }
}
type GameplayVersion = 'legacy' | 'v3.1' | 'v3.2' | 'v3.3' | 'v3.4';
const configuredVersion = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env?.VITE_GAMEPLAY_VERSION;
const gameplayVersion: GameplayVersion = configuredVersion === 'legacy' || configuredVersion === 'v3.1' || configuredVersion === 'v3.2' || configuredVersion === 'v3.3' || configuredVersion === 'v3.4' ? configuredVersion : 'v3.4';
const STORAGE_KEYS: Record<GameplayVersion, string> = {
  legacy: 'campus-lab-session-v1',
  'v3.1': 'campus-lab-session-upgrade-v3.1',
  'v3.2': 'campus-lab-session-upgrade-v3.2',
  'v3.3': 'campus-lab-session-upgrade-v3.3',
  'v3.4': 'campus-lab-session-upgrade-v3.4',
};
const STORAGE_KEY = STORAGE_KEYS[gameplayVersion];
export function readSession(): Session | null {
  try { const value = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null'); return value && typeof value.session_id === 'string' && typeof value.token === 'string' ? value : null; } catch { return null; }
}
export function storeSession(session: Session | null) {
  if (session) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session)); else sessionStorage.removeItem(STORAGE_KEY);
}
async function request<T>(path: string, session: Session | null, body?: object, timeoutMs = 15000, extraHeaders: Record<string, string> = {}): Promise<{ ok: true; event_id: string; data: T }> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const headers = new Headers(extraHeaders);
    headers.delete('Authorization');
    headers.delete('X-Session-Token');
    if (body !== undefined) headers.set('Content-Type', 'application/json');
    if (session) headers.set('X-Session-Token', session.token);
    const response = await fetch(path, { method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal });
    let value;
    try { value = await response.json(); } catch { throw new ApiError('SERVICE_UNAVAILABLE', '服务暂不可用，请检查本地服务后再试。'); }
    if (value?.ok === false && value.error && typeof value.error.message === 'string') throw new ApiError(value.error.code, value.error.message, value.visible_state ?? null, value.event_id ?? null);
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
  action: (session: Session, state: VisibleState, tool: Tool, args: ActionArguments) => request<ActionData>(`${path(session)}/actions`, session, { ...version(state), tool, arguments: args }),
  control: (session: Session, state: VisibleState, operation: 'reset' | 'save' | 'restore') => request<ControlData>(`${path(session)}/${operation}`, session, version(state)),
  ai: (session: Session, state: VisibleState, message: string, settings: AiSettings = { provider: 'mock' }, hintLevel?: 1 | 2 | 3) => {
    const headers: Record<string, string> = { 'X-AI-Provider': settings.provider };
    if (settings.provider === 'deepseek') {
      const apiKey = settings.apiKey.trim();
      if (!apiKey) return Promise.reject(new ApiError('AI_KEY_REQUIRED', '请先填写 DeepSeek API Key，再询问伙伴。'));
      if (/[^\x21-\x7E]/.test(apiKey)) return Promise.reject(new ApiError('AI_KEY_INVALID', 'API Key 格式不正确，请重新输入，避免空格、中文或换行。'));
      headers['X-AI-Api-Key'] = apiKey;
    }
    return request<AiTurnData>(`${path(session)}/ai/turns`, session, { ...version(state), message, ...(hintLevel === undefined ? {} : { hint_level: hintLevel }) }, 55000, headers);
  },
  confirm: (session: Session, proposalId: string) => request<ActionData>(`${path(session)}/proposals/${encodeURIComponent(proposalId)}/confirm`, session, {}),
  cancel: (session: Session, proposalId: string) => request<{ proposal: Proposal; visible_state: VisibleState }>(`${path(session)}/proposals/${encodeURIComponent(proposalId)}/cancel`, session, {}),
};
