import type { CircuitPuzzle } from '../api';

const directions = ['N', 'E', 'S', 'W'] as const;
const points: Record<string, [number, number]> = { N: [50, 5], E: [95, 50], S: [50, 95], W: [5, 50] };
const sideNames = { N: '上', E: '右', S: '下', W: '左' };

export default function CircuitBoard({ board, disabled, rotate }: { board: CircuitPuzzle; disabled: boolean; rotate: (id: string) => void }) {
  const completed = board.status === 'completed';
  return <section className={`v5-circuit-panel ${completed ? 'is-completed' : ''}`} aria-label="线路连接面板">
    <div className="v5-puzzle-heading"><span className="v5-instrument-tag">配电线路 / 3 × 3</span><span className="v5-board-status" role="status">{completed ? '● 线路已接通' : '○ 等待检查'}</span></div>
    <p className="v5-circuit-help">把铜色接点连成一条线路，从电源通向出口。点击模块可顺时针旋转，调整好后检查线路。</p>
    <div className="v5-circuit" aria-label="三乘三线路模块">
      {board.modules.map(module => {
        const ports = (module.shape === 'I' ? ['N', 'S'] : ['N', 'E']).map(direction => directions[(directions.indexOf(direction as typeof directions[number]) + module.rotation) % 4]);
        const source = board.source.module_id === module.module_id;
        const sink = board.sink.module_id === module.module_id;
        const position = `第${module.row + 1}行第${module.column + 1}列`;
        return <button className={`v5-circuit-module ${source ? 'is-source' : ''} ${sink ? 'is-sink' : ''}`} disabled={disabled || completed} key={module.module_id} onClick={() => rotate(module.module_id)} aria-label={`${position}，${module.shape === 'I' ? '直线' : '转角'}接头，${ports.map(port => sideNames[port]).join('与')}相连${source ? `，电源从${sideNames[board.source.side]}侧进入` : ''}${sink ? `，出口在${sideNames[board.sink.side]}侧` : ''}${completed ? '，线路已接通' : '，顺时针旋转'}`}>
          <svg viewBox="0 0 100 100" aria-hidden="true">
            <rect x="9" y="9" width="82" height="82" rx="12" fill="#233f3b" stroke="#5b7970" strokeWidth="1" />
            {directions.map(direction => <circle key={direction} cx={points[direction][0]} cy={points[direction][1]} r="4" fill="#6e8170" />)}
            {ports.map(direction => <g key={direction}><path d={`M50 50L${points[direction][0]} ${points[direction][1]}`} fill="none" stroke="#2b261d" strokeWidth="16" /><path d={`M50 50L${points[direction][0]} ${points[direction][1]}`} fill="none" stroke={completed ? '#f5d985' : '#d2ad66'} strokeWidth="10" /><circle cx={points[direction][0]} cy={points[direction][1]} r="5" fill="#f1d696" /></g>)}
            <circle cx="50" cy="50" r="9" fill="#ccb078" stroke="#f6dfac" strokeWidth="2" />
            <path d="M46 50h8" stroke="#64533b" strokeWidth="2" />
          </svg>
          <span className="v5-module-label">{source ? `电源 · ${sideNames[board.source.side]}侧` : sink ? `出口 · ${sideNames[board.sink.side]}侧` : `${module.row + 1} · ${module.column + 1}`}</span>
          {source && <span className={`v5-terminal v5-terminal-${board.source.side}`} aria-hidden="true">＋</span>}
          {sink && <span className={`v5-terminal v5-terminal-${board.sink.side}`} aria-hidden="true">↗</span>}
        </button>;
      })}
    </div>
    <p className="v5-circuit-caption">{completed ? '线路已由设备确认接通，可以继续探索。' : '接点相碰才会导通 · 检查结果以设备反馈为准'}</p>
  </section>;
}
