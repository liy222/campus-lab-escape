import { useEffect, useMemo, useRef, useState } from 'react';
import Assistant from '../Assistant';
import catalog from '../assets/generated-catalog.json';
import { ApiError, type ActionArguments, type SaveSlot, type Tool, type VisibleState } from '../api';
import { trapPanelFocus } from '../components/panelFocus';
import { localSession, type Level, type Run, type V5Client } from './client';
import GeneratedScene from './GeneratedScene';
import CircuitBoard from './CircuitBoard';
import { buildSceneModel } from './visual/scene';
import type { GeneratedState, SceneModel } from './visual/types';
import './v5.css';

type Drawer = 'notebook' | 'assistant' | 'saves' | null;

export default function GeneratedPlay({ client, run, level }: { client: V5Client; run: Run; level?: Level }) {
  const api = useRef(client.classic(run.session_id)).current, session = localSession(run.session_id);
  const [state, setState] = useState<GeneratedState | null>(null), current = useRef<GeneratedState | null>(null), retired = useRef(new Set<string>());
  const [pending, setPending] = useState(false), busy = useRef(false), [error, setError] = useState(''), [notice, setNotice] = useState(''), [uncertain, setUncertain] = useState(false);
  const [view, setView] = useState<string | null>(null), [item, setItem] = useState<string | null>(null), [drawer, setDrawer] = useState<Drawer>(null);
  const [code, setCode] = useState(''), [sequence, setSequence] = useState<string[]>([]), [saveName, setSaveName] = useState(''), [slots, setSlots] = useState<SaveSlot[]>([]);
  const [confirm, setConfirm] = useState<{ kind: 'reset' | 'restore' | 'delete'; slot?: SaveSlot } | null>(null), dialog = useRef<HTMLDialogElement>(null), alive = useRef(true), panelTrigger = useRef<HTMLElement | null>(null);
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [victoryOpen, setVictoryOpen] = useState(true);

  function apply(next: GeneratedState, reconciled = false) {
    const old = current.current;
    if (!alive.current || next.session_id !== run.session_id || (old && (next.revision < old.revision || retired.current.has(next.generation)))) return false;
    if (old?.generation !== next.generation) {
      if (old) retired.current.add(old.generation);
      setView(null); setDrawer(null); setItem(null); setCode(''); setSequence([]); setCredentials({ username: '', password: '' }); setConfirm(null);
    } else if (old?.room.room_id !== next.room.room_id) {
      setView(null); setItem(null); setCode(''); setSequence([]);
    }
    setView(open => open && !next.objects.some(object => object.object_id === open) ? null : open);
    current.current = next; setState(next);
    if (reconciled) setUncertain(false);
    return true;
  }
  async function saves() { const r = await api.saveSlots(session); if (alive.current && r.data.visible_state.generation === current.current?.generation) setSlots(r.data.slots); }
  async function sync() { const r = await api.state(session); if (apply(r.data.visible_state as GeneratedState, true)) await saves(); }
  async function work(fn: () => Promise<void>) {
    if (busy.current) return;
    busy.current = true; setPending(true); setError('');
    try { await fn(); } catch (e) {
      if (!alive.current) return;
      const problem = e instanceof ApiError ? e : new ApiError('CLIENT_ERROR', '操作未完成');
      if (problem.visibleState) apply(problem.visibleState as GeneratedState);
      setError(problem.message);
      if (['NETWORK_ERROR', 'SERVICE_UNAVAILABLE', 'STALE_STATE', 'STALE_GENERATION'].includes(problem.code)) setUncertain(true);
    } finally { busy.current = false; if (alive.current) setPending(false); }
  }
  useEffect(() => { alive.current = true; void work(sync); return () => { alive.current = false; }; }, []);
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !dialog.current?.open) {
        if (drawer) setDrawer(null); else setView(null);
      }
    };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [drawer]);
  useEffect(() => { if (confirm) dialog.current?.showModal(); else dialog.current?.close(); }, [confirm]);
  useEffect(() => {
    if (view || drawer) {
      if (!panelTrigger.current) panelTrigger.current = document.activeElement as HTMLElement;
      document.querySelector<HTMLElement>('.v5-overlay button')?.focus();
    } else if (panelTrigger.current) { panelTrigger.current.focus(); panelTrigger.current = null; }
  }, [view, drawer]);
  useEffect(() => { setVictoryOpen(true); }, [state?.status]);

  const sceneInput = useMemo(() => state ? {
    level_id: state.level_id,
    theme: level?.theme ?? null,
    room: state.room,
    objects: state.objects,
  } : null, [state?.level_id, state?.room, state?.objects, level?.theme]);
  const model = useMemo(() => sceneInput ? buildSceneModel(sceneInput) : null, [sceneInput]);
  const lastRoom = useRef<SceneModel | null>(null);
  if (model && model.objects.length) lastRoom.current = model;
  const sceneModel = model && model.objects.length ? model : lastRoom.current ?? model;

  function openDrawer(kind: Exclude<Drawer, null>) { panelTrigger.current = document.activeElement as HTMLElement; setView(null); setDrawer(kind); }
  function action(tool: Tool, args: ActionArguments) {
    if (!current.current || uncertain) return;
    const old = current.current;
    void work(async () => {
      const r = await api.action(session, old, tool, args);
      if (!apply(r.data.visible_state as GeneratedState)) return;
      setNotice([r.data.receipt.message, r.data.receipt.observation].filter(Boolean).join(' '));
      if (tool === 'submit_code') setCode('');
      if (tool === 'submit_sequence') setSequence([]);
    });
  }
  function inspect(id: string) {
    if (pending || drawer) return;
    panelTrigger.current = document.activeElement as HTMLElement;
    setView(id); setCode(''); setSequence([]);
    if (item) { action('use_item', { item_id: item, target_id: current.current?.objects.find(object => object.object_id === id)?.target_id || id }); setItem(null); }
    else action('inspect', { object_id: id });
  }
  async function confirmed() {
    if (!state || !confirm) return;
    const choice = confirm;
    setConfirm(null);
    await work(async () => {
      const r = choice.kind === 'reset' ? await api.control(session, state, 'reset') : choice.kind === 'restore' ? await api.restoreSaveSlot(session, state, choice.slot!.save_id) : await api.deleteSaveSlot(session, state, choice.slot!.save_id);
      if (apply(r.data.visible_state as GeneratedState)) { await saves(); setNotice(r.data.message); }
    });
  }
  if (!state) return <div className="v5-game v5-loading" aria-busy={pending}><p role="status">正在读取账户内进度…</p>{error && <p className="v5-alert" role="alert">{error}</p>}<button onClick={() => void work(sync)} disabled={pending}>重试读取</button></div>;

  const object = state.objects.find(candidate => candidate.object_id === view);
  const disabled = pending || uncertain || state.status === 'won';
  const circuits = state.minigames?.circuits || [state.minigames?.circuit].filter(Boolean);
  const sequences = state.minigames?.sequences || [state.minigames?.sequence].filter(Boolean);
  const circuit = circuits.find(board => board?.target_id === (object?.target_id || view));
  const seq = sequences.find(board => board?.target_id === (object?.target_id || view));
  const sceneObject = model?.objects.find(candidate => candidate.object_id === view);
  const legacyArt = !sceneObject?.closeup ? catalog.assets.find(asset => asset.id === object?.art_id) : null;

  return <main className="v5-game" aria-busy={pending}>
    <header className="v5-hud">
      <div className="v5-hud-title">
        <p className="v5-kicker">{model?.themeName ? `${model.themeName} · 校园探索` : '校园探索'} · {state.status === 'won' ? '已完成' : '现场勘察'}</p>
        <h1>{level?.title || state.room.name}</h1>
        <p className="v5-hud-room">{state.room.name}</p>
      </div>
      <div className="v5-hud-actions">
        <button onClick={() => openDrawer('notebook')}>笔记<span>{state.clues.length}</span></button>
        <button onClick={() => openDrawer('assistant')}>探索伙伴</button>
        <button onClick={() => { openDrawer('saves'); void work(saves); }}>进度与存档</button>
      </div>
    </header>

    <div className="v5-feedback" aria-live="polite">
      {pending && <p>正在处理…</p>}
      {error && <p className="v5-alert" role="alert">{error}</p>}
      {notice && <p className="v5-notice">{notice}</p>}
      {uncertain && <button onClick={() => void work(sync)} disabled={pending}>同步实际进度</button>}
    </div>

    <div className="v5-stage">
      {sceneModel && <GeneratedScene model={sceneModel} disabled={disabled || Boolean(drawer) || Boolean(view) || Boolean(confirm)} onObject={inspect} roomName={state.room.name} />}
      <div className="v5-stage-caption" aria-hidden="true"><span>{model?.themeName ? `${model.themeName} · 雨夜` : '通用校园手绘'}</span><span>点按场景中的光点查看物件</span></div>
      {state.status === 'won' && victoryOpen && <section className="v5-victory" role="status" aria-label="探索结算">
        <p className="v5-kicker">探索完成 / CLEARED</p>
        <h2>你找到了出口。</h2>
        <p className="v5-victory-lead">{state.room.name}的雨声还在，观测记录已经归档。</p>
        {state.settlement && <dl className="v5-stats">
          <div><dt>用时</dt><dd>{Math.floor(state.settlement.elapsed_seconds / 60)} 分</dd></div>
          <div><dt>线索</dt><dd>{state.settlement.clues_found}</dd></div>
          <div><dt>提示</dt><dd>{state.settlement.hint_count}</dd></div>
          <div><dt>评级</dt><dd>{state.settlement.rating}</dd></div>
        </dl>}
        <div className="v5-victory-actions">
          <button onClick={() => openDrawer('saves')}>查看存档</button>
          <button className="v5-quiet" onClick={() => setVictoryOpen(false)}>再看一眼场景</button>
        </div>
      </section>}
      <div className="v5-stage-foot">
        <p className="v5-room-note"><span aria-hidden="true">⌖</span>{state.room.description}</p>
        <nav className="v5-exits" aria-label="可见通道">
          {state.exits.map(exit => <button key={exit.destination_id} disabled={disabled || Boolean(view) || Boolean(drawer)} onClick={() => action('move', { destination_id: exit.destination_id })}>{exit.name}<span aria-hidden="true">→</span></button>)}
        </nav>
        {state.status === 'won' && !victoryOpen && <button className="v5-reopen" onClick={() => setVictoryOpen(true)}>重看结算</button>}
      </div>
    </div>

    <section className="v5-tray" aria-label="随身物品与档案">
      <div className="v5-inventory">
        <strong>随身物品</strong>
        {state.inventory.length === 0 && <span className="v5-empty">暂时没有物品</span>}
        {state.inventory.map(entry => <button key={entry.item_id} disabled={disabled || Boolean(view) || Boolean(drawer)} aria-pressed={item === entry.item_id} className={item === entry.item_id ? 'is-selected' : ''} onClick={() => setItem(item === entry.item_id ? null : entry.item_id)}>{entry.name}{item === entry.item_id ? ' · 已选中' : ''}</button>)}
        {item && <button className="v5-quiet" onClick={() => setItem(null)}>取消选择</button>}
      </div>
      <details className="v5-story">
        <summary>探索档案 <span>{level?.theme ? '创作主题与故事' : '本关故事'}</span></summary>
        {level?.theme && <div className="v5-theme-brief"><small>你的创作主题</small><p>{level.theme}</p></div>}
        {level?.story ? <p className="v5-story-text">{level.story}</p> : <p>{state.room.description}</p>}
        <small className="v5-art-note">{model?.themeName ? `当前画面使用「${model.themeName}」主题素材，仅覆盖天文社相关主题。` : '当前主题尚未提供专属素材，画面使用通用校园手绘，主题由故事、物件与线索呈现。'}</small>
      </details>
    </section>

    {(object || drawer) && <div className={`v5-overlay ${circuit ? 'has-circuit' : ''}`} role="dialog" aria-modal="true" aria-label={object?.name || '游戏面板'} onKeyDown={trapPanelFocus}>
      <section className="v5-sheet">
        <button className="v5-close" onClick={() => { setView(null); setDrawer(null); }}>关闭面板</button>
        {object && <>
          <p className="v5-kicker">{object.kind === 'item' ? '可携带物品' : '物件特写'}</p>
          <h2>{object.name}</h2>
          {object.completed && <p className="v5-done">✓ 已完成</p>}
          <div className={`v5-closeup ${sceneObject?.variantId ?? 'generic'}`} aria-hidden="true">
            {sceneObject?.closeup
              ? <img src={sceneObject.closeup} alt="" data-closeup-src={sceneObject.closeup} />
              : legacyArt ? <img src={legacyArt.url} alt="" data-closeup-src={legacyArt.url} /> : null}
          </div>
          <p className="v5-object-text">{object.description}</p>
          {state.clues.filter(clue => clue.object_id === object.object_id).map(clue => <article className="v5-clue" key={clue.clue_id}><h3>{clue.title}</h3><p>{clue.text}</p></article>)}
          <div className="v5-object-actions">
            {object.actions.filter(entry => !['submit_code', 'submit_login', 'submit_circuit', 'rotate_circuit', 'submit_sequence', 'inspect'].includes(entry.tool)).map((entry, index) => <button key={index} disabled={disabled} onClick={() => action(entry.tool, entry.arguments)}>{entry.label}</button>)}
            {state.inventory.map(entry => <button key={entry.item_id} disabled={disabled} onClick={() => action('use_item', { item_id: entry.item_id, target_id: object.target_id || object.object_id })}>使用 {entry.name}</button>)}
          </div>
          {object.actions.some(entry => entry.tool === 'submit_code') && <form className="v5-code" onSubmit={event => { event.preventDefault(); const entry = object.actions.find(candidate => candidate.tool === 'submit_code')!; action('submit_code', { ...entry.arguments, code }); }}>
            <label>输入你的推理<input autoComplete="off" maxLength={32} value={code} onChange={event => setCode(event.target.value)} /></label>
            <button disabled={disabled || !code.trim()}>提交密码</button>
          </form>}
          {object.actions.some(entry => entry.tool === 'submit_login') && <form className="v5-login" onSubmit={event => { event.preventDefault(); action('submit_login', { ...object.actions.find(candidate => candidate.tool === 'submit_login')!.arguments, ...credentials }); }}>
            <label>终端用户名<input value={credentials.username} onChange={event => setCredentials({ ...credentials, username: event.target.value })} /></label>
            <label>终端密码<input type="password" value={credentials.password} onChange={event => setCredentials({ ...credentials, password: event.target.value })} /></label>
            <button disabled={disabled}>提交终端登录</button>
          </form>}
          {circuit && <div className="v5-puzzle-workbench">
            <CircuitBoard board={circuit} disabled={disabled || !object.actions.some(entry => entry.tool === 'submit_circuit')} rotate={id => action('rotate_circuit', { target_id: circuit.target_id, module_id: id })} />
            <button disabled={disabled || circuit.status === 'completed' || !object.actions.some(entry => entry.tool === 'submit_circuit')} onClick={() => action('submit_circuit', { target_id: circuit.target_id })}>{circuit.status === 'completed' ? '线路已接通' : pending ? '正在检查…' : '检查线路'}</button>
          </div>}
          {seq && <section className="v5-sequence">
            <h3>四设备顺序</h3>
            <p>根据已发现线索选择次序，草稿不会保存。</p>
            <ol className="v5-sequence-draft">{sequence.map((id, index) => <li key={index}>{seq.devices.find(device => device.device_id === id)?.label || id}</li>)}</ol>
            <div className="v5-sequence-buttons">{seq.devices.map(device => <button key={device.device_id} disabled={disabled || sequence.length >= seq.length || seq.status === 'completed' || !object.actions.some(entry => entry.tool === 'submit_sequence')} onClick={() => setSequence(list => [...list, device.device_id])}>{device.symbol} {device.label}</button>)}</div>
            <div className="v5-sequence-actions">
              <button disabled={disabled} onClick={() => setSequence([])}>清除草稿</button>
              <button disabled={disabled || sequence.length !== seq.length || seq.status === 'completed' || !object.actions.some(entry => entry.tool === 'submit_sequence')} onClick={() => action('submit_sequence', { target_id: seq.target_id, device_ids: sequence })}>{seq.status === 'completed' ? '顺序已确认' : '提交顺序'}</button>
            </div>
          </section>}
        </>}
        {drawer === 'notebook' && <>
          <p className="v5-kicker">探索笔记 / FIELD NOTES</p>
          <h2>已发现的线索</h2>
          {level?.title && <p className="v5-notebook-title">{level.title}</p>}
          {!state.clues.length && <p className="v5-empty">点击物件查看，发现会记在这里。</p>}
          {state.clues.map(clue => <article className="v5-clue" key={clue.clue_id}><h3>{clue.title}</h3><p>{clue.text}</p></article>)}
        </>}
        {drawer === 'assistant' && <Assistant apiOverride={api} session={session} state={state} manualPending={pending} needsSync={uncertain} onState={next => apply(next as GeneratedState)} onUncertain={setUncertain} onForbidden={() => client.onInvalid?.()} />}
        {drawer === 'saves' && <>
          <p className="v5-kicker">进度与存档 / ARCHIVE</p>
          <h2>保存与读取</h2>
          <p className="v5-empty">进度跟随当前本地账户。重新开始复用同一关卡，保留已有存档。</p>
          <form className="v5-save-form" onSubmit={event => { event.preventDefault(); void work(async () => { const r = await api.createSaveSlot(session, state, saveName.trim() || undefined); if (apply(r.data.visible_state as GeneratedState)) { setSaveName(''); await saves(); setNotice(r.data.message); } }); }}>
            <label>存档名称<input maxLength={40} value={saveName} onChange={event => setSaveName(event.target.value)} /></label>
            <button disabled={pending || uncertain}>保存新时刻</button>
          </form>
          {slots.map(slot => <article className="v5-save" key={slot.save_id}>
            <div><h3>{slot.name}</h3><p>{new Date(slot.saved_at).toLocaleString('zh-CN')} · {slot.clues_found} 条线索</p></div>
            <div><button disabled={pending || uncertain} onClick={() => setConfirm({ kind: 'restore', slot })}>读取</button><button className="v5-quiet" disabled={pending || uncertain} onClick={() => setConfirm({ kind: 'delete', slot })}>删除</button></div>
          </article>)}
          {!slots.length && <p className="v5-empty">还没有保存的时刻。</p>}
          <button className="v5-danger" disabled={pending || uncertain} onClick={() => setConfirm({ kind: 'reset' })}>重新开始当前关卡</button>
        </>}
      </section>
    </div>}

    <dialog className="v5-confirm" ref={dialog} onCancel={() => setConfirm(null)} onClose={() => setConfirm(null)}>
      <h2>{confirm?.kind === 'delete' ? '删除这份存档？' : confirm?.kind === 'restore' ? '读取这份存档？' : '重新开始？'}</h2>
      <p>{confirm?.kind === 'delete' ? `“${confirm.slot?.name}”删除后无法恢复，当前进度不变。` : confirm?.kind === 'restore' ? `将当前进度替换为“${confirm.slot?.name}”，清除临时输入和密钥。` : '清空当前探索，复用此关卡；已有存档仍保留。'}</p>
      <div><button autoFocus onClick={() => setConfirm(null)}>取消</button><button disabled={pending} onClick={() => void confirmed()}>确认{confirm?.kind === 'delete' ? '删除' : confirm?.kind === 'restore' ? '读取' : '重新开始'}</button></div>
    </dialog>
  </main>;
}
