import type { VisibleState } from '../api';

export function RoomHud({ state, onNotebook, onAssistant, onMenu }: { state: VisibleState; onNotebook: () => void; onAssistant: () => void; onMenu: () => void }) {
  return <header className="game-hud"><div><small>CAMPUS LAB / {state.room.room_id}</small><h2 id="room-title">{state.room.name}</h2></div><div>
    <button className="hud-button" aria-label="线索笔记" onClick={onNotebook}>笔记 <span>{state.clues.length}</span></button>
    <button className="hud-button" aria-label="AI 探索伙伴" onClick={onAssistant}>LAB ASSIST</button>
    <button className="hud-button" aria-label="游戏菜单" onClick={onMenu}>☰</button>
  </div></header>;
}
export function InventoryBar({ state, selectedItemId, disabled, onItem }: { state: VisibleState; selectedItemId: string | null; disabled: boolean; onItem: (id: string) => void }) {
  return <aside className="inventory-bar inventory" aria-label="我的背包"><span className="inventory-label">背包</span>{state.inventory.map(item => <article className={`inventory-item ${selectedItemId === item.item_id ? 'item-selected' : ''}`} key={item.item_id} data-item-id={item.item_id}>
    <button className="item-select-button" aria-pressed={selectedItemId === item.item_id} aria-label={`${item.name} · ${selectedItemId === item.item_id ? '取消选择' : '选择物品'}`} title={item.description} disabled={disabled} onClick={() => onItem(item.item_id)}><span aria-hidden="true" className={`item-glyph item-${item.item_id}`}/><span>{item.name}</span></button>
  </article>)}{Array.from({ length: Math.max(0, 4 - state.inventory.length) }, (_, index) => <span key={index} className="empty-slot" aria-hidden="true"/>)}{selectedItemId && <button className="button subtle cancel-item" disabled={disabled} onClick={() => onItem(selectedItemId)}>取消</button>}</aside>;
}
