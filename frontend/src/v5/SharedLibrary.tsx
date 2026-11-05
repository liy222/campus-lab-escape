import { useEffect, useState } from 'react';
import { ApiError } from '../api';
import type { SharedLevel, SharedPage, V5Client } from './client';
import { packBackground, themeCoverage } from './visual/registry';

const difficulties: Record<string, string> = { easy: '简单', normal: '普通', hard: '困难' };
export default function SharedLibrary({ client, view, busy, refreshVersion, onStart, onLeaderboard }: {
  client: V5Client; view: 'hall' | 'joined'; busy: boolean; refreshVersion: number;
  onStart: (level: SharedLevel) => void; onLeaderboard: (level: SharedLevel) => void;
}) {
  const [page, setPage] = useState(1), [reload, setReload] = useState(0), [data, setData] = useState<SharedPage | null>(null), [loading, setLoading] = useState(true), [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    setLoading(true); setError('');
    void client.sharedLevels(view, page).then(response => {
      if (!alive) return;
      const last = Math.max(1, Math.ceil(response.data.total / response.data.page_size));
      if (response.data.page > last) { setPage(last); return; }
      setData(response.data);
    }).catch(problem => { if (alive) setError(problem instanceof ApiError ? problem.message : '暂时无法读取共享关卡。'); }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [client, view, page, reload, refreshVersion]);
  const title = view === 'hall' ? '共享大厅' : '我的参与';
  return <section className="v5-levels v5-shared-library" aria-labelledby={`shared-${view}-title`} aria-busy={loading}>
    <div className="v5-row"><div><p className="v5-kicker">一起探索 / SHARED CHALLENGES</p><h2 id={`shared-${view}-title`}>{title}</h2></div><button type="button" className="v5-quiet" disabled={busy || loading} onClick={() => setReload(value => value + 1)}>刷新共享关卡</button></div>
    <p className="v5-sharing-note">{view === 'hall' ? '作者发布的固定关卡。本机登录账号可加入，个人进度与存档各自独立。' : '已加入的关卡会保留在这里。作者取消共享后，你仍可继续原会话。'} 每账号记录最快成绩，提示与伙伴的使用次数会标注在榜单上。</p>
    {loading && <p className="v5-empty" role="status">正在读取共享关卡…</p>}
    {error && <p className="v5-alert" role="alert">{error} 请刷新共享关卡后重试。</p>}
    {data && !error && <>
      {data.shared_levels.length === 0 ? <p className="v5-empty">{view === 'hall' ? '大厅还没有已发布的关卡。你可以在“我的关卡”中发布。' : '你还没有加入共享关卡。前往共享大厅开始一次挑战。'}</p> : <ul>{data.shared_levels.map(level => {
        const theme = themeCoverage(level.theme);
        const cover = theme.pack ? packBackground(theme.pack, 'neutral_lab', { level_id: level.level_id, created_at: level.created_at }).background.src : '/art-handpainted/backgrounds/r1-room-shell.png';
        return <li className="v5-level-card v5-shared-card" key={level.share_id} data-share-id={level.share_id} data-level-id={level.level_id}>
          <div className="v5-level-cover" style={{ backgroundImage: `url(${cover})` }} aria-hidden="true">{theme.name && <em>{theme.name}</em>}</div>
          <div className="v5-level-copy"><h3>{level.title || level.theme || '校园探索'}</h3><p>作者 {level.author_username}{level.is_author && <span className="v5-author-tag">你是作者</span>} · {level.room_count} 间房 · {difficulties[level.difficulty] || level.difficulty}</p>
            <p className="v5-sharing-status">{level.published ? '共享中' : '已取消共享 · 原参与者可继续'}{level.session_id ? ` · ${level.challenge_status === 'practice' ? '练习进度' : level.status === 'won' ? '已完成本轮' : '已有独立进度'}` : ' · 尚未加入'}</p>
            {(level.theme || level.story) && <p className="v5-level-description">{level.theme || level.story}</p>}
          </div><div className="v5-level-actions"><button type="button" disabled={busy || loading || (!level.published && !level.session_id)} onClick={() => onStart(level)}>{level.session_id ? '继续计时挑战' : '开始计时挑战'}</button><button type="button" className="v5-quiet" disabled={busy || loading} onClick={() => onLeaderboard(level)}>查看排行榜</button></div>
        </li>;
      })}</ul>}
      <nav className="v5-sharing-pages" aria-label={`${title}分页`}><button type="button" disabled={busy || loading || page <= 1} onClick={() => setPage(value => value - 1)}>上一页</button><span>第 {data.page} 页 · 共 {data.total} 个关卡</span><button type="button" disabled={busy || loading || data.page * data.page_size >= data.total} onClick={() => setPage(value => value + 1)}>下一页</button></nav>
    </>}
  </section>;
}
