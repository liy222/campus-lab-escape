import { useEffect, useState } from 'react';
import type { Challenge } from './client';
import { formatDuration } from './Leaderboard';

export default function ChallengeBanner({ challenge, shareId, author, disabled, onLeaderboard, onRestart }: {
  challenge?: Challenge; shareId: string; author?: string; disabled: boolean; onLeaderboard: () => void; onRestart: () => void;
}) {
  const [now, setNow] = useState(Date.now);
  useEffect(() => {
    if (challenge?.status !== 'active') return;
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [challenge?.attempt_id, challenge?.status]);
  const started = challenge ? Date.parse(challenge.started_at) : NaN;
  const elapsed = challenge?.status === 'active' && Number.isFinite(started) ? Math.max(0, now - started) : challenge?.elapsed_ms;
  return <section className="v5-challenge" aria-label="计时挑战状态" data-share-id={shareId} data-challenge-status={challenge?.status || 'loading'}>
    <div><p className="v5-kicker">共享关卡{author ? ` · 作者 ${author}` : ''}{challenge?.is_author ? ' · 你是作者' : ''}</p><strong>{challenge?.status === 'active' ? '计时挑战进行中' : challenge?.status === 'practice' ? '练习模式 · 不计入排行榜' : challenge?.status === 'finished' ? '本轮挑战已结束' : '正在同步挑战状态'}</strong>{elapsed !== null && elapsed !== undefined && <time className="v5-challenge-clock" aria-label={challenge?.status === 'active' ? '当前挑战估算用时' : '服务端记录用时'}>{formatDuration(elapsed, challenge?.status !== 'active')}</time>}
      <p>{challenge ? `免费提示 ${challenge.hint_count} 次 · 伙伴 ${challenge.companion_count} 次` : '请以同步后的服务端挑战状态为准。'}</p>
      <p className="v5-challenge-rule">{challenge?.status === 'practice' ? '跨轮或已完成存档进入练习，保留已有成绩。重新开始可开启完整挑战。' : '计时包含离线、退出与重启，本轮读档不会回退计时。正式用时由服务端在行动通关时记录。'}</p>
    </div><div className="v5-challenge-actions"><button type="button" onClick={onLeaderboard}>排行榜</button><button type="button" className="v5-quiet" disabled={disabled} onClick={onRestart}>重开挑战</button></div>
  </section>;
}
