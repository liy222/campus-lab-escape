import { useEffect, useRef, useState } from 'react';
import { api, ApiError, type ActionArguments, type AiSettings, type AiTurnData, type Proposal, type Receipt, type Session, type VisibleState } from './api';

const reasons: Record<string, string> = { MODEL_TIMEOUT: '模型未能在时间内完成，已停止本次问答。', MODEL_UNAVAILABLE: '模型服务暂不可用，可以继续手动探索。', MODEL_INVALID_OUTPUT: '返回的建议无法通过检查，未执行任何建议行动。', AI_LIMIT_REACHED: '本次问答达到调用上限，已停止。', STALE_STATE: '问答期间进度已改变，请依据当前场景重新询问。' };
const proposalLabels = { pending: '待确认 · proposed', committed: '已执行 · committed', cancelled: '已取消 · cancelled', expired: '已过期', invalidated: '已失效', rejected: '已拒绝 · rejected', unknown: '结果待核对' };
type ProposalView = { proposal: Proposal; receipt: Receipt | null; outcome: keyof typeof proposalLabels; message?: string; replayed?: boolean };
type Trace = { id: string; eventId: string | null; outcome: string; tool: string; arguments: ActionArguments; revision: number; generation: string; message: string; receipt?: Receipt };
type CompanionExchange = { id: string; generation: string; revision: number; question: string; answer: string; outdated: boolean };
interface Props { session: Session; state: VisibleState; manualPending: boolean; needsSync: boolean; onState: (state: VisibleState, reconciled?: boolean) => boolean; onUncertain: (value: boolean) => void; onForbidden: (sessionId: string) => void; onReference?: (clueId: string) => void }

export default function Assistant({ session, state, manualPending, needsSync, onState, onUncertain, onForbidden, onReference }: Props) {
  const [question, setQuestion] = useState('');
  const [provider, setProvider] = useState<AiSettings['provider']>('mock');
  const [apiKey, setApiKey] = useState('');
  const [turn, setTurn] = useState<AiTurnData | null>(null);
  const [view, setView] = useState<ProposalView | null>(null);
  const [pending, setPending] = useState<'ask' | 'confirm' | 'cancel' | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [traces, setTraces] = useState<Trace[]>([]);
  const [companionHistory, setCompanionHistory] = useState<CompanionExchange[]>([]);
  const [now, setNow] = useState(Date.now);
  const [hintLevel, setHintLevel] = useState<1 | 2 | 3>(state.statistics?.current_hint_level || 1);
  const hintMode = state.level_version === '3.4.0';
  const presetHintMode = hintMode && provider === 'mock';
  const companionMode = hintMode && provider === 'deepseek';
  const busy = useRef(false);
  const current = useRef(state);
  const pendingGeneration = useRef<string | null>(null);
  const assistantRevision = useRef<number | null>(null);
  const observedProgress = useRef({ generation: state.generation, revision: state.revision });
  const requestContextKey = JSON.stringify([session.session_id, session.token, state.generation, provider]);
  const requestContext = useRef({ key: requestContextKey, version: 0 });
  if (requestContext.current.key !== requestContextKey) requestContext.current = { key: requestContextKey, version: requestContext.current.version + 1 };
  current.current = state;
  useEffect(() => { setApiKey(''); setProvider('mock'); setQuestion(''); setTurn(null); setView(null); setTraces([]); setCompanionHistory([]); assistantRevision.current = null; setError(''); setNotice(''); }, [session.session_id, session.token]);
  useEffect(() => {
    setApiKey(''); setProvider('mock');
    setQuestion(''); setTurn(null); setView(null); setTraces([]); setCompanionHistory([]); assistantRevision.current = null; setError(''); setNotice('');
  }, [state.generation]);
  useEffect(() => { setQuestion(''); }, [state.revision]);
  useEffect(() => {
    setCompanionHistory([]); assistantRevision.current = null;
  }, [provider, session.session_id, session.token, state.generation]);
  useEffect(() => {
    const previous = observedProgress.current;
    if (previous.generation !== state.generation) {
      observedProgress.current = { generation: state.generation, revision: state.revision };
      assistantRevision.current = null;
      return;
    }
    if (previous.revision === state.revision) return;
    observedProgress.current = { generation: state.generation, revision: state.revision };
    if (assistantRevision.current === state.revision) assistantRevision.current = null;
    else setCompanionHistory(entries => entries.map(entry => ({ ...entry, outdated: true })));
  }, [state.generation, state.revision]);
  useEffect(() => { setHintLevel(state.statistics?.current_hint_level || 1); }, [state.generation, state.statistics?.current_hint_level]);
  useEffect(() => { const timer = window.setInterval(() => setNow(Date.now()), 1000); return () => window.clearInterval(timer); }, []);
  const currentView = view?.proposal.generation === state.generation ? view : null;
  const outdated = !!currentView && currentView.outcome === 'pending' && currentView.proposal.revision !== state.revision;
  const expired = !!currentView && currentView.outcome === 'pending' && Date.parse(currentView.proposal.expires_at) <= now;
  const outcome = outdated ? 'invalidated' : expired ? 'expired' : currentView?.outcome;
  const canConfirm = !!currentView && outcome === 'pending' && state.status === 'playing' && !pending && !manualPending && !needsSync;
  const currentTurn = turn?.visible_state.generation === state.generation ? turn : null;
  const answerOutdated = currentTurn && currentTurn.visible_state.revision !== state.revision;
  const companionChatTurn = companionMode && !!currentTurn && currentTurn.usage.model_calls > 0 && currentTurn.status !== 'stopped' && !!currentTurn.answer.trim();
  const missingApiKey = provider === 'deepseek' && !apiKey.trim();
  const invalidApiKey = provider === 'deepseek' && /[^\x21-\x7E]/.test(apiKey.trim());

  function chooseProvider(next: AiSettings['provider']) {
    if (busy.current) return;
    if (next === 'mock') setApiKey('');
    setProvider(next); setQuestion(''); setTurn(null); setCompanionHistory([]); assistantRevision.current = null; setError('');
  }

  function trace(proposal: Proposal, outcome: string, message: string, receipt?: Receipt, eventId?: string | null) {
    setTraces(entries => [{ id: eventId || `${proposal.proposal_id}-${outcome}`, eventId: eventId || null, outcome, tool: receipt?.tool || proposal.tool, arguments: receipt?.arguments || proposal.arguments, revision: receipt?.revision_after ?? proposal.revision, generation: receipt?.generation || proposal.generation, message, ...(receipt ? { receipt } : {}) }, ...entries].slice(0, 8));
  }
  function knownReferences(ids: string[], projection: VisibleState) { return ids.every(id => projection.clues.some(clue => clue.clue_id === id)); }
  async function failure(caught: unknown, proposal?: Proposal, startedGeneration?: string) {
    const problem = caught instanceof ApiError ? caught : new ApiError('CLIENT_ERROR', '问答操作未完成，请稍后重新询问。');
    if (problem.visibleState) onState(problem.visibleState);
    if (problem.code === 'FORBIDDEN_SESSION') onForbidden(session.session_id);
    else if (startedGeneration && current.current.generation !== startedGeneration) { setNotice('进度已更换，旧问答的结果已忽略。'); return; }
    else if (['NETWORK_ERROR', 'SERVICE_UNAVAILABLE'].includes(problem.code)) {
      if (proposal) { setView({ proposal, receipt: null, outcome: 'unknown' }); trace(proposal, 'unknown', '响应丢失，未取得执行收据。'); }
      onUncertain(true);
      try { const response = await api.state(session); if (onState(response.data.visible_state, true)) setNotice('已同步实际进度。未自动重发问答或确认，请依据场景继续。'); }
      catch { setNotice('尚未确认操作结果，请先点击“同步进度”。'); }
    } else if (proposal) {
      const status = problem.code === 'PROPOSAL_EXPIRED' ? 'expired' : problem.code === 'PROPOSAL_INVALIDATED' || problem.code === 'STALE_STATE' || problem.code === 'STALE_GENERATION' ? 'invalidated' : problem.code === 'PROPOSAL_CANCELLED' ? 'cancelled' : 'rejected';
      setView({ proposal, receipt: null, outcome: status, message: problem.message });
      trace(proposal, status, problem.message, undefined, problem.eventId);
    }
    setError(problem.message);
  }
  async function ask() {
    if (busy.current || manualPending || needsSync || state.status === 'won') return;
    if (missingApiKey) { setError('请先填写 DeepSeek API Key，再询问伙伴。'); return; }
    if (invalidApiKey) { setError('API Key 格式不正确，请重新输入，避免空格、中文或换行。'); return; }
    if (!presetHintMode && (!question.trim() || question.length > 2000)) { setError('请填写 1–2000 字的问句。'); return; }
    const started = current.current;
    const startedContext = requestContext.current.version;
    busy.current = true; pendingGeneration.current = started.generation; setPending('ask'); setError(''); setNotice(''); setView(null);
    try {
      const settings: AiSettings = provider === 'deepseek' ? { provider, apiKey } : { provider };
      const message = presetHintMode ? '获取当前进度的预设提示' : question;
      const response = await api.ai(session, started, message, settings, presetHintMode ? hintLevel : undefined);
      if (requestContext.current.version !== startedContext) return;
      const data = response.data;
      if (!onState(data.visible_state)) { setNotice('问答来自较早的进度，已忽略。请重新询问。'); return; }
      if (current.current.generation !== started.generation || data.visible_state.generation !== started.generation) { setNotice('游戏进度已更换，旧问答已清除。请重新询问。'); return; }
      if (!knownReferences(data.clue_refs, data.visible_state) || (data.proposal && !knownReferences(data.proposal.clue_refs, data.visible_state))) throw new ApiError('MODEL_INVALID_OUTPUT', '建议含无法核对的线索引用，未显示该建议。已发现线索仍保留。');
      setTurn(data);
      if (companionMode) {
        assistantRevision.current = data.visible_state.revision;
        if (data.usage.model_calls > 0 && data.status !== 'stopped' && data.answer.trim()) setCompanionHistory(entries => [...entries, { id: data.turn_id, generation: data.visible_state.generation, revision: data.visible_state.revision, question: redactCompanionText(message), answer: data.answer, outdated: false }].slice(-4));
      }
      if (data.proposal) {
        setView({ proposal: data.proposal, receipt: null, outcome: data.proposal.status });
        trace(data.proposal, 'proposed', '服务器保存了建议；尚未执行。', undefined, response.event_id);
      }
    } catch (caught) { if (requestContext.current.version === startedContext) await failure(caught, undefined, started.generation); }
    finally { busy.current = false; pendingGeneration.current = null; setPending(null); }
  }
  async function decide(operation: 'confirm' | 'cancel') {
    if (busy.current || !currentView || !canConfirm) return;
    const proposal = currentView.proposal;
    if (proposal.generation !== current.current.generation || proposal.revision !== current.current.revision || Date.parse(proposal.expires_at) <= Date.now()) return;
    busy.current = true; setPending(operation); setError(''); setNotice('');
    try {
      if (operation === 'confirm') {
        const response = await api.confirm(session, proposal.proposal_id);
        if (!onState(response.data.visible_state)) { setNotice('确认响应来自较早进度，请同步当前状态。'); return; }
        if (response.data.visible_state.generation !== proposal.generation) return;
        if (!response.data.proposal) throw new ApiError('SERVICE_UNAVAILABLE', '确认响应缺少行动记录，请同步进度。');
        setView({ proposal: response.data.proposal, receipt: response.data.receipt, outcome: response.data.proposal.status, replayed: response.data.replayed });
        trace(response.data.proposal, 'committed', response.data.receipt.message, response.data.receipt, response.data.receipt.event_id);
      } else {
        const response = await api.cancel(session, proposal.proposal_id);
        if (!onState(response.data.visible_state) || response.data.visible_state.generation !== proposal.generation) return;
        setView({ proposal: response.data.proposal, receipt: null, outcome: response.data.proposal.status, message: '建议已取消，没有执行该行动。' });
        trace(response.data.proposal, 'cancelled', '服务器确认取消；没有执行该行动。', undefined, response.event_id);
      }
    } catch (caught) { await failure(caught, proposal, proposal.generation); }
    finally { busy.current = false; setPending(null); }
  }
  function references(ids: string[]) {
    return <ul className="ai-references">{ids.map(id => { const clue = state.clues.find(clue => clue.clue_id === id); return clue ? <li key={id}><a href={`#clue-${id}`} onClick={event => { if (onReference) { event.preventDefault(); onReference(id); } }}>{clue.title} ↗</a></li> : null; })}</ul>;
  }
  function redactCompanionText(value: string) {
    const secrets = [...new Set([apiKey, apiKey.trim(), session.token].filter(secret => secret.length > 0))];
    return secrets.reduce((safe, secret) => safe.split(secret).join('[已隐藏]'), value);
  }
  return <section className={`assistant ai-panel panel ${hintMode ? 'hint-mode' : ''}`} aria-labelledby="assistant-title">
    <div className="panel-heading"><h2 id="assistant-title">AI 探索伙伴</h2>{currentTurn && <span className="provider-badge">{companionMode && currentTurn.usage.model_calls === 0 ? '本地提醒（未调用模型）' : currentTurn.usage.provider === 'mock' ? '本次回答：免费模拟' : currentTurn.usage.provider === 'deepseek' ? '本次回答：真实 DeepSeek' : `本次回答服务：${currentTurn.usage.provider}`}</span>}</div>
    {presetHintMode ? <><p className="panel-caption">只根据你已发现的信息提供提示，不会替你执行行动。已接受提示：<strong className="hint-count">{state.statistics?.hint_count ?? 0}</strong> 次</p><label className="hint-level-label" htmlFor="hint-level">提示强度</label><select id="hint-level" className="hint-level" value={hintLevel} disabled={!!pending} onChange={event => setHintLevel(Number(event.target.value) as 1 | 2 | 3)}><option value={1}>L1 · 方向提示</option><option value={2}>L2 · 关注范围</option><option value={3}>L3 · 部分关系</option></select><p className="hint-level-help">L1 给出探索方向；L2 缩小关注范围；L3 提示部分线索关系。选择强度不会发送请求。</p></> : companionMode ? <p className="panel-caption">可围绕已发现线索和当前公开进度作简短交流。伙伴不会执行行动，也不会直接给出完整答案。</p> : <p className="panel-caption">依据已发现的线索讨论下一步。建议行动经你确认后才会执行。</p>}
    <fieldset className="ai-settings" disabled={!!pending}>
      <legend>选择伙伴模式</legend>
      <div className="ai-mode-options">
        <label className={provider === 'mock' ? 'ai-mode selected' : 'ai-mode'}><input type="radio" name="ai-provider" value="mock" checked={provider === 'mock'} onChange={() => chooseProvider('mock')}/><span><strong>{hintMode ? '预设提示（免费）' : '免费模拟'}</strong><small>使用预设建议，无 API 费用</small></span></label>
        <label className={provider === 'deepseek' ? 'ai-mode selected' : 'ai-mode'}><input type="radio" name="ai-provider" value="deepseek" checked={provider === 'deepseek'} onChange={() => chooseProvider('deepseek')}/><span><strong>{hintMode ? 'AI 伙伴（真实模型）' : '真实 DeepSeek'}</strong><small>使用你自己的 API 账户</small></span></label>
      </div>
      {provider === 'deepseek' && <div className="ai-key-settings">
        <label htmlFor="ai-api-key">DeepSeek API Key</label>
        <div className="ai-key-row"><input id="ai-api-key" type="password" autoComplete="off" autoCapitalize="none" spellCheck={false} value={apiKey} placeholder="在这里输入你的 API Key" aria-describedby={`ai-key-note${missingApiKey || invalidApiKey ? ' ai-key-required' : ''}`} onChange={event => setApiKey(event.target.value)}/><button type="button" className="button subtle" disabled={!apiKey || !!pending} onClick={() => setApiKey('')}>清除密钥</button></div>
        <p id="ai-key-note">密钥仅在当前页面内存中保留；刷新、切换游戏或回到免费模拟时会清除，不随进度保存。</p>
        {(missingApiKey || invalidApiKey) && <p id="ai-key-required" className="ai-key-required">{missingApiKey ? '请先填写 API Key，才能询问真实伙伴。' : 'API Key 格式不正确，请重新输入，避免空格、中文或换行。'}</p>}
        <p className="ai-real-note">{companionMode ? '每次交流会发送当前问题、最近3轮对话、已发现线索和当前公开进度；不会读取未发现内容或代你操作。回答是简短引导，不会直接给出完整答案。请求会使用你的 API 账户用量。使用模型：deepseek-flash。' : hintMode ? '点击“获取提示”会根据已发现的信息请求一个受限提示。发送给 DeepSeek 的仅是符合条件的提示主题名称和已发现线索 ID，不包含你的问题、对话历史或线索全文；请求会使用你的 API 账户用量。AI 伙伴当前仍提供受限提示，不会按问题自由聊天。使用模型：deepseek-flash。' : '点击“询问伙伴”会把你的问题与已发现的线索发送给 DeepSeek，并扣除你的 API 账户用量。使用模型：deepseek-flash。'}</p>
      </div>}
      <p className="ai-settings-note">{presetHintMode ? '选择提示强度、选择模式、填写或清除密钥都不会发起请求；只有点击“获取提示”才会调用所选服务。' : '选择模式、填写或清除密钥不会发起问答；只有点击“询问伙伴”才会调用所选伙伴。'}</p>
    </fieldset>
    <form className="ai-question" onSubmit={event => { event.preventDefault(); void ask(); }}>
      {!presetHintMode && <><label htmlFor="ai-question">{companionMode ? '想问探索伙伴什么？' : hintMode ? '想获得什么提示？' : '想问探索伙伴什么？'}</label>
      <textarea id="ai-question" maxLength={2000} rows={3} value={question} disabled={!!pending || needsSync || state.status === 'won'} placeholder={companionMode ? '例如：我已经发现的线索之间有什么联系？' : hintMode ? '例如：下一步可以关注哪里？' : '例如：我应该先查看哪些物件？'} onChange={event => setQuestion(event.target.value)}/></>}
      <div className="ai-question-actions">{!presetHintMode && <small>{question.length}/2000</small>}<button className={`button primary ${presetHintMode ? 'hint-ask' : ''}`} disabled={!!pending || manualPending || needsSync || state.status === 'won' || (!presetHintMode && !question.trim()) || missingApiKey || invalidApiKey}>{presetHintMode ? '获取提示' : '询问伙伴'}</button></div>
    </form>
    {state.status === 'won' && <p className="muted">已完成探索。可以保存、恢复或开始新游戏。</p>}
    <div className="ai-feedback" aria-live="polite">{pending && <p className="pending"><span className="spinner"/>{pending === 'ask' ? pendingGeneration.current !== state.generation ? '进度已更换，正在结束旧问答…' : '正在查看线索并思考，最长约 45 秒。你仍可手动探索…' : pending === 'confirm' ? '正在确认行动，请稍候…' : '正在取消建议，请稍候…'}</p>}{error && <p className="error" role="alert">{error}</p>}{notice && <p className="notice">{notice}</p>}</div>
    {companionMode && companionHistory.length > 0 && <section className="companion-history" aria-label="最近的伙伴交流">{companionHistory.map(entry => <article key={entry.id} className={entry.outdated ? 'companion-exchange outdated' : 'companion-exchange'}><p className="companion-question">{entry.question}</p><p className="companion-answer">{entry.answer}</p>{entry.outdated && <small>回答时的进度已改变 · 这是此前讨论，请以当前场景为准。</small>}</article>)}</section>}
    {currentTurn && <div className="ai-answer">{!companionChatTurn && <div className="ai-status">{companionMode ? currentTurn.usage.model_calls === 0 ? '本地提醒（未调用模型）' : currentTurn.status === 'stopped' ? '本次伙伴交流未完成' : '伙伴暂时无法继续交流' : hintMode ? currentTurn.status === 'stopped' ? '本次提示未完成' : currentTurn.usage.provider === 'unavailable' || !currentTurn.answer.trim() ? '暂无可用提示' : '提示已提供' : currentTurn.status === 'completed' ? '问答已完成' : currentTurn.status === 'no_suggestion' ? '暂无行动建议' : '本次问答已停止'}{answerOutdated && <span> · 回答时的进度已改变</span>}</div>}{!companionChatTurn && <p>{currentTurn.answer || '本次没有可显示的回答。'}</p>}{currentTurn.stop_reason && <p className="stop-reason">{reasons[currentTurn.stop_reason] || currentTurn.stop_reason}</p>}{currentTurn.clue_refs.length > 0 && <><h3>引用的已发现线索</h3>{references(currentTurn.clue_refs)}</>}<details className="usage"><summary>本次服务与用量</summary><p>{currentTurn.usage.provider === 'mock' ? '开发模拟输出，不是真实模型验收证据。' : `服务 ${currentTurn.usage.provider} · 模型 ${currentTurn.usage.model ?? '未提供'}`}</p><p>输入 token：{currentTurn.usage.input_tokens ?? '未提供'} · 输出 token：{currentTurn.usage.output_tokens ?? '未提供'}</p><p>服务调用尝试 {currentTurn.usage.model_calls} 次 · 查看工具 {currentTurn.usage.read_tool_calls} 次</p></details></div>}
    {!hintMode && currentView && <section className="proposal-card" aria-labelledby="proposal-title"><div className="panel-heading"><h3 id="proposal-title">{outcome === 'committed' ? '已确认的行动' : '建议行动'}</h3><span className={`proposal-status status-${outcome}`}>{outcome && proposalLabels[outcome]}</span></div>{!outdated && !expired && <><p>{outcome !== 'pending' && '原建议：'}{currentView.proposal.summary}</p><dl className="proposal-parameters"><div><dt>工具</dt><dd>{currentView.proposal.tool}</dd></div>{Object.entries(currentView.proposal.arguments).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl><p className="proposal-expiry">期限：<time dateTime={currentView.proposal.expires_at}>{new Date(currentView.proposal.expires_at).toLocaleString('zh-CN', { hour12: false })}</time> · 绑定进度 {currentView.proposal.revision}</p>{currentView.proposal.clue_refs.length > 0 && references(currentView.proposal.clue_refs)}</>}{outdated && <p>当前进度已变化，这条旧建议已在界面失效。请重新询问。</p>}{expired && <p>确认期限已过。请重新询问获取新建议。</p>}{currentView.message && <p>{currentView.message}</p>}{currentView.receipt && <div className="committed-receipt"><strong>服务器执行记录</strong><p>{currentView.receipt.message}</p><small>{currentView.receipt.changed ? '实际状态已变化' : '没有再次改变状态'} · 进度 {currentView.receipt.revision_before} → {currentView.receipt.revision_after}{currentView.replayed ? ' · 返回原执行记录' : ''}</small>{currentView.receipt.observation && <p>{currentView.receipt.observation}</p>}</div>}<div className="proposal-actions"><button className="button primary" disabled={!canConfirm} onClick={() => void decide('confirm')}>确认执行</button><button className="button" disabled={!canConfirm} onClick={() => void decide('cancel')}>取消建议</button></div>{outcome === 'pending' && <small className="proposal-disclaimer">参数由服务器固定；确认前没有执行该行动。</small>}</section>}
    {traces.length > 0 && <details className="ai-trace"><summary>建议与执行记录</summary><ol>{traces.map((entry, index) => <li key={`${entry.id}-${index}`}><strong>{entry.outcome}</strong><p>{entry.message}</p><small>进度 {entry.revision} · {entry.tool}</small><pre>{JSON.stringify({ event_id: entry.eventId, generation: entry.generation, revision: entry.revision, tool: entry.tool, arguments: entry.arguments, ...(entry.receipt ? { receipt: entry.receipt } : {}) }, null, 2)}</pre></li>)}</ol></details>}
  </section>;
}
