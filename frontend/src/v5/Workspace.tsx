import { useEffect, useRef, useState } from 'react';
import App from '../App';
import { ApiError } from '../api';
import { V5Client, localSession, sanitize, type Auth, type Job, type Level, type Run } from './client';
import GeneratedPlay from './GeneratedPlay';
import { packBackground, themeCoverage } from './visual/registry';
import './v5.css';

const jobLabel: Record<Job['status'], string> = { pending: '等待生成', generating: '正在生成', validating: '正在校验', ready: '已就绪', rejected: '校验拒绝', failed: '生成失败', unknown: '结果未知' };
const difficultyLabel: Record<string, string> = { easy: '简单', normal: '普通', hard: '困难' };
const campusThemes = ['雨夜天文社', '图书馆档案', '化学实验室', '计算机机房', '校园广播室'];
const jobError: Record<string, string> = {
  PROCESS_RESTARTED: '本地服务重启中断任务，请查询结果；不会自动重复付费生成。',
  MODEL_TIMEOUT: '模型超时，生成结果未知；不会自动重试。',
  MODEL_INVALID_OUTPUT: '模型输出未通过关卡校验。',
  ADMISSION_REJECTED: '关卡未通过结构与可解性校验，没有发布到你的关卡列表。',
  MODEL_OUTCOME_UNKNOWN: '模型调用结果未知，不会自动重复请求。',
  MODEL_UNAVAILABLE: '模型服务暂不可用。',
  AI_LIMIT_REACHED: '已达到生成额度或调用限制。',
};

function coverFor(level: Level) {
  const coverage = themeCoverage(level.theme);
  return coverage.pack ? packBackground(coverage.pack, 'neutral_lab', { level_id: level.level_id, created_at: level.created_at }).background.src : '/art-handpainted/backgrounds/r1-room-shell.png';
}

export default function Workspace() {
  const client = useRef(new V5Client()).current;
  const [auth, setAuth] = useState<Auth | null>(null), [loading, setLoading] = useState(true), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [form, setForm] = useState({ username: '', password: '' }), [register, setRegister] = useState(false);
  const [levels, setLevels] = useState<Level[]>([]), [runs, setRuns] = useState<Run[]>([]), [active, setActive] = useState<Run | null>(null);
  const [theme, setTheme] = useState('雨夜天文社'), [roomCount, setRoomCount] = useState(2), [difficulty, setDifficulty] = useState('normal'), [key, setKey] = useState(''), [job, setJob] = useState<Job | null>(null);
  const liveAuth = useRef(''); liveAuth.current = auth?.auth_context || '';
  const channel = useRef<BroadcastChannel | null>(null);
  const clear = () => { setKey(''); setActive(null); setLevels([]); setRuns([]); setJob(null); };
  const invalidate = () => { client.auth = { user: null, auth_context: null, csrf_token: '' }; clear(); setAuth(null); setError('登录状态已改变。请重新登录；临时密钥已清除。'); };
  client.onInvalid = invalidate;

  async function refresh() {
    const stamp = client.epoch;
    const [list, sessions, jobs] = await Promise.all([client.request<{ levels: Level[] }>('levels'), client.request<{ sessions: Run[] }>('sessions'), client.request<{ jobs: Job[] }>('level-generations')]);
    if (stamp !== client.epoch) return;
    setLevels(list.data.levels); setRuns(sessions.data.sessions);
    if (jobs.data.jobs.length) setJob(jobs.data.jobs[0]);
  }
  useEffect(() => {
    let alive = true;
    void (async () => {
      try { const a = await client.csrf(); if (!alive) return; setAuth(a); if (a.user) await refresh(); }
      catch (e) { if (alive) setError((e as Error).message); }
      finally { if (alive) setLoading(false); }
    })();
    const broadcast = new BroadcastChannel('campus-v5-identity');
    channel.current = broadcast;
    broadcast.onmessage = event => {
      if (event.data === 'identitychanged') {
        client.epoch++; invalidate();
        void client.csrf().then(a => { if (alive) setAuth(a); });
      }
    };
    return () => { alive = false; client.epoch++; broadcast.close(); };
  }, []);
  useEffect(() => {
    if (!job || !['pending', 'generating', 'validating'].includes(job.status)) return;
    let alive = true;
    const stamp = client.epoch;
    const timer = window.setTimeout(() => {
      void client.request<{ job: Job }>(`level-generations/${encodeURIComponent(job.job_id)}`).then(r => {
        if (alive && stamp === client.epoch) {
          setJob(r.data.job);
          if (r.data.job.status === 'ready') { void refresh(); window.setTimeout(() => { if (alive) void refresh().catch(() => {}); }, 1500); }
        }
      }).catch(e => { if (alive) { setJob(j => j ? { ...j, status: 'unknown' } : null); setError((e as Error).message); } });
    }, 1500);
    return () => { alive = false; window.clearTimeout(timer); };
  }, [job]);

  async function task(work: () => Promise<void>) {
    if (busy) return;
    setBusy(true); setError('');
    try { await work(); } catch (e) { setError(e instanceof ApiError ? e.message : '操作未完成，请重试。'); } finally { setBusy(false); }
  }
  async function start(mode: 'classic' | 'generated', levelId?: string) {
    setKey('');
    await task(async () => {
      const r = await client.request<Run>('sessions', { request_id: crypto.randomUUID(), mode, ...(levelId ? { level_id: levelId } : {}) });
      setActive(r.data);
    });
  }
  async function generate() {
    const owner = liveAuth.current;
    const temporaryKey = key.trim();
    if (!temporaryKey) { setError('生成关卡需要你自己的 DeepSeek API Key。'); return; }
    if (temporaryKey.length > 256 || /[^\x21-\x7E]/.test(temporaryKey)) { setError('密钥格式不正确，请去除空格、中文或换行。'); return; }
    if (!theme.trim()) { setError('请选择校园主题。'); return; }
    await task(async () => {
      if (owner !== client.auth.auth_context) throw new ApiError('STALE_AUTH', '账号已改变，请重新填写密钥。');
      const id = crypto.randomUUID();
      try {
        const r = await client.request<{ job: Job }>('level-generations', { request_id: id, theme: sanitize(theme, temporaryKey), room_count: roomCount, difficulty }, { 'X-AI-Api-Key': temporaryKey }, 55000);
        if (owner === liveAuth.current) setJob(r.data.job);
      } catch (e) {
        if (e instanceof ApiError && e.code === 'NETWORK_ERROR') setJob({ job_id: '', status: 'unknown' });
        throw e;
      } finally { setKey(''); }
    });
  }
  const logout = () => void task(async () => { await client.logout(); clear(); setAuth(await client.csrf()); channel.current?.postMessage('identitychanged'); });
  const coverage = themeCoverage(theme);
  const generating = Boolean(job && ['pending', 'generating', 'validating'].includes(job.status));

  if (loading) return <div className="v5-shell v5-loading" role="status">正在连接本地校园档案…</div>;

  if (active && auth?.user) {
    const adapter = client.classic(active.session_id);
    return <div className="v5-play-shell">
      <nav className="v5-play-nav">
        <button onClick={() => { setKey(''); setActive(null); void refresh().catch(e => setError(e.message)); }}><span aria-hidden="true">←</span> 我的关卡</button>
        <span className="v5-play-id">{auth.user.username} · {active.mode === 'classic' ? '经典校园实验室' : '生成关卡'}</span>
        <button onClick={logout}>退出登录</button>
      </nav>
      {active.mode === 'classic'
        ? <App key={`${auth.auth_context}:${active.session_id}`} connection={{ api: adapter, session: localSession(active.session_id), onForbidden: invalidate }} />
        : <GeneratedPlay key={`${auth.auth_context}:${active.session_id}`} client={client} run={active} level={levels.find(level => level.level_id === active.level_id)} />}
    </div>;
  }

  return <main className="v5-shell" aria-busy={busy}>
    <div className="v5-veil" aria-hidden="true" />
    <header className="v5-masthead">
      <div>
        <p className="v5-kicker">CAMPUS · LOCAL ARCHIVE{coverage.pack ? ` · ${coverage.pack.display_name}` : ''}</p>
        <h1>校园里的另一扇门</h1>
        <p className="v5-intro">在旧档案与手写便笺之间，寻找只属于你的校园故事。</p>
        <ul className="v5-tags"><li>手绘校园</li><li>线索解谜</li><li>本地保存</li></ul>
      </div>
      {auth?.user && <div className="v5-account"><span>{auth.user.username}</span><button disabled={busy} onClick={logout}>退出登录</button></div>}
    </header>

    {error && <p className="v5-alert v5-shell-alert" role="alert">{error}</p>}

    {!auth?.user
      ? <section className="v5-auth-panel" aria-labelledby="auth-title">
        <p className="v5-kicker">{register ? '建立身份 / REGISTER' : '回到档案室 / SIGN IN'}</p>
        <h2 id="auth-title">{register ? '建立本地账户' : '欢迎回来'}</h2>
        <p className="v5-auth-note">账户与关卡保存在这台电脑的本地服务里，不会上传。</p>
        <form onSubmit={event => {
          event.preventDefault();
          void task(async () => {
            if (!client.auth.csrf_token) await client.csrf();
            clear();
            const a = await client.authenticate(register ? 'register' : 'login', form.username, form.password);
            setForm({ username: '', password: '' }); setAuth(a); channel.current?.postMessage('identitychanged'); await refresh();
          });
        }}>
          <label>用户名（3–24位字母、数字或下划线）<input required autoComplete="username" minLength={3} maxLength={24} pattern="[A-Za-z0-9_]+" title="3–24位字母、数字或下划线" value={form.username} onChange={event => setForm({ ...form, username: event.target.value })} /></label>
          <label>密码（12–128位）<input type="password" required minLength={12} maxLength={128} autoComplete={register ? 'new-password' : 'current-password'} value={form.password} onChange={event => setForm({ ...form, password: event.target.value })} /></label>
          <button className="v5-primary" disabled={busy}>{busy ? '正在处理…' : register ? '注册并进入' : '登录'}</button>
        </form>
        <button className="v5-quiet" disabled={busy} onClick={() => { setRegister(!register); setForm({ username: '', password: '' }); setError(''); }}>{register ? '已有账户，返回登录' : '第一次来？注册本地账户'}</button>
      </section>
      : <div className="v5-dashboard">
        <section className="v5-classic">
          <p className="v5-kicker">原有三房间 · 手绘场景</p>
          <h2>经典校园实验室</h2>
          <p>保留原有实验准备室、设备实验室和出口控制室，账户内独立记录探索与存档。</p>
          <button disabled={busy} onClick={() => void start('classic')}>{runs.some(run => run.mode === 'classic') ? '继续经典关卡' : '进入经典关卡'} <span aria-hidden="true">→</span></button>
        </section>

        <section className="v5-generator" aria-labelledby="create-title">
          <p className="v5-kicker">一段故事，从这里开始 / CREATE</p>
          <h2 id="create-title">选择校园主题，开始探索</h2>
          <p className="v5-generator-lead">从已有五类手绘主题中选择，AI 围绕所选主题创作故事与谜面，程序安排可解的关卡结构；数字、设备顺序和对应关系随谜底变化，生成结果仍需通过校验。</p>
          <form onSubmit={event => { event.preventDefault(); void generate(); }}>
            <label className="v5-field">
              <span className="v5-step">01 / 选择主题</span>
              校园主题
              <select value={theme} onChange={event => setTheme(event.target.value)}>
                {campusThemes.map(name => <option key={name} value={name}>{name}</option>)}
              </select>
            </label>
            {coverage.pack && <p className="v5-coverage is-on"><span aria-hidden="true">✦</span> 已支持主题素材「{coverage.pack.display_name}」：{coverage.pack.coverage || '使用本主题的场景与代表物件，部分角色沿用通用手绘素材。'}</p>}
            <p className="v5-step">02 / 探索的规模</p>
            <div className="v5-fields">
              <label>房间数量<select value={roomCount} onChange={event => setRoomCount(Number(event.target.value))}><option value={1}>1 间</option><option value={2}>2 间</option><option value={3}>3 间</option></select></label>
              <label>难度<select value={difficulty} onChange={event => setDifficulty(event.target.value)}><option value="easy">简单</option><option value="normal">普通</option><option value="hard">困难</option></select></label>
            </div>
            <label className="v5-field">
              <span className="v5-step">03 / 开启创作</span>
              本次生成的 DeepSeek API Key
              <input type="password" maxLength={256} autoComplete="off" spellCheck={false} value={key} onChange={event => setKey(event.target.value)} />
              <small>仅当前页面临时使用，提交后清除；不会保存到账户或关卡。点击生成会使用你的 API 额度。</small>
            </label>
            <button className="v5-primary" disabled={busy || generating}>{busy ? '正在提交…' : '生成关卡'} <span aria-hidden="true">→</span></button>
          </form>
          {job && <div className="v5-job" role="status">
            <strong>{jobLabel[job.status] || '结果未知'}</strong>
            {job.job_id && <small>任务 {job.job_id}</small>}
            {job.error_code && <p>{jobError[job.error_code] || `生成未完成（${job.error_code}）。`}</p>}
            {job.error && <p>{sanitize(typeof job.error === 'string' ? job.error : job.error.message || job.error.code || '生成未通过')}</p>}
            {job.message && <p>{sanitize(job.message)}</p>}
            {job.status === 'unknown' && <button onClick={() => void task(async () => {
              if (!job.job_id) { await refresh(); return; }
              const r = await client.request<{ job: Job }>(`level-generations/${encodeURIComponent(job.job_id)}`);
              setJob(r.data.job);
              if (r.data.job.status === 'ready') await refresh();
            })}>查询任务结果</button>}
          </div>}
        </section>

        <section className="v5-levels" aria-labelledby="levels-title">
          <div className="v5-row"><div><p className="v5-kicker">我的探索档案 / COLLECTION</p><h2 id="levels-title">我的关卡</h2></div><button className="v5-quiet" disabled={busy} onClick={() => void task(refresh)}>刷新列表</button></div>
          {levels.length === 0 ? <p className="v5-empty">尚无生成关卡。生成通过校验后，会保存在这里。</p> : <ul>
            {levels.map((level, index) => {
              const run = runs.find(candidate => candidate.level_id === level.level_id);
              const themed = themeCoverage(level.theme);
              return <li className="v5-level-card" key={level.level_id}>
                <div className="v5-level-cover" style={{ backgroundImage: `url(${coverFor(level)})` }} aria-hidden="true"><span>{String(index + 1).padStart(2, '0')}</span>{themed.pack && <em>{themed.name}</em>}</div>
                <div className="v5-level-copy">
                  <h3>{level.title || level.theme || '校园探索'}</h3>
                  <p>{level.room_count} 间房 · {difficultyLabel[level.difficulty] || level.difficulty}{run ? ` · ${run.status === 'won' ? '已通关' : '已有进度'}` : ''}</p>
                  {(level.theme || level.story) && <p className="v5-level-description">{level.theme || level.story}</p>}
                </div>
                <button disabled={busy} onClick={() => void start('generated', level.level_id)}>{run ? '继续探索' : '开始探索'} <span aria-hidden="true">→</span></button>
              </li>;
            })}
          </ul>}
        </section>
      </div>}
  </main>;
}
