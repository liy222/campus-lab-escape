import GameCanvas from '../game/GameCanvas';
import type { SceneInput } from '../game/bridge';
import type { ActionArguments, Receipt, Tool, VisibleState } from '../api';

interface Props {
  state: VisibleState; view: string | null; selectedItemId: string | null; disabled: boolean; animation: Receipt | null;
  codes: Record<string, string>; onCode: (id: string, value: string) => void; onError: (value: string) => void;
  onView: (id: string | null) => void; onObject: (id: string) => void;
  onAction: (tool: Tool, args: ActionArguments) => void; onItem: (id: string) => void;
  onNotebook: () => void; onAssistant: () => void; onMenu: () => void;
}
export default function Room1(props: Props) {
  const { state, view, disabled, selectedItemId, onAction } = props;
  const object = state.objects.find(object => object.object_id === view);
  const clue = object ? state.clues.find(clue => clue.object_id === object.object_id) : null;
  const codeAction = object?.actions.find(action => action.tool === 'submit_code');
  const onInput = (input: SceneInput) => {
    if (input.kind === 'object') props.onObject(input.objectId);
    else if (selectedItemId && input.tool !== 'move') onAction('use_item', { item_id: selectedItemId, target_id: input.targetId });
    else if (input.tool === 'move') onAction('move', { destination_id: input.targetId });
    else if (input.tool === 'inspect') onAction('inspect', { object_id: input.targetId });
    else {
      const affordance = state.objects.find(value => value.object_id === input.targetId)?.actions.find(action => action.tool === input.tool);
      if (affordance) onAction(affordance.tool, affordance.arguments);
    }
  };
  return <section className="visual-room" aria-label="实验准备室游戏">
    <header className="game-hud"><div><small>CAMPUS LAB / R1</small><h2 id="room-title">{state.room.name}</h2></div><div>
      <button className="hud-button" aria-label="线索笔记" onClick={props.onNotebook}>笔记 <span>{state.clues.length}</span></button>
      <button className="hud-button" aria-label="AI 探索伙伴" onClick={props.onAssistant}>LAB ASSIST</button>
      <button className="hud-button" aria-label="游戏菜单" onClick={props.onMenu}>☰</button>
    </div></header>
    <GameCanvas projection={{ state, view: object?.object_id || null, disabled, animation: props.animation }} onInput={onInput}/>
    {object && <div className="closeup-controls">
      <button className="button closeup-back" onClick={() => props.onView(null)}>← 返回房间</button>
      <span className="closeup-title">{object.name}</span>
      <div className="closeup-actions">{object.actions.filter(action => ['inspect', 'take', 'interact'].includes(action.tool)).map(action => <button key={action.tool} className="button" data-scene-action={action.tool} data-target-id={object.object_id} disabled={disabled} onClick={() => onAction(action.tool, action.arguments)}>{action.label}</button>)}
        {object.object_id === 'r1_door' && state.exits.some(exit => exit.destination_id === 'R2' && exit.unlocked) && <button className="button exit-button" data-scene-action="move" disabled={disabled} onClick={() => onAction('move', { destination_id: 'R2' })}>进入设备实验室 →</button>}
        {selectedItemId && <button className="button use-button" disabled={disabled} onClick={() => onAction('use_item', { item_id: selectedItemId, target_id: object.object_id })}>使用物品 ↗</button>}
      </div>
      {codeAction && <form className="code-form mechanical-lock" onSubmit={event => { event.preventDefault(); const code = props.codes[object.object_id] || ''; if (!/^[0-9]{1,16}$/.test(code)) { props.onError('请输入 1–16 位数字。'); return; } onAction('submit_code', { ...codeAction.arguments, code }); }}>
        <label htmlFor={`code-${object.object_id}`}>输入你推理出的数字</label><div><input id={`code-${object.object_id}`} inputMode="numeric" autoComplete="off" maxLength={16} pattern="[0-9]{1,16}" placeholder="••••" value={props.codes[object.object_id] || ''} disabled={disabled} onChange={event => props.onCode(object.object_id, event.target.value)}/><button className="button" disabled={disabled}>提交</button></div>
      </form>}
      {clue && <article className={`closeup-reading ${object.object_id === 'r1_microscope' ? 'eyepiece-reading' : ''}`}><small>{clue.title}</small><p>{clue.text}</p></article>}
      {!clue && <p className="closeup-description">{object.description}</p>}
    </div>}
    <aside className="inventory-bar inventory" aria-label="我的背包"><span className="inventory-label">背包</span>{state.inventory.map(item => <article className={`inventory-item ${selectedItemId === item.item_id ? 'item-selected' : ''}`} key={item.item_id} data-item-id={item.item_id}>
      <button className="item-select-button" aria-pressed={selectedItemId === item.item_id} aria-label={`${item.name} · ${selectedItemId === item.item_id ? '取消选择' : '选择物品'}`} title={item.description} disabled={disabled} onClick={() => props.onItem(item.item_id)}><span aria-hidden="true" className={`item-glyph item-${item.item_id}`}/><span>{item.name}</span></button>
    </article>)}{Array.from({ length: Math.max(0, 4 - state.inventory.length) }, (_, index) => <span key={index} className="empty-slot" aria-hidden="true"/>)}{selectedItemId && <button className="button subtle cancel-item" onClick={() => props.onItem(selectedItemId)}>取消</button>}</aside>
  </section>;
}
