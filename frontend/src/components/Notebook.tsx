import { useEffect, useRef } from 'react';
import type { VisibleState } from '../api';
import { trapPanelFocus } from './panelFocus';

export default function Notebook({ state, page, onPage, onClose }: { state: VisibleState; page: number; onPage: (page: number) => void; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { ref.current?.focus(); }, []);
  const pages = Math.max(1, Math.ceil(state.clues.length / 2));
  const current = Math.min(page, pages - 1);
  return <div className="notebook-modal" role="dialog" aria-modal="true" aria-labelledby="notebook-title" tabIndex={-1} ref={ref} onKeyDown={event => { trapPanelFocus(event); if (event.key === 'Escape') onClose(); }}>
    <header><div><small>FIELD NOTES</small><h2 id="notebook-title">线索笔记</h2></div><button className="button subtle" onClick={onClose}>合上笔记</button></header>
    <ol className="clue-list">{state.clues.slice(current * 2, current * 2 + 2).map(clue => <li key={clue.clue_id} id={`clue-${clue.clue_id}`} tabIndex={-1}>
      <h3>{clue.title}</h3><p>{clue.text}</p></li>)}</ol>
    {!state.clues.length && <p className="notebook-empty">第一页，等待发现。</p>}
    <nav aria-label="笔记翻页"><button className="button" disabled={current === 0} onClick={() => onPage(current - 1)}>上一页</button><span>{current + 1} / {pages}</span><button className="button" disabled={current + 1 >= pages} onClick={() => onPage(current + 1)}>下一页</button></nav>
  </div>;
}
