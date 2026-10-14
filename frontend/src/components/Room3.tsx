import { useState } from 'react';
import GameCanvas from '../game/GameCanvas';
import type { SceneInput } from '../game/bridge';
import { InventoryBar, RoomBackdrop, RoomHud } from './RoomChrome';
import type { ActionArguments, Receipt, Tool, VisibleState } from '../api';

interface Props {
  state: VisibleState; view: string | null; selectedItemId: string | null; disabled: boolean; animation: Receipt | null; reducedMotion: boolean;
  sequenceDraft: string[]; onDraft: (draft: string[]) => void;
  onView: (id: string | null) => void; onObject: (id: string) => void; onAction: (tool: Tool, args: ActionArguments) => void;
  onItem: (id: string) => void; onNotebook: () => void; onAssistant: () => void; onMenu: () => void;
}
export default function Room3(props: Props) {
  const { state, view, selectedItemId, onAction } = props;
  const [available, setAvailable] = useState(false), [marker, setMarker] = useState('idle');
  const disabled = props.disabled || !available || marker === 'door_open';
  const object = state.objects.find(object => object.object_id === view), clue = state.clues.find(clue => clue.object_id === view);
  const sequence = view === 'r3_panel' ? state.minigames?.sequence : null;
  const submitSequence = object?.actions.find(action => action.tool === 'submit_sequence');
  const startCheck = state.device_states?.exit === 'CARD_ACCEPTED'
    ? state.objects.find(object => object.object_id === 'exit_door')?.actions.find(action => action.tool === 'interact')
    : undefined;
  const sequenceInstruction = sequence?.status === 'completed'
    ? '终检已通过。请前往实验室出口释放门锁，再推开出口。'
    : submitSequence
      ? '终检已启动。按你推理出的次序点选四个设备，再提交顺序。'
      : state.device_states?.exit === 'CARD_ACCEPTED'
        ? '门禁卡已接受。请先启动终检；当前顺序草稿会保留。'
        : '请先在实验室出口使用门禁卡，再返回此处启动终检。现在可以先填写顺序草稿。';
  const onInput = (input: SceneInput) => {
    if (disabled || input.kind === 'circuit-module') return;
    if (input.kind === 'object') {
      if (input.objectId === 'r3_panel' && state.puzzle_states?.panel === 'STRIP_INSERTED') onAction('inspect', { object_id: input.objectId });
      else props.onObject(input.objectId);
      return;
    }
    if (input.kind === 'sequence-device') {
      if (sequence?.status === 'editing' && props.sequenceDraft.length < sequence.length && sequence.devices.some(device => device.device_id === input.deviceId)) props.onDraft([...props.sequenceDraft, input.deviceId]);
      return;
    }
    if (selectedItemId && input.tool !== 'move') onAction('use_item', { item_id: selectedItemId, target_id: input.targetId });
    else if (input.tool === 'move') onAction('move', { destination_id: input.targetId });
    else if (input.tool === 'inspect') onAction('inspect', { object_id: input.targetId });
    else { const action = state.objects.find(object => object.object_id === input.targetId)?.actions.find(action => action.tool === input.tool); if (action) onAction(action.tool, action.arguments); }
  };
  return <section className="visual-room room3-room" data-closeup={object?.object_id || 'room'} aria-label="出口控制室游戏">
    <RoomBackdrop state={state}/>
    <RoomHud state={state} onNotebook={props.onNotebook} onAssistant={props.onAssistant} onMenu={props.onMenu}/>
    <GameCanvas projection={{ state, view: object?.object_id || null, disabled: props.disabled, animation: props.animation, sequenceDraft: props.sequenceDraft, reducedMotion: props.reducedMotion }} onInput={onInput} onAvailability={setAvailable} onAnimation={setMarker}/>
    {object && <div className="closeup-controls room3-controls">
      <button className="button closeup-back" disabled={disabled} onClick={() => props.onView(null)}>← 返回房间</button><span className="closeup-title">{object.name}</span>
      <div className="closeup-actions">{object.actions.filter(action => ['inspect', 'interact'].includes(action.tool)).map(action => <button key={action.tool} className="button" data-scene-action={action.tool} data-target-id={object.object_id} disabled={disabled} onClick={() => onAction(action.tool, action.arguments)}>{action.label}</button>)}
        {object.object_id === 'exit_door' && state.exits.some(exit => exit.destination_id === 'EXIT' && exit.unlocked) && <button className="button exit-button" data-scene-action="move" data-target-id="EXIT" disabled={disabled} onClick={() => onAction('move', { destination_id: 'EXIT' })}>走出实验室 →</button>}
        {selectedItemId && <button className="button use-button" disabled={disabled} onClick={() => onAction('use_item', { item_id: selectedItemId, target_id: object.object_id })}>使用物品 ↗</button>}
      </div>
      {sequence && <section className="sequence-controls" aria-label="设备顺序草稿" data-sequence-status={sequence.status}>
        <p className="minigame-instructions sequence-instructions" role="status">{sequenceInstruction}</p>
        <ol className="sequence-draft" aria-label="当前顺序草稿">{Array.from({ length: sequence.length }, (_, index) => { const id = props.sequenceDraft[index], device = sequence.devices.find(device => device.device_id === id); return <li key={index} data-draft-index={index} data-device-id={sequence.status === 'completed' ? undefined : id}><span>{index + 1}</span><strong>{sequence.status === 'completed' ? '已通过' : device ? `${device.symbol} ${device.label}` : '待选择'}</strong></li>; })}</ol>
        <div className="minigame-actions">{startCheck && <button className="button sequence-start" data-scene-action={startCheck.tool} data-target-id="exit_door" disabled={disabled} onClick={() => onAction(startCheck.tool, startCheck.arguments)}>{startCheck.label}</button>}<button className="button sequence-clear" disabled={disabled || !props.sequenceDraft.length || sequence.status === 'completed'} onClick={() => props.onDraft([])}>清除草稿</button><button className="button sequence-submit" data-scene-action="submit_sequence" data-target-id={sequence.target_id} disabled={disabled || props.sequenceDraft.length !== sequence.length || sequence.status === 'completed' || !submitSequence} onClick={() => { if (submitSequence) onAction(submitSequence.tool, { ...submitSequence.arguments, device_ids: props.sequenceDraft }); }}>提交顺序</button></div>
      </section>}
      {clue && <article className="closeup-reading"><small>{clue.title}</small><p>{clue.text}</p></article>}
      {!clue && !sequence && <p className="closeup-description">{object.description}</p>}
    </div>}
    <InventoryBar state={state} selectedItemId={selectedItemId} disabled={disabled} onItem={props.onItem}/>
  </section>;
}
