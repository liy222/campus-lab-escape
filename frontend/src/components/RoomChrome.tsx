import PaintedObject from './PaintedObject';
import { useEffect, useState } from 'react';
import type { VisibleState } from '../api';
import { room1Assets, room2Assets, room3Assets } from '../assets/manifest';

export function useCompactStage() {
  const query = '(max-width:760px) and (orientation:portrait), (max-height:520px)';
  const [compact, setCompact] = useState(() => window.matchMedia(query).matches);
  useEffect(() => { const media = window.matchMedia(query), update = () => setCompact(media.matches); media.addEventListener('change', update); return () => media.removeEventListener('change', update); }, []);
  return compact;
}

export function RoomBackdrop({ state }: { state: VisibleState }) {
  const image = state.room.room_id === 'R3' ? (state.progress.power_on ? room3Assets.r3_background : room3Assets.r3_background_off) : state.room.room_id === 'R2' ? (state.progress.power_on ? room2Assets.r2_background_on : room2Assets.r2_background_dark) : room1Assets.background;
  return <div className="stage-ambience" aria-hidden="true" style={{ backgroundImage: `url(${image})` }}/>;
}


export function RoomHud({ state, onNotebook, onAssistant, onMenu }: { state: VisibleState; onNotebook: () => void; onAssistant: () => void; onMenu: () => void }) {
  return <header className="game-hud"><div><small>CAMPUS LAB / {state.room.room_id}</small><h2 id="room-title">{state.room.name}</h2></div><div>
    <button className="hud-button" aria-label="线索笔记" onClick={onNotebook}>笔记 <span>{state.clues.length}</span></button>
    <button className="hud-button" aria-label="AI 探索伙伴" onClick={onAssistant}><span className="hud-label-long">LAB ASSIST</span><span className="hud-label-short">伙伴</span></button>
    <button className="hud-button" aria-label="游戏菜单" onClick={onMenu}>☰</button>
  </div></header>;
}
export function InventoryBar({ state, selectedItemId, disabled, onItem }: { state: VisibleState; selectedItemId: string | null; disabled: boolean; onItem: (id: string) => void }) {
  return <aside className="inventory-bar inventory" aria-label="我的背包"><span className="inventory-label">背包</span>{state.inventory.map(item => <article className={`inventory-item ${selectedItemId === item.item_id ? 'item-selected' : ''}`} key={item.item_id} data-item-id={item.item_id}>
    <button className="item-select-button" aria-pressed={selectedItemId === item.item_id} aria-label={`${item.name} · ${selectedItemId === item.item_id ? '取消选择' : '选择物品'}`} title={item.description} disabled={disabled} onClick={() => onItem(item.item_id)}><PaintedObject className="inventory-painted" assetKey={item.item_id === 'fuse' ? 'r1_fuse' : item.item_id === 'research_strip' ? 'r2_research_strip' : item.item_id === 'access_card' ? 'r2_access_card' : 'sample_slide'}/><span>{item.name}</span></button>
  </article>)}{Array.from({ length: Math.max(0, 4 - state.inventory.length) }, (_, index) => <span key={index} className="empty-slot" aria-hidden="true"/>)}{selectedItemId && <button className="button subtle cancel-item" disabled={disabled} onClick={() => onItem(selectedItemId)}>取消</button>}</aside>;
}
