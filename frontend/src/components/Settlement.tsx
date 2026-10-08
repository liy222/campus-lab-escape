import { room3Assets } from '../assets/manifest';
import type { VisibleState } from '../api';
export default function Settlement({ state, onReset, onRecords }: { state: VisibleState; onReset: () => void; onRecords: () => void }) {
  const result = state.settlement;
  if (!result) return <section className="victory-screen" role="status">正在同步本局结算…</section>;
  const seconds = Math.max(0, Math.floor(result.elapsed_seconds));
  return <section className="victory-screen" aria-labelledby="settlement-title" style={{ backgroundImage: `url(${room3Assets.r3_victory_background})` }}>
    <div className="victory-card"><p className="eyebrow">CAMPUS LAB · OUTSIDE</p><h1 id="settlement-title">逃离成功</h1><p className="victory-message">门外的灯，终于亮了。</p>
      <dl className="victory-statistics"><div><dt>用时</dt><dd data-stat="elapsed_seconds">{String(Math.floor(seconds / 3600)).padStart(2, '0')}:{String(Math.floor(seconds / 60) % 60).padStart(2, '0')}:{String(seconds % 60).padStart(2, '0')}</dd></div><div><dt>发现线索</dt><dd data-stat="clues_found">{result.clues_found}/{result.clues_total}</dd></div><div><dt>隐藏发现</dt><dd data-stat="hidden_found">{result.hidden_found}/{result.hidden_total}</dd></div><div><dt>AI 提示</dt><dd data-stat="hint_count">{result.hint_count}</dd></div><div><dt>错误尝试</dt><dd data-stat="mistake_count">{result.mistake_count}</dd></div></dl>
      <div className="victory-rating"><span>评级</span><strong data-stat="rating">{result.rating}</strong></div><div className="victory-actions"><button className="button victory-reset" onClick={onReset}>重新开始</button><button className="button victory-records" onClick={onRecords}>返回记录</button></div>
    </div>
  </section>;
}
