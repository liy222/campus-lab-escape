import { useEffect, useRef, useState } from 'react';
import { api, ApiError, readSession, storeSession, type Args, type Session, type Tool, type VisibleState } from './api';
import Assistant from './Assistant';

const kindLabel = { clue: '可观察', container: '容器', door: '通道', device: '设备', item: '物品' };
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
export default function App() {
  const [session, setSession] = useState<Session | null>(readSession);
  const [state, setState] = useState<VisibleState | null>(null);
  const stateRef = useRef<VisibleState | null>(null);
  const retiredGenerations = useRef(new Set<string>());
  const busy = useRef(false);
  const [pending, setPending] = useState(false);
  const [needsSync, setNeedsSync] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [codes, setCodes] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [observation, setObservation] = useState('');
  const [confirmation, setConfirmation] = useState<'new' | 'reset' | 'restore' | null>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [history, setHistory] = useState<{ id: string; text: string }[]>([]);
  const selected = state?.objects.find(object => object.object_id === selectedId) || state?.objects[0];
  useEffect(() => { if (confirmation) dialogRef.current?.showModal(); else dialogRef.current?.close(); }, [confirmation]);
  function apply(next: VisibleState, replace = false, reconciled = false): boolean {
    const previous = stateRef.current;
    if (!replace && previous && (next.session_id !== previous.session_id || next.revision < previous.revision || retiredGenerations.current.has(next.generation))) return false;
    if (replace) retiredGenerations.current.clear();
    else if (previous && previous.generation !== next.generation) retiredGenerations.current.add(previous.generation);
    if (previous && previous.revision !== next.revision) setCodes({});
    if (!previous || replace || previous.generation !== next.generation) { setCodes({}); setObservation(''); setSelectedId(null); setHistory([]); }
    stateRef.current = next; setState(next); if (replace || reconciled) setNeedsSync(false); return true;
  }
  function invalidateSession(sessionId: string) {
    if (stateRef.current && stateRef.current.session_id !== sessionId) return;
    storeSession(null); setSession(null); stateRef.current = null; setState(null); setCodes({}); setHistory([]); setObservation(''); setSelectedId(null); setNeedsSync(false); retiredGenerations.current.clear();
  }
  async function execute(work: () => Promise<void>, reconcile = false) {
    if (busy.current) return;
    busy.current = true; setPending(true); setError(''); setNotice('');
    try { await work(); }
    catch (caught) {
      const failure = caught instanceof ApiError ? caught : new ApiError('CLIENT_ERROR', '操作未完成，请稍后重试。');
      if (failure.visibleState) apply(failure.visibleState);
      if (failure.code === 'FORBIDDEN_SESSION' && session) invalidateSession(session.session_id);
      else if (reconcile && session && ['NETWORK_ERROR', 'SERVICE_UNAVAILABLE'].includes(failure.code)) {
        setNeedsSync(true);
        try { const response = await api.state(session); apply(response.data.visible_state, false, true); setNotice('已同步服务器上的实际进度，请确认当前场景和存档后再操作。'); } catch { setNotice('尚未确认这次操作的结果。请先同步进度，确认后再继续。'); }
      }
      setError(failure.message);
    } finally { busy.current = false; setPending(false); }
  }
  function create() {
    setConfirmation(null);
    void execute(async () => { const response = await api.create(); const nextSession = { session_id: response.data.session_id, token: response.data.token }; storeSession(nextSession); setSession(nextSession); apply(response.data.visible_state, true); setNotice('游戏已开始。选择场景中的物件，慢慢寻找线索。'); });
  }
  function sync() { if (!session) return; void execute(async () => { const response = await api.state(session); apply(response.data.visible_state, false, true); setNotice('已同步当前进度。'); }); }
  function action(tool: Tool, args: Args) {
    if (!session || !stateRef.current || needsSync) return;
    const current = stateRef.current;
    void execute(async () => {
      const response = await api.action(session, current, tool, args);
      if (!apply(response.data.visible_state)) return;
      if (current.generation !== response.data.visible_state.generation) { setNotice('游戏进度已更新，请依据当前场景继续探索。'); return; }
      const receipt = response.data.receipt; setNotice(receipt.message); setObservation(receipt.observation || '');
      setHistory(entries => [{ id: receipt.event_id, text: receipt.message }, ...entries.filter(entry => entry.id !== receipt.event_id)].slice(0, 5));
      if (tool === 'submit_code') setCodes({});
    }, true);
  }
  function control(operation: 'reset' | 'save' | 'restore') {
    setConfirmation(null);
    if (!session || !stateRef.current || needsSync) return;
    const current = stateRef.current;
    void execute(async () => { const response = await api.control(session, current, operation); if (apply(response.data.visible_state)) setNotice(response.data.message); }, true);
  }
  const won = state?.status === 'won';
  const disabled = pending || needsSync || !!won;
  const savedAt = state?.save ? new Date(state.save.saved_at) : null;
  const savedTime = savedAt && !Number.isNaN(savedAt.getTime()) ? savedAt.toLocaleString('zh-CN', { hour12: false }) : state?.save?.saved_at;
  return <div className="app-shell">
    <a className="skip-link" href="#game">跳到游戏内容</a>
    <header className="topbar"><a className="brand" href="#game"><span className="brand-mark"><Icon kind="device"/></span><span>逃离校园实验室<small>CAMPUS LAB · ESCAPE</small></span></a><div className="top-actions"><span className="local-badge">● 本地游戏</span><button className="button subtle" disabled={pending} onClick={() => session ? setConfirmation('new') : create()}>新游戏</button>{session && <button className="button subtle" disabled={pending} onClick={sync}>{state ? '同步进度' : '继续当前游戏'}</button>}</div></header>
    <main id="game"><div className="page-heading"><div><p className="eyebrow">一次校园里的小小冒险</p><h1>{won ? '你找到出口了。' : '观察。发现。离开。'}</h1><p className="intro">每个不起眼的物件，都可能藏着下一步。</p></div><div className="chapter-badge"><span>{state?.room.room_id || 'START'}</span><small>{state ? '当前所在' : '准备探索'}</small></div></div>
      <div className="feedback" aria-live="polite" aria-atomic="true">{pending && <p className="pending"><span className="spinner"/>正在处理，请稍候…</p>}{error && <p className="error" role="alert">{error}</p>}{notice && <p className="notice">{notice}</p>}</div>
      {!state ? <section className="welcome panel"><div className="welcome-art" aria-hidden="true"><div className="art-window"><span/><span/><span/><span/></div><div className="art-desk"/><div className="art-note"/><div className="art-lamp"/><div className="art-plant"/></div><div className="welcome-copy"><p className="eyebrow">实验室的灯，还亮着</p><h2>从这里开始探索</h2><p>查看房间里的物件，记录发现的线索。收集道具、尝试你的推理，打开通往下一个房间的门。</p><div className="welcome-buttons"><button className="button primary" disabled={pending} onClick={() => session ? setConfirmation('new') : create()}>开始新游戏 →</button>{session && <button className="button" disabled={pending} onClick={sync}>继续当前游戏</button>}</div><small>进度与当前浏览器标签页关联，刷新后可以继续。</small></div></section> : <>
        {won && <section className="victory" role="status"><Icon kind="spark"/><div><h2>成功逃离实验室</h2><p>所有已发现的线索，仍保留在笔记中。</p></div></section>}
        <div className="game-grid">
          <aside className="inventory panel" aria-labelledby="inventory-title"><div className="panel-heading"><h2 id="inventory-title"><Icon kind="bag"/>我的背包</h2><span className="count">{state.inventory.length}</span></div><p className="panel-caption">收集的道具，会留在这里。</p>{state.inventory.length === 0 ? <div className="empty"><span className="empty-icon"><Icon kind="bag"/></span><p>背包还是空的</p><small>探索场景，寻找可以带走的物品。</small></div> : <div className="item-list">{state.inventory.map(item => <article className="inventory-item" key={item.item_id}><h3><Icon kind="item"/>{item.name}</h3><p>{item.description}</p>{item.usable_targets.map(target => <button className="button use-button" key={target} disabled={disabled} onClick={() => action('use_item', { item_id: item.item_id, target_id: target })}>使用于{state.objects.find(object => object.object_id === target)?.name || '当前目标'} ↗</button>)}</article>)}</div>}<button className="button subtle inventory-refresh" disabled={pending || needsSync} onClick={() => action('get_inventory', {})}>查看背包</button><div className="status-note">● {state.progress.power_on ? '实验室已供电' : '设备供电尚未完成'}<br/>● {state.progress.check_done ? '出口检查已完成' : '出口检查尚未完成'}</div></aside>
          <section className="scene panel" aria-labelledby="room-title"><div className="panel-heading"><div><p className="eyebrow">当前场景 / {state.room.room_id}</p><h2 id="room-title">{state.room.name}</h2></div><span className="scene-tag">{won ? '探索完成' : '探索中'}</span></div><p className="room-description">{state.room.description}</p><div className="lab-scene" data-room={state.room.room_id} data-powered={state.progress.power_on} aria-label="当前可见物件"><div className="scene-window" aria-hidden="true"><span/><span/><span/><span/></div><div className="scene-light" aria-hidden="true"/><div className="scene-table" aria-hidden="true"/><div className="object-grid">{state.objects.map((object, index) => <button className={`object-tile ${selected?.object_id === object.object_id ? 'selected' : ''}`} key={object.object_id} disabled={pending} onClick={() => { setSelectedId(object.object_id); setObservation(''); }} aria-pressed={selected?.object_id === object.object_id}><span className={`object-illustration kind-${object.kind}`}><Icon kind={object.kind}/></span><span className="object-number">{String(index + 1).padStart(2, '0')}</span><strong>{object.name}</strong><small>{kindLabel[object.kind]}</small></button>)}</div>{state.objects.length === 0 && <p className="scene-empty">{won ? '实验室的门已在身后。' : '这里暂时没有可观察的物件。'}</p>}</div>
            {selected && <section className="object-details" aria-labelledby="selected-title"><div className="detail-heading"><span className="small-icon"><Icon kind={selected.kind}/></span><div><small>选中的物件</small><h3 id="selected-title">{selected.name}</h3></div></div><p>{selected.description}</p><div className="object-actions">{selected.actions.map((affordance, index) => affordance.requires_code ? <form className="code-form" key={`${selected.object_id}-${index}`} onSubmit={event => { event.preventDefault(); const code = codes[selected.object_id] || ''; if (!/^[0-9]{1,16}$/.test(code)) { setError('请输入 1–16 位数字密码。'); return; } action(affordance.tool, { ...affordance.arguments, code }); }}><label htmlFor={`code-${selected.object_id}`}>{selected.name}密码</label><div><input id={`code-${selected.object_id}`} type="text" inputMode="numeric" autoComplete="off" pattern="[0-9]{1,16}" maxLength={16} required placeholder="输入你推理出的密码" value={codes[selected.object_id] || ''} disabled={disabled} onChange={event => setCodes(current => ({ ...current, [selected.object_id]: event.target.value }))}/><button className="button primary" disabled={disabled}>{affordance.label}</button></div></form> : <button className={`button ${affordance.tool === 'take' ? 'primary' : ''}`} key={`${selected.object_id}-${index}`} disabled={pending || needsSync || (!!won && !['inspect', 'get_inventory'].includes(affordance.tool))} onClick={() => action(affordance.tool, affordance.arguments)}>{affordance.label} <span aria-hidden="true">→</span></button>)}</div>{observation && <div className="observation"><span>观察记录</span><p>{observation}</p></div>}</section>}
            <div className="exits"><h3>前往其他房间</h3>{state.exits.map(exit => <button className="exit-button" key={exit.destination_id} disabled={disabled || !exit.unlocked} onClick={() => action('move', { destination_id: exit.destination_id })}><Icon kind="door"/><span>{exit.name}<small>{exit.unlocked ? '通道已打开' : '通道尚未解锁'}</small></span><span aria-hidden="true">{exit.unlocked ? '→' : '锁定'}</span></button>)}{state.exits.length === 0 && <p className="muted">没有其他通道。</p>}</div>
          </section>
          <aside className="clues panel" aria-labelledby="clues-title"><div className="panel-heading"><h2 id="clues-title"><Icon kind="clue"/>线索笔记</h2><span className="count">{state.clues.length}</span></div><p className="panel-caption">只记录你亲自发现的信息。</p>{state.clues.length === 0 ? <div className="empty"><span className="empty-icon"><Icon kind="clue"/></span><p>第一页，等待发现</p><small>查看物件后，新的线索会自动记入笔记。</small></div> : <ol className="clue-list">{state.clues.map((clue, index) => <li key={clue.clue_id} id={`clue-${clue.clue_id}`} tabIndex={-1}><div className="clue-heading"><span>{String(index + 1).padStart(2, '0')}</span><h3>{clue.title}</h3></div><p>{clue.text}</p></li>)}</ol>}<div className="notebook-tip">先观察，再尝试。<br/>答案可能就在已经发现的细节里。</div></aside>
        </div>
        <div className="support-grid"><Assistant key={state.session_id} session={session!} state={state} manualPending={pending} needsSync={needsSync} onState={(next, reconciled = false) => apply(next, false, reconciled)} onUncertain={value => { if (stateRef.current?.session_id === state.session_id) setNeedsSync(value); }} onForbidden={invalidateSession}/><section className="save-panel panel" aria-labelledby="save-title"><h2 id="save-title">游戏进度</h2><p>刷新后可继续当前游戏。每次保存会覆盖本会话的单个存档。</p>{state.save ? <div className="save-summary"><span className="saved-badge">已有存档</span><p>保存时间：<time dateTime={state.save.saved_at}>{savedTime}</time></p><small>保存时进度 {state.save.source_revision} · 关卡 {state.save.level_version}</small></div> : <p className="no-save">尚无存档，保存后才能恢复。</p>}<div className="save-actions"><button className="button" disabled={pending || needsSync} onClick={() => control('save')}>保存进度</button><button className="button" disabled={pending || needsSync || !state.save} onClick={() => setConfirmation('restore')}>恢复存档</button><button className="button subtle" disabled={pending || needsSync} onClick={() => setConfirmation('reset')}>重新开始</button></div></section></div>
        {history.length > 0 && <details className="history"><summary>最近的行动记录 <span>{history.length}</span></summary><ol>{history.map(entry => <li key={entry.id}>{entry.text}</li>)}</ol></details>}
      </>}
      <footer><span>校园实验室 · 认真观察，大胆推理</span><span>{state ? `关卡 ${state.level_version} · 进度 ${state.revision}` : '本地探索 · 手动游玩'}</span></footer>
    </main>
    <dialog ref={dialogRef} onCancel={() => setConfirmation(null)} onClose={() => setConfirmation(null)} aria-labelledby="confirmation-title"><h2 id="confirmation-title">{confirmation === 'new' ? '开始新的游戏？' : confirmation === 'restore' ? '恢复已保存的进度？' : '重新开始当前游戏？'}</h2><p>{confirmation === 'new' ? '当前标签页将切换到新游戏，旧会话将无法从这里继续。' : confirmation === 'restore' ? '当前进度将替换为单槽存档中的场景、道具和已发现线索。存档会保留。' : '这会清空当前探索进度和线索；已有存档仍可恢复。'}</p><div className="dialog-actions"><button className="button" autoFocus onClick={() => setConfirmation(null)}>取消</button><button className="button primary" disabled={pending} onClick={() => confirmation === 'new' ? create() : control(confirmation === 'restore' ? 'restore' : 'reset')}>{confirmation === 'restore' ? '确认恢复' : '确认开始'}</button></div></dialog>
  </div>;
}

