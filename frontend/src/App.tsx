import { useEffect, useRef, useState } from 'react';
import { api, ApiError, readSession, storeSession, type ActionArguments, type CircuitPuzzle, type Receipt, type SaveSlot, type Session, type Tool, type VisibleState } from './api';
import Assistant from './Assistant';
import RoomLoader from './components/RoomLoader';
import Entry from './components/Entry';
import { useGamePresentation } from './game/preferences';
import Notebook from './components/Notebook';
import { trapPanelFocus } from './components/panelFocus';

const kindLabel = { clue: '可观察', container: '容器', door: '通道', device: '设备', item: '物品' };
const hotspotPosition: Record<string, string> = {
  r1_plaque: 'r1-plaque', r1_clock: 'r1-clock', r1_record: 'r1-record', r1_microscope: 'r1-microscope',
  sample_slide: 'r1-slide', r1_cabinet: 'r1-cabinet', r1_symbols: 'r1-symbols', r1_fuse: 'r1-fuse', r1_door: 'r1-door',
  r2_maintenance: 'r2-maintenance', r2_monitor: 'r2-monitor', r2_powerbox: 'r2-powerbox',
  research_strip: 'r2-strip', access_card: 'r2-card', r2_door: 'r2-door',
  r3_legend: 'r3-legend', r3_panel: 'r3-panel', exit_door: 'r3-exit',
};
function Icon({ kind }: { kind: string }) {
  const paths: Record<string, React.ReactNode> = {
    clue: <><path d="M5 3h10l4 4v14H5V3ZM14 3v5h5M8 12h8M8 16h6"/></>,
    container: <><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M4 12h16M12 3v18M9 8v1M15 8v1M9 16v1M15 16v1"/></>,
    door: <path d="M5 21V3h14v18M3 21h18M9 6h7v15M13 13h.01"/>,
    device: <><rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4M7 9h10M7 12h5"/></>,
    item: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 9h18M7 14h4M16 14h1"/></>,
    bag: <path d="M7 7V5a5 5 0 0 1 10 0v2M5 7h14l2 14H3L5 7ZM8 12h8"/>,
    spark: <path d="m12 2 2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5L12 2Z"/>,
  };
  return <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[kind] || paths.clue}</svg>;
}
function circuitPorts(shape: 'I' | 'L', rotation: number): string[] {
  const base = shape === 'I' ? ['N', 'S'] : ['N', 'E'];
  const clockwise = ['N', 'E', 'S', 'W'];
  return base.map(side => clockwise[(clockwise.indexOf(side) + rotation) % 4]);
}
function durationLabel(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  return `${Math.floor(seconds / 3600)}:${String(Math.floor(seconds / 60) % 60).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}
const saveRoomLabel: Record<string, string> = { R1: '第一房间', R2: '第二房间', R3: '第三房间', EXIT: '出口' };
function saveTimeLabel(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false });
}
function CircuitBoard({ circuit, disabled, onRotate }: { circuit: CircuitPuzzle; disabled: boolean; onRotate: (moduleId: string) => void }) {
  const sourceId = circuit.source.module_id;
  const sinkId = circuit.sink.module_id;
  const sideLabel: Record<string, string> = { N: '上侧', E: '右侧', S: '下侧', W: '左侧' };
  return <div className={`circuit-board ${circuit.status === 'completed' ? 'is-complete' : ''}`} role="group" aria-label="三乘三线路模块">
    {Array.from({ length: circuit.rows * circuit.columns }, (_, index) => {
      const row = Math.floor(index / circuit.columns);
      const column = index % circuit.columns;
      const module = circuit.modules.find(item => item.row === row && item.column === column);
      if (!module) return <div key={`empty-${row}-${column}`} className="circuit-cell circuit-cell-empty" aria-hidden="true"/>;
      const ports = circuitPorts(module.shape, module.rotation);
      const portPoint: Record<string, [number, number]> = { N: [50, 7], E: [93, 50], S: [50, 93], W: [7, 50] };
      const isSource = module.module_id === sourceId;
      const isSink = module.module_id === sinkId;
      return <button key={module.module_id} type="button" className={`circuit-cell ${isSource ? 'circuit-cell-source' : ''} ${isSink ? 'circuit-cell-sink' : ''}`} data-module-id={module.module_id} data-source={isSource || undefined} data-sink={isSink || undefined} disabled={disabled || circuit.status === 'completed'} onClick={() => onRotate(module.module_id)} aria-label={`旋转线路模块 ${module.module_id} 顺时针90度`}>
        <svg viewBox="0 0 100 100" aria-hidden="true" focusable="false"><circle className="circuit-junction" cx="50" cy="50" r="8"/>{ports.map(side => { const [x, y] = portPoint[side]; return <g key={side}><path className="circuit-wire" d={`M50 50 L${x} ${y}`}/><circle className="circuit-port" cx={x} cy={y} r="5"/></g>; })}</svg>
        <span className="circuit-module-id">{module.module_id}</span>{isSource && <span className={`circuit-terminal-label terminal-${circuit.source.side.toLowerCase()}`}>{sideLabel[circuit.source.side]}电源</span>}{isSink && <span className={`circuit-terminal-label terminal-${circuit.sink.side.toLowerCase()}`}>{sideLabel[circuit.sink.side]}主系统</span>}
      </button>;
    })}
  </div>;
}
export default function App() {
  const [session, setSession] = useState<Session | null>(readSession);
  const [state, setState] = useState<VisibleState | null>(null);
  const stateRef = useRef<VisibleState | null>(null);
  const retiredGenerations = useRef(new Set<string>());
  const busy = useRef(false);
  const [pending, setPending] = useState(false);
  const [needsSync, setNeedsSync] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [interactionId, setInteractionId] = useState<string | null>(null);
  const [loginOpenId, setLoginOpenId] = useState<string | null>(null);
  const [codes, setCodes] = useState<Record<string, string>>({});
  const [loginCredentials, setLoginCredentials] = useState({ username: '', password: '' });
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [observation, setObservation] = useState('');
  const [confirmation, setConfirmation] = useState<'new' | 'reset' | 'restore' | 'slot-restore' | null>(null);
  const [saveSlots, setSaveSlots] = useState<SaveSlot[]>([]);
  const [saveName, setSaveName] = useState('');
  const [saveListError, setSaveListError] = useState('');
  const [restoreSaveId, setRestoreSaveId] = useState<string | null>(null);
  const saveListRequest = useRef(0);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [history, setHistory] = useState<{ id: string; text: string }[]>([]);
  const [sequenceDraft, setSequenceDraft] = useState<string[]>([]);
  const [clockNow, setClockNow] = useState(Date.now);
  const [drawer, setDrawer] = useState<'notebook' | 'assistant' | 'menu' | null>(null);
  const [notebookPage, setNotebookPage] = useState(0);
  const [visualReceipt, setVisualReceipt] = useState<Receipt | null>(null);
  const visual = state?.level_version === '3.4.0';
  const visualEntry = !state && !['legacy', 'v3.1', 'v3.2', 'v3.3'].includes((import.meta as ImportMeta & { env?: Record<string, string> }).env?.VITE_GAMEPLAY_VERSION || 'v3.4');
  const presentation = useGamePresentation(visualReceipt, state);
  useEffect(() => { if (!visual) setDrawer(null); }, [visual]);
  useEffect(() => { const close = (event: KeyboardEvent) => { if (event.key === 'Escape' && !dialogRef.current?.open) { if (drawer) setDrawer(null); else setSelectedId(null); } }; window.addEventListener('keydown', close); return () => window.removeEventListener('keydown', close); }, [drawer]);
  useEffect(() => { if (drawer === 'assistant' || drawer === 'menu') document.querySelector<HTMLElement>('.visual-support [role="dialog"] .drawer-close')?.focus(); }, [drawer]);
  const selected = state?.objects.find(object => object.object_id === selectedId) || null;
  useEffect(() => { if (confirmation) dialogRef.current?.showModal(); else dialogRef.current?.close(); }, [confirmation]);
  useEffect(() => { const timer = window.setInterval(() => setClockNow(Date.now()), 1000); return () => window.clearInterval(timer); }, []);
  function apply(next: VisibleState, replace = false, reconciled = false): boolean {
    const previous = stateRef.current;
    if (!replace && previous && (next.session_id !== previous.session_id || next.revision < previous.revision || retiredGenerations.current.has(next.generation))) return false;
    if (replace) retiredGenerations.current.clear();
    else if (previous && previous.generation !== next.generation) retiredGenerations.current.add(previous.generation);
    setVisualReceipt(null);
    const generationChanged = !previous || replace || previous.generation !== next.generation;
    const roomChanged = !!previous && previous.room.room_id !== next.room.room_id;
    if (previous && previous.revision !== next.revision) setCodes({});
    if (generationChanged || roomChanged) {
      setCodes({}); setLoginCredentials({ username: '', password: '' }); setObservation(''); setSelectedId(null); setSelectedItemId(null); setInteractionId(null); setLoginOpenId(null);
      setSequenceDraft([]);
      setDrawer(null); setNotebookPage(0);
      if (generationChanged) setHistory([]);
    }
    if (selectedItemId && !next.inventory.some(item => item.item_id === selectedItemId)) setSelectedItemId(null);
    stateRef.current = next; setState(next); if (replace || reconciled) setNeedsSync(false); return true;
  }
  async function refreshSaveSlots(activeSession: Session, expected: VisibleState): Promise<void> {
    const requestId = ++saveListRequest.current;
    setSaveListError('');
    try {
      const response = await api.saveSlots(activeSession);
      const live = stateRef.current;
      const projection = response.data.visible_state;
      if (requestId !== saveListRequest.current || !live
        || live.session_id !== activeSession.session_id || live.session_id !== expected.session_id
        || live.generation !== expected.generation || live.revision !== expected.revision
        || projection.session_id !== expected.session_id || projection.generation !== expected.generation
        || projection.revision !== expected.revision) return;
      setSaveSlots(response.data.slots);
    } catch (caught) {
      if (requestId !== saveListRequest.current) return;
      if (caught instanceof ApiError && caught.code === 'FORBIDDEN_SESSION') { invalidateSession(activeSession.session_id); return; }
      setSaveListError(caught instanceof ApiError ? caught.message : '存档列表暂时无法读取，请同步进度后重试。');
    }
  }
  function invalidateSession(sessionId: string) {
    if (stateRef.current && stateRef.current.session_id !== sessionId) return;
    saveListRequest.current += 1; setSaveSlots([]); setSaveListError(''); setRestoreSaveId(null);
    storeSession(null); setSession(null); stateRef.current = null; setState(null); setCodes({}); setLoginCredentials({ username: '', password: '' }); setHistory([]); setObservation(''); setSequenceDraft([]); setSelectedId(null); setSelectedItemId(null); setInteractionId(null); setLoginOpenId(null); setNeedsSync(false); retiredGenerations.current.clear();
  }
  async function execute(work: () => Promise<void>, reconcile = false, actionFeedback = false) {
    if (busy.current) return;
    busy.current = true; setPending(true); setError(''); setNotice('');
    try { await work(); }
    catch (caught) {
      const failure = caught instanceof ApiError ? caught : new ApiError('CLIENT_ERROR', '操作未完成，请稍后重试。');
      if (actionFeedback && !['NETWORK_ERROR', 'SERVICE_UNAVAILABLE', 'FORBIDDEN_SESSION'].includes(failure.code)) presentation.play('error');
      if (failure.visibleState) apply(failure.visibleState);
      if (failure.code === 'FORBIDDEN_SESSION' && session) invalidateSession(session.session_id);
      else if (reconcile && session && ['NETWORK_ERROR', 'SERVICE_UNAVAILABLE'].includes(failure.code)) {
        setNeedsSync(true);
        try { const response = await api.state(session); if (apply(response.data.visible_state, false, true)) await refreshSaveSlots(session, response.data.visible_state); setNotice('已同步服务器上的实际进度与存档列表，请确认当前场景后再操作。'); } catch { setNotice('尚未确认这次操作的结果。请先同步进度，确认后再继续。'); }
      }
      setError(failure.message);
    } finally { busy.current = false; setPending(false); }
  }
  function create() {
    setConfirmation(null);
    void execute(async () => { const response = await api.create(); const nextSession = { session_id: response.data.session_id, token: response.data.token }; saveListRequest.current += 1; setSaveSlots([]); setSaveListError(''); storeSession(nextSession); setSession(nextSession); apply(response.data.visible_state, true); await refreshSaveSlots(nextSession, response.data.visible_state); setNotice('游戏已开始。选择场景中的物件，慢慢寻找线索。'); });
  }
  function sync() { if (!session) return; void execute(async () => { const response = await api.state(session); if (apply(response.data.visible_state, false, true)) await refreshSaveSlots(session, response.data.visible_state); setNotice('已同步当前进度和存档列表。'); }); }
  function action(tool: Tool, args: ActionArguments) {
    if (!session || !stateRef.current || needsSync) return;
    const current = stateRef.current;
    void execute(async () => {
      const response = await api.action(session, current, tool, args);
      if (!apply(response.data.visible_state)) return;
      if (current.generation !== response.data.visible_state.generation) { setNotice('游戏进度已更新，请依据当前场景继续探索。'); return; }
      const receipt = response.data.receipt; if (!response.data.replayed) setVisualReceipt(receipt);
      if (current.level_version === '3.4.0' && ['R1', 'R2', 'R3'].includes(current.room.room_id) && tool === 'inspect' && typeof args.object_id === 'string' && response.data.visible_state.objects.some(object => object.object_id === args.object_id)) setSelectedId(args.object_id);
      setNotice(receipt.message); setObservation(receipt.observation || '');
      setHistory(entries => [{ id: receipt.event_id, text: receipt.message }, ...entries.filter(entry => entry.id !== receipt.event_id)].slice(0, 5));
      if (tool === 'submit_code') { setCodes({}); setInteractionId(null); }
      if (tool === 'submit_login') { setLoginCredentials({ username: '', password: '' }); setLoginOpenId(null); }
    }, true, true);
  }
  function visualObject(objectId: string) {
    if (pending || needsSync || !stateRef.current?.objects.some(object => object.object_id === objectId)) return;
    if (selectedItemId) { action('use_item', { item_id: selectedItemId, target_id: objectId }); return; }
    action('inspect', { object_id: objectId });
  }
  function openReference(clueId: string) {
    const index = stateRef.current?.clues.findIndex(clue => clue.clue_id === clueId) ?? -1;
    if (index >= 0) { setNotebookPage(Math.floor(index / 2)); setDrawer('notebook'); }
  }
  function selectObject(objectId: string) {
    setSelectedId(objectId); setInteractionId(null); setLoginOpenId(null); setCodes({}); setLoginCredentials({ username: '', password: '' }); setObservation('');
  }
  function interact(objectId: string) {
    const object = stateRef.current?.objects.find(value => value.object_id === objectId);
    if (!object) return;
    const opensMinigame = object.actions.some(affordance => affordance.tool === 'submit_circuit' || affordance.tool === 'submit_sequence');
    if (opensMinigame) { setInteractionId(objectId); setObservation(''); return; }
    const serverInteraction = object.actions.find(affordance => affordance.tool === 'interact');
    const takeAction = object.actions.find(affordance => affordance.tool === 'take');
    const codeAction = object.actions.find(affordance => affordance.tool === 'submit_code');
    const loginAction = object.actions.find(affordance => affordance.tool === 'submit_login' && affordance.arguments.target_id === 'r2_monitor');
    const inspectAction = object.actions.find(affordance => affordance.tool === 'inspect');
    if (serverInteraction) { setInteractionId(null); action('interact', serverInteraction.arguments); }
    else if (takeAction) { setInteractionId(null); action('take', takeAction.arguments); }
    else if (codeAction) { setInteractionId(objectId); setCodes(current => ({ ...current, [objectId]: '' })); }
    else if (loginAction) { setInteractionId(null); setLoginOpenId(objectId); }
    else if (inspectAction) { setInteractionId(null); action('inspect', inspectAction.arguments); }
    else { setInteractionId(null); action('inspect', { object_id: objectId }); }
  }
  function control(operation: 'reset' | 'save' | 'restore') {
    setConfirmation(null);
    if (!session || !stateRef.current || needsSync) return;
    const current = stateRef.current;
    void execute(async () => { const response = await api.control(session, current, operation); if (apply(response.data.visible_state)) { if (operation === 'reset' || operation === 'restore') setSequenceDraft([]); await refreshSaveSlots(session, response.data.visible_state); setNotice(response.data.message); } }, true);
  }
  function saveNewSlot() {
    if (!session || !stateRef.current || needsSync) return;
    const current = stateRef.current;
    const activeSession = session;
    const name = saveName.trim();
    void execute(async () => {
      const response = await api.createSaveSlot(activeSession, current, name || undefined);
      if (!apply(response.data.visible_state)) return;
      setSaveName('');
      await refreshSaveSlots(activeSession, response.data.visible_state);
      setNotice(response.data.message);
    }, true);
  }
  function restoreSelectedSlot() {
    setConfirmation(null);
    if (!session || !stateRef.current || needsSync || !restoreSaveId) return;
    const activeSession = session;
    const current = stateRef.current;
    const saveId = restoreSaveId;
    setRestoreSaveId(null);
    void execute(async () => {
      const response = await api.restoreSaveSlot(activeSession, current, saveId);
      if (!apply(response.data.visible_state)) return;
      await refreshSaveSlots(activeSession, response.data.visible_state);
      setNotice(response.data.message);
    }, true);
  }
  function requestSlotRestore(slot: SaveSlot) {
    if (pending || needsSync) return;
    setRestoreSaveId(slot.save_id);
    setConfirmation('slot-restore');
  }
  const won = state?.status === 'won';
  const disabled = pending || needsSync || !!won;
  const loginAffordance = selected?.object_id === 'r2_monitor'
    ? selected.actions.find(affordance => affordance.tool === 'submit_login' && affordance.arguments.target_id === 'r2_monitor')
    : undefined;
  const savedAt = state?.save ? new Date(state.save.saved_at) : null;
  const savedTime = savedAt && !Number.isNaN(savedAt.getTime()) ? savedAt.toLocaleString('zh-CN', { hour12: false }) : state?.save?.saved_at;
  return <div className={`app-shell ${visual || visualEntry ? 'visual-shell' : ''} ${presentation.reducedMotion ? 'reduce-motion' : ''}`}>
    <span className="presentation-observer" hidden data-audio-state={presentation.audioState} data-audio-cues={presentation.cueCount} data-audio-last-cue={presentation.lastCue} data-reduced-motion={presentation.reducedMotion}/>
    <a className="skip-link" href="#game">跳到游戏内容</a>
    <header className="topbar"><a className="brand" href="#game"><span className="brand-mark"><Icon kind="device"/></span><span>逃离校园实验室<small>CAMPUS LAB · ESCAPE</small></span></a><div className="top-actions"><span className="local-badge">● 本地游戏</span><button className="button subtle" disabled={pending} onClick={() => session ? setConfirmation('new') : create()}>新游戏</button>{session && <button className="button subtle" disabled={pending} onClick={sync}>{state ? '同步进度' : '继续当前游戏'}</button>}</div></header>
    <main id="game"><div className="page-heading"><div><p className="eyebrow">一次校园里的小小冒险</p><h1>{won ? '你找到出口了。' : '观察。发现。离开。'}</h1><p className="intro">每个不起眼的物件，都可能藏着下一步。</p></div><div className="chapter-badge"><span>{state?.room.room_id || 'START'}</span><small>{state ? '当前所在' : '准备探索'}</small></div></div>
      <div className="feedback" aria-live="polite" aria-atomic="true">{pending && <p className="pending"><span className="spinner"/>正在处理，请稍候…</p>}{error && <p className="error" role="alert">{error}</p>}{notice && <p className="notice">{notice}</p>}</div>
      {!state ? visualEntry ? <Entry hasSession={!!session} disabled={pending} onStart={() => session ? setConfirmation('new') : create()} onContinue={sync}/> : <section className="welcome panel"><div className="welcome-art" aria-hidden="true"><div className="art-window"><span/><span/><span/><span/></div><div className="art-desk"/><div className="art-note"/><div className="art-lamp"/><div className="art-plant"/></div><div className="welcome-copy"><p className="eyebrow">实验室的灯，还亮着</p><h2>从这里开始探索</h2><p>查看房间里的物件，记录发现的线索。收集道具、尝试你的推理，打开通往下一个房间的门。</p><div className="welcome-buttons"><button className="button primary" disabled={pending} onClick={() => session ? setConfirmation('new') : create()}>开始新游戏 →</button>{session && <button className="button" disabled={pending} onClick={sync}>继续当前游戏</button>}</div><small>进度与当前浏览器标签页关联，刷新后可以继续。</small></div></section> : <>
        {won && !visual && <section className="victory" role="status"><Icon kind="spark"/><div><h2>成功逃离实验室</h2><p>所有已发现的线索，仍保留在笔记中。</p></div></section>}
        {!visual && state.level_version === '3.4.0' && state.statistics && <section className="run-statistics panel" aria-label="本局统计"><h2>本局探索统计</h2><dl className="statistics-grid"><div><dt>用时</dt><dd data-stat="elapsed_seconds">{durationLabel(state.settlement?.elapsed_seconds ?? Math.floor(Math.max(0, clockNow - Date.parse(state.statistics.started_at)) / 1000))}</dd></div><div><dt>线索</dt><dd data-stat="clues_found">{state.statistics.clues_found}/{state.statistics.clues_total}</dd></div><div><dt>AI 提示</dt><dd data-stat="hint_count">{state.statistics.hint_count}</dd></div><div><dt>失误</dt><dd data-stat="mistake_count">{state.statistics.mistake_count}</dd></div><div><dt>隐藏发现</dt><dd data-stat="hidden_found">{state.statistics.hidden_found}/{state.statistics.hidden_total}</dd></div></dl></section>}
        {!visual && state.level_version === '3.4.0' && won && state.settlement && <section className="settlement-panel panel" aria-labelledby="settlement-title"><div className="panel-heading"><h2 id="settlement-title">本局结算</h2><span className="settlement-rating" data-stat="rating">{state.settlement.rating}</span></div><p>评级依据本局探索记录，评级不会影响通关。</p><dl className="statistics-grid"><div><dt>用时</dt><dd data-stat="elapsed_seconds">{durationLabel(state.settlement.elapsed_seconds)}</dd></div><div><dt>线索</dt><dd data-stat="clues_found">{state.settlement.clues_found}/{state.settlement.clues_total}</dd></div><div><dt>AI 提示</dt><dd data-stat="hint_count">{state.settlement.hint_count}</dd></div><div><dt>失误</dt><dd data-stat="mistake_count">{state.settlement.mistake_count}</dd></div><div><dt>隐藏发现</dt><dd data-stat="hidden_found">{state.settlement.hidden_found}/{state.settlement.hidden_total}</dd></div></dl></section>}
        {visual ? <RoomLoader state={state} view={selectedId} selectedItemId={selectedItemId} disabled={disabled || !!drawer} animation={visualReceipt} reducedMotion={presentation.reducedMotion}
          codes={codes} onCode={(id, value) => setCodes(current => ({ ...current, [id]: value }))} onError={setError}
          loginCredentials={loginCredentials} onLogin={(field, value) => setLoginCredentials(current => ({ ...current, [field]: value }))}
          sequenceDraft={sequenceDraft} onDraft={setSequenceDraft} onView={setSelectedId} onObject={visualObject} onAction={action}
          onItem={id => setSelectedItemId(current => current === id ? null : id)} onNotebook={() => setDrawer('notebook')} onAssistant={() => setDrawer('assistant')} onMenu={() => setDrawer('menu')}
          onReset={() => setConfirmation('reset')} onRecords={() => setDrawer('menu')}/> : <div className="game-grid">
          <aside className="inventory panel" aria-labelledby="inventory-title"><div className="panel-heading"><h2 id="inventory-title"><Icon kind="bag"/>我的背包</h2><span className="count">{state.inventory.length}</span></div><p className="panel-caption">收集的道具，会留在这里。</p>{state.inventory.length === 0 ? <div className="empty"><span className="empty-icon"><Icon kind="bag"/></span><p>背包还是空的</p><small>探索场景，寻找可以带走的物品。</small></div> : <div className="item-list">{state.inventory.map(item => <article className={`inventory-item ${selectedItemId === item.item_id ? 'item-selected' : ''}`} key={item.item_id}><h3><Icon kind="item"/>{item.name}</h3><p>{item.description}</p><button className="button item-select-button" aria-pressed={selectedItemId === item.item_id} disabled={disabled} onClick={() => setSelectedItemId(current => current === item.item_id ? null : item.item_id)}>{selectedItemId === item.item_id ? '取消选择' : '选择物品'}</button></article>)}</div>}<button className="button subtle inventory-refresh" disabled={pending || needsSync} onClick={() => action('get_inventory', {})}>查看背包</button></aside>
          <section className="scene panel" aria-labelledby="room-title"><div className="panel-heading"><div><p className="eyebrow">当前场景 / {state.room.room_id}</p><h2 id="room-title">{state.room.name}</h2></div><span className="scene-tag">{won ? '探索完成' : '探索中'}</span></div><p className="room-description">{state.room.description}</p><div className="lab-scene" data-room={state.room.room_id} data-powered={state.progress.power_on} aria-label="当前可见物件"><div className="scene-window" aria-hidden="true"><span/><span/><span/><span/></div><div className="scene-light" aria-hidden="true"/><div className="scene-table" aria-hidden="true"/><div className={`graybox-props props-${state.room.room_id}`} aria-hidden="true"><span className="prop-clock"/><span className="prop-workbench"/><span className="prop-cabinet"/><span className="prop-computer"/><span className="prop-panel"/><span className="prop-exit"/></div><div className={`object-grid object-grid-${state.room.room_id.toLowerCase()}`}>{state.objects.map((object, index) => <button className={`object-tile room-hotspot hotspot-${hotspotPosition[object.object_id] || 'fallback'} ${selected?.object_id === object.object_id ? 'selected' : ''}`} key={object.object_id} disabled={pending} onClick={() => selectObject(object.object_id)} aria-pressed={selected?.object_id === object.object_id}><span className={`object-illustration kind-${object.kind}`}><Icon kind={object.kind}/></span><span className="object-number">{String(index + 1).padStart(2, '0')}</span><strong>{object.name}</strong><small>{kindLabel[object.kind]}{state.observed_object_ids?.includes(object.object_id) ? ' · 已观察' : ''}</small></button>)}</div>{state.objects.length === 0 && <p className="scene-empty">{won ? '实验室的门已在身后。' : '这里暂时没有可观察的物件。'}</p>}</div>
            {selected && <section className="object-details" aria-labelledby="selected-title"><div className="detail-heading"><span className="small-icon"><Icon kind={selected.kind}/></span><div><small>选中的物件</small><h3 id="selected-title">{selected.name}</h3></div></div><p>{selected.description}</p><div className="object-actions">{selected.actions.some(affordance => affordance.tool === 'inspect') && <button className="button" disabled={pending || needsSync} onClick={() => action('inspect', selected.actions.find(affordance => affordance.tool === 'inspect')!.arguments)}>观察 <span aria-hidden="true">→</span></button>}<button className="button primary" disabled={pending || needsSync || !!won} onClick={() => interact(selected.object_id)}>互动 <span aria-hidden="true">→</span></button>{state.minigames?.circuit?.target_id === selected.object_id && state.minigames.circuit.status === 'completed' && <button className="button subtle" disabled={pending} onClick={() => setInteractionId(selected.object_id)}>查看线路板</button>}{state.minigames?.sequence?.target_id === selected.object_id && state.minigames.sequence.status === 'completed' && <button className="button subtle" disabled={pending} onClick={() => setInteractionId(selected.object_id)}>查看顺序</button>}{selectedItemId && <button className="button use-button" disabled={disabled} onClick={() => action('use_item', { item_id: selectedItemId, target_id: selected.object_id })}>使用物品 ↗</button>}</div>{interactionId === selected.object_id && selected.actions.some(affordance => affordance.tool === 'submit_code') && <form className="code-form" onSubmit={event => { event.preventDefault(); const affordance = selected.actions.find(item => item.tool === 'submit_code'); if (!affordance) return; const code = codes[selected.object_id] || ''; if (!/^[0-9]{1,16}$/.test(code)) { setError('请输入 1–16 位数字。'); return; } action(affordance.tool, { ...affordance.arguments, code }); }}><label htmlFor={`code-${selected.object_id}`}>输入你推理出的数字</label><div><input id={`code-${selected.object_id}`} type="text" inputMode="numeric" autoComplete="off" pattern="[0-9]{1,16}" maxLength={16} required placeholder="1–16 位数字" value={codes[selected.object_id] || ''} disabled={disabled} onChange={event => setCodes(current => ({ ...current, [selected.object_id]: event.target.value }))}/><button className="button primary" disabled={disabled}>提交</button></div></form>}{loginOpenId === selected.object_id && loginAffordance && <form className="login-form" onSubmit={event => { event.preventDefault(); action('submit_login', { target_id: loginAffordance.arguments.target_id, username: loginCredentials.username, password: loginCredentials.password }); }}><h4>登录终端</h4><label htmlFor="terminal-username">用户名</label><input id="terminal-username" name="username" autoComplete="username" value={loginCredentials.username} disabled={disabled} onChange={event => setLoginCredentials(current => ({ ...current, username: event.target.value }))}/><label htmlFor="terminal-password">密码</label><input id="terminal-password" name="password" type="password" autoComplete="current-password" value={loginCredentials.password} disabled={disabled} onChange={event => setLoginCredentials(current => ({ ...current, password: event.target.value }))}/><button className="button primary" disabled={disabled}>提交登录</button></form>}{interactionId === selected.object_id && !selected.actions.some(affordance => affordance.tool === 'submit_code' || affordance.tool === 'submit_login' || affordance.tool === 'submit_circuit' || affordance.tool === 'submit_sequence') && <p className="interaction-prompt">选择已发现的道具，或继续观察这个物件。</p>}{observation && <div className="observation"><span>观察记录</span><p>{observation}</p></div>}</section>}
            {selected && interactionId === selected.object_id && state.minigames?.circuit && state.minigames.circuit.target_id === selected.object_id && <section className="minigame-panel circuit-panel" aria-labelledby="circuit-title"><div className="minigame-heading"><div><p className="eyebrow">设备小游戏 · 线路连接</p><h3 id="circuit-title">将电源接到主系统</h3></div><span className={`minigame-status ${state.minigames.circuit.status === 'completed' ? 'is-complete' : ''}`}>{state.minigames.circuit.status === 'completed' ? '线路已确认' : '可调整'}</span></div><p className="minigame-instructions">点击模块可顺时针旋转90°。观察电源与主系统的方向端口，连接规则由设备确认。</p><CircuitBoard circuit={state.minigames.circuit} disabled={disabled} onRotate={moduleId => action('rotate_circuit', { target_id: state.minigames!.circuit!.target_id, module_id: moduleId })}/><div className="minigame-actions"><button className="button primary circuit-submit" disabled={disabled || state.minigames.circuit.status === 'completed'} onClick={() => action('submit_circuit', { target_id: state.minigames!.circuit!.target_id })}>提交线路</button></div></section>}
            {selected && interactionId === selected.object_id && state.minigames?.sequence && state.minigames.sequence.target_id === selected.object_id && <section className="minigame-panel sequence-panel" aria-labelledby="sequence-title"><div className="minigame-heading"><div><p className="eyebrow">设备小游戏 · 顺序操作</p><h3 id="sequence-title">选择控制设备的顺序</h3></div><span className={`minigame-status ${state.minigames.sequence.status === 'completed' ? 'is-complete' : ''}`}>{state.minigames.sequence.status === 'completed' ? '顺序已确认' : '临时草稿'}</span></div><p className="minigame-instructions">按你推理出的次序点选设备。草稿只保存在当前页面；提交后由设备判断结果。</p><ol className="sequence-draft" aria-label="当前顺序草稿">{sequenceDraft.map((deviceId, index) => { const device = state.minigames!.sequence!.devices.find(item => item.device_id === deviceId); return <li key={`${index}-${deviceId}`}><span>{index + 1}</span><strong>{device?.symbol} {device?.label || deviceId}</strong></li>; })}{sequenceDraft.length === 0 && <li className="sequence-draft-empty">尚未选择设备</li>}</ol><div className="sequence-devices" role="group" aria-label="可选择的控制设备">{state.minigames.sequence.devices.map(device => <button type="button" className="button sequence-device" key={device.device_id} data-device-id={device.device_id} disabled={disabled || state.minigames!.sequence!.status === 'completed' || sequenceDraft.length >= state.minigames!.sequence!.length} onClick={() => setSequenceDraft(current => current.length < state.minigames!.sequence!.length ? [...current, device.device_id] : current)} aria-label={`将${device.label}（${device.symbol}）加入当前顺序草稿`}><span aria-hidden="true">{device.symbol}</span>{device.label}</button>)}</div><div className="minigame-actions"><button type="button" className="button subtle sequence-clear" disabled={disabled || sequenceDraft.length === 0 || state.minigames.sequence.status === 'completed'} onClick={() => setSequenceDraft([])}>清除草稿</button><button type="button" className="button primary sequence-submit" disabled={disabled || sequenceDraft.length !== state.minigames.sequence.length || state.minigames.sequence.status === 'completed'} onClick={() => { const affordance = selected.actions.find(item => item.tool === 'submit_sequence'); if (affordance) action('submit_sequence', { ...affordance.arguments, device_ids: sequenceDraft }); }}>提交顺序</button></div></section>}
            <div className="exits"><h3>可见通道</h3>{state.exits.map(exit => <button className="exit-button" key={exit.destination_id} disabled={disabled} onClick={() => action('move', { destination_id: exit.destination_id })}><Icon kind="door"/><span>{exit.name}<small>尝试前往</small></span><span aria-hidden="true">→</span></button>)}{state.exits.length === 0 && <p className="muted">暂时没有可见通道。</p>}</div>
          </section>
          <aside className="clues panel" aria-labelledby="clues-title"><div className="panel-heading"><h2 id="clues-title"><Icon kind="clue"/>线索笔记</h2><span className="count">{state.clues.length}</span></div><p className="panel-caption">只记录你亲自发现的信息。</p>{state.clues.length === 0 ? <div className="empty"><span className="empty-icon"><Icon kind="clue"/></span><p>第一页，等待发现</p><small>查看物件后，新的线索会自动记入笔记。</small></div> : <ol className="clue-list">{state.clues.map((clue, index) => <li key={clue.clue_id} id={`clue-${clue.clue_id}`} tabIndex={-1}><div className="clue-heading"><span>{String(index + 1).padStart(2, '0')}</span><h3>{clue.title}</h3></div><p>{clue.text}</p></li>)}</ol>}<div className="notebook-tip">先观察，再尝试。<br/>答案可能就在已经发现的细节里。</div></aside>
        </div>}
        {visual && drawer && <button className="drawer-backdrop" aria-label="关闭面板" onClick={() => setDrawer(null)}/>}
        {visual && drawer === 'notebook' && <Notebook state={state} page={notebookPage} onPage={setNotebookPage} onClose={() => setDrawer(null)}/>}
        <div className={`support-grid ${visual ? 'visual-support' : ''}`} data-drawer={drawer || 'closed'} aria-hidden={visual && confirmation ? true : undefined}>
          <div className="assistant-container" hidden={visual && drawer !== 'assistant'} role={visual && drawer === 'assistant' ? 'dialog' : undefined} aria-modal={visual && drawer === 'assistant' ? true : undefined} aria-labelledby={visual ? 'assistant-title' : undefined} onKeyDown={visual ? trapPanelFocus : undefined}>{visual && <button className="button drawer-close" onClick={() => setDrawer(null)}>关闭伙伴</button>}<Assistant key={state.session_id} session={session!} state={state} manualPending={pending} needsSync={needsSync} onState={(next, reconciled = false) => apply(next, false, reconciled)} onUncertain={value => { if (stateRef.current?.session_id === state.session_id) setNeedsSync(value); }} onForbidden={invalidateSession} onReference={visual ? openReference : undefined}/></div>
          <section className="save-panel panel" aria-labelledby="save-title" hidden={visual && drawer !== 'menu'} role={visual && drawer === 'menu' ? 'dialog' : undefined} aria-modal={visual && drawer === 'menu' ? true : undefined} onKeyDown={visual ? trapPanelFocus : undefined}>
            {visual && <button className="button drawer-close" onClick={() => setDrawer(null)}>继续游戏</button>}
            <h2 id="save-title">游戏进度</h2>
            {visual && <div className="presentation-settings"><button className="button sound-toggle" aria-pressed={presentation.muted} onClick={() => presentation.setMuted(value => !value)}>{presentation.muted ? '开启声音' : '静音'}</button><label><input type="checkbox" className="motion-toggle" checked={presentation.manualReduced || presentation.systemReduced} disabled={presentation.systemReduced} onChange={event => presentation.setManualReduced(event.target.checked)}/>减少动态效果</label></div>}
            {visual && state.statistics && <dl className="statistics-grid menu-statistics"><div><dt>用时</dt><dd data-stat="elapsed_seconds">{durationLabel(state.settlement?.elapsed_seconds ?? Math.floor(Math.max(0, clockNow - Date.parse(state.statistics.started_at)) / 1000))}</dd></div><div><dt>线索</dt><dd data-stat="clues_found">{state.statistics.clues_found}/{state.statistics.clues_total}</dd></div><div><dt>AI 提示</dt><dd data-stat="hint_count">{state.statistics.hint_count}</dd></div><div><dt>失误</dt><dd data-stat="mistake_count">{state.statistics.mistake_count}</dd></div><div><dt>隐藏发现</dt><dd data-stat="hidden_found">{state.statistics.hidden_found}/{state.statistics.hidden_total}</dd></div></dl>}
            {visual && <div className="menu-actions"><button className="button" disabled={pending} onClick={sync}>同步进度</button><button className="button" disabled={pending} onClick={() => setConfirmation('new')}>新游戏</button></div>}
            <p>存档保存在本机并跟随当前游戏。每次保存都会新增一份，不覆盖已有记录；新游戏会使用另一份存档列表。</p>
            <form className="save-slot-create" onSubmit={event => { event.preventDefault(); saveNewSlot(); }}>
              <label htmlFor="save-slot-name">存档名称（可选，最多40字）</label>
              <div className="save-slot-create-row"><input id="save-slot-name" className="save-slot-name" maxLength={40} value={saveName} disabled={pending || needsSync} placeholder="留空由系统命名" onChange={event => setSaveName(event.target.value)}/><button type="submit" className="button primary save-slot-create-button" disabled={pending || needsSync}>保存新存档</button></div>
            </form>
            <div className="save-slot-list" role="list" aria-label="当前游戏的存档列表">
              {saveSlots.map(slot => <article className={`save-slot ${slot.kind === 'legacy' ? 'save-slot-legacy' : ''}`} role="listitem" key={slot.save_id} data-save-id={slot.save_id}>
                <div className="save-slot-heading"><h3>{slot.name}</h3><span className="save-slot-kind">{slot.kind === 'legacy' ? '旧版单槽' : '独立存档'}</span></div>
                <p className="save-slot-meta"><time dateTime={slot.saved_at}>{saveTimeLabel(slot.saved_at)}</time><span>{slot.room_id ? saveRoomLabel[slot.room_id] : '房间未知'}</span><span>{slot.status === 'won' ? '已通关' : slot.status === 'playing' ? '进行中' : '状态未记录'}</span><span>{slot.clues_found === null ? '线索数未记录' : `${slot.clues_found} 条线索`}</span></p>
                <small>关卡 {slot.level_version}</small>
                <button type="button" className="button save-slot-restore" aria-label={`读取存档：${slot.name}`} disabled={pending || needsSync} onClick={() => requestSlotRestore(slot)}>读取</button>
              </article>)}
              {!saveSlots.length && !saveListError && <p className="no-save">还没有存档。保存后可在这里选择任一时刻读取。</p>}
            </div>
            {saveListError && <p className="error save-list-error" role="alert">{saveListError}</p>}
            <details className="legacy-save-controls" open>
              <summary>旧版单槽兼容操作</summary>
              <p>每次保存会替换这份旧版存档；上方新建的存档会各自保留。旧版存档也会出现在上方列表。</p>
              {state.save ? <div className="save-summary"><span className="saved-badge">已有旧版单槽</span><p>保存时间：<time dateTime={state.save.saved_at}>{savedTime}</time></p><small>保存时进度 {state.save.source_revision} · 关卡 {state.save.level_version}</small></div> : <p className="no-save">尚无旧版单槽存档。</p>}
              <div className="save-actions"><button className="button" disabled={pending || needsSync} onClick={() => control('save')}>保存进度</button><button className="button" disabled={pending || needsSync || !state.save} onClick={() => setConfirmation('restore')}>恢复存档</button><button className="button subtle" disabled={pending || needsSync} onClick={() => setConfirmation('reset')}>重新开始</button></div>
            </details>
          </section>
        </div>
        {history.length > 0 && <details className="history"><summary>最近的行动记录 <span>{history.length}</span></summary><ol>{history.map(entry => <li key={entry.id}>{entry.text}</li>)}</ol></details>}
      </>}
      <footer><span>校园实验室 · 认真观察，大胆推理</span><span>{state ? `关卡 ${state.level_version} · 进度 ${state.revision}` : '本地探索 · 手动游玩'}</span></footer>
    </main>
    {visualReceipt?.tool === 'move' && visualReceipt.changed && <div className="room-transition" key={visualReceipt.event_id} aria-hidden="true"/>}
    <dialog ref={dialogRef} onCancel={() => setConfirmation(null)} onClose={() => { setConfirmation(null); if (confirmation === 'slot-restore') setRestoreSaveId(null); }} aria-labelledby="confirmation-title"><h2 id="confirmation-title">{confirmation === 'new' ? '开始新的游戏？' : confirmation === 'slot-restore' ? '读取指定存档？' : confirmation === 'restore' ? '恢复已保存的进度？' : '重新开始当前游戏？'}</h2><p>{confirmation === 'new' ? '当前标签页将切换到新游戏，旧会话将无法从这里继续。' : confirmation === 'slot-restore' ? `当前进度将替换为“${saveSlots.find(slot => slot.save_id === restoreSaveId)?.name || '所选存档'}”保存的状态。读取后会清除当前临时输入和顺序草稿。` : confirmation === 'restore' ? '当前进度将替换为旧版单槽存档中的场景、道具和已发现线索。单槽存档会保留。' : '这会清空当前探索进度和线索；已有存档仍可读取。'} </p><div className="dialog-actions"><button className="button" autoFocus onClick={() => { setConfirmation(null); setRestoreSaveId(null); }}>取消</button><button className="button primary" disabled={pending} onClick={() => confirmation === 'new' ? create() : confirmation === 'slot-restore' ? restoreSelectedSlot() : control(confirmation === 'restore' ? 'restore' : 'reset')}>{confirmation === 'slot-restore' ? '读取此存档' : confirmation === 'restore' ? '确认恢复' : '确认开始'}</button></div></dialog>
  </div>;
}

