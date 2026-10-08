import { useState } from 'react';
import GameCanvas from '../game/GameCanvas';
import { InventoryBar, RoomHud } from './RoomChrome';
import type { SceneInput } from '../game/bridge';
import type { ActionArguments, Receipt, Tool, VisibleState } from '../api';

interface Props {
  state: VisibleState; view: string | null; selectedItemId: string | null; disabled: boolean; animation: Receipt | null; reducedMotion?: boolean;
  codes: Record<string, string>; onCode: (id: string, value: string) => void; onError: (value: string) => void;
  onView: (id: string | null) => void; onObject: (id: string) => void;
  onAction: (tool: Tool, args: ActionArguments) => void; onItem: (id: string) => void;
  onNotebook: () => void; onAssistant: () => void; onMenu: () => void;
}
export default function Room1(props: Props) {
  const { state, view, selectedItemId, onAction } = props;
  const [available, setAvailable] = useState(false);
  const disabled = props.disabled || !available;
  const object = state.objects.find(object => object.object_id === view);
  const clue = object ? state.clues.find(clue => clue.object_id === object.object_id) : null;
  const codeAction = object?.actions.find(action => action.tool === 'submit_code');
  const onInput = (input: SceneInput) => {
    if (input.kind === 'circuit-module' || input.kind === 'sequence-device') return;
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
    <RoomHud state={state} onNotebook={props.onNotebook} onAssistant={props.onAssistant} onMenu={props.onMenu}/>
    <GameCanvas projection={{ state, view: object?.object_id || null, disabled: props.disabled, animation: props.animation, reducedMotion: props.reducedMotion }} onInput={onInput} onAvailability={setAvailable}/>
    {object && <div className="closeup-controls">
      <button className="button closeup-back" disabled={disabled} onClick={() => props.onView(null)}>← 返回房间</button>
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
    <InventoryBar state={state} selectedItemId={selectedItemId} disabled={disabled} onItem={props.onItem}/>
  </section>;
}
