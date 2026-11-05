import { useEffect, useId, useRef, useState } from 'react';
import { ApiError } from '../api';
import type { Leaderboard, LeaderboardEntry, V5Client } from './client';

export function formatDuration(value: number, precise = true) {
  const milliseconds = Math.max(0, Math.floor(value));
  const minutes = Math.floor(milliseconds / 60000), seconds = Math.floor(milliseconds / 1000) % 60;
  const clock = `${minutes}:${String(seconds).padStart(2, '0')}`;
  return precise ? `${clock}.${String(milliseconds % 1000).padStart(3, '0')}` : clock;
}
function Assistance({ entry }: { entry: Pick<LeaderboardEntry, 'hint_count' | 'companion_count'> }) {
  return <span>免费提示 {entry.hint_count} · 伙伴 {entry.companion_count}</span>;
}

/** A failed leaderboard read is independent of the accepted game completion. */
export function LeaderboardPanel({ client, shareId, summaryOnly = false }: { client: V5Client; shareId: string; summaryOnly?: boolean }) {
  const [data, setData] = useState<Leaderboard | null>(null), [loading, setLoading] = useState(true), [error, setError] = useState(''), [reload, setReload] = useState(0);
  useEffect(() => {
    let alive = true;
    setLoading(true); setError(''); setData(null);
    void client.leaderboard(shareId).then(response => { if (alive) setData(response.data); }).catch(problem => {
      if (alive) setError(problem instanceof ApiError ? problem.message : '排行榜暂时无法读取。');
    }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [client, shareId, reload]);
  return <section className={`v5-leaderboard ${summaryOnly ? 'is-summary' : ''}`} aria-label={summaryOnly ? '个人最佳成绩' : '通关排行榜'} data-share-id={shareId} aria-busy={loading}>
    <div className="v5-board-heading"><h3>{summaryOnly ? '你的个人最佳' : '通关排行榜'}</h3><button type="button" disabled={loading} onClick={() => setReload(value => value + 1)}>刷新榜单</button></div>
    {loading && <p role="status">正在读取成绩…</p>}
    {error && <p className="v5-board-error" role="alert">榜单暂未读取：{error} 游戏通关结果不受本次读取影响，可刷新重试。</p>}
    {data && <>
      <div className="v5-own-best" data-own-rank={data.own_entry?.rank ?? ''}>
        {data.own_entry ? <><strong>第 {data.own_entry.rank} 名 · {formatDuration(data.own_entry.elapsed_ms)}</strong><p>{data.own_entry.username}{data.own_entry.is_author && <span className="v5-author-tag">作者</span>} · <Assistance entry={data.own_entry} /></p></> : <p>你还没有有效通关成绩。完成计时挑战后，将记录你的最快成绩。</p>}
      </div>
      {!summaryOnly && <><p className="v5-board-note">每账号保留最快成绩，共 {data.total_players} 位玩家有成绩；此处展示前50名。相同用时按完成时间和轮次稳定排序。</p>
        {data.entries.length ? <div className="v5-board-table-wrap"><table><caption>本关卡的个人最快通关记录</caption><thead><tr><th scope="col">名次</th><th scope="col">玩家</th><th scope="col">正式用时</th><th scope="col">使用辅助</th><th scope="col">完成时间</th></tr></thead><tbody>{data.entries.map(entry => <tr key={entry.attempt_id} data-rank={entry.rank} data-is-own={entry.attempt_id === data.own_entry?.attempt_id}>
          <td>{entry.rank}</td><th scope="row">{entry.username}{entry.is_author && <span className="v5-author-tag">作者</span>}{entry.attempt_id === data.own_entry?.attempt_id && <span className="v5-me-tag">你</span>}</th><td><time>{formatDuration(entry.elapsed_ms)}</time></td><td><Assistance entry={entry} /></td><td><time dateTime={entry.finished_at}>{new Date(entry.finished_at).toLocaleString('zh-CN')}</time></td>
        </tr>)}</tbody></table></div> : <p>还没有有效通关记录，欢迎成为第一位完成挑战的玩家。</p>}
      </>}
    </>}
  </section>;
}

export function LeaderboardDialog({ client, shareId, title, onClose }: { client: V5Client; shareId: string; title: string; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null), heading = useId();
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    dialog.current?.showModal();
    return () => { dialog.current?.close(); if (previous?.isConnected) previous.focus(); };
  }, []);
  return <dialog className="v5-leaderboard-dialog" ref={dialog} aria-labelledby={heading} onCancel={event => { event.preventDefault(); onClose(); }}>
    <button type="button" className="v5-close" autoFocus onClick={onClose}>关闭排行榜</button><p className="v5-kicker">校园挑战 / LEADERBOARD</p><h2 id={heading}>{title}</h2>
    <LeaderboardPanel client={client} shareId={shareId} />
  </dialog>;
}
