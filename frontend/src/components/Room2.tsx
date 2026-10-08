import GameCanvas from '../game/GameCanvas';
import type { SceneInput } from '../game/bridge';
import { InventoryBar, RoomHud } from './RoomChrome';
import type { ActionArguments, Receipt, Tool, VisibleState } from '../api';

interface Props {
  state: VisibleState; view: string | null; selectedItemId: string | null; disabled: boolean; animation: Receipt | null;
  loginCredentials: { username: string; password: string }; onLogin: (field: 'username' | 'password', value: string) => void;
  onView: (id: string | null) => void; onObject: (id: string) => void; onAction: (tool: Tool, args: ActionArguments) => void;
  onItem: (id: string) => void; onNotebook: () => void; onAssistant: () => void; onMenu: () => void;
}
export default function Room2(props: Props) {
  const { state, view, disabled, selectedItemId, onAction } = props;
  const object = state.objects.find(value => value.object_id === view);
  const clue = object ? state.clues.find(value => value.object_id === object.object_id) : null;
  const login = object?.actions.find(action => action.tool === 'submit_login');
  const circuit = view === 'r2_powerbox' ? state.minigames?.circuit : null;
  const onInput = (input: SceneInput) => {
    if (input.kind === 'object') { props.onObject(input.objectId); return; }
    if (input.kind === 'circuit-module') {
      if (selectedItemId) onAction('use_item', { item_id: selectedItemId, target_id: input.targetId });
      else onAction('rotate_circuit', { target_id: input.targetId, module_id: input.moduleId });
      return;
    }
    if (selectedItemId && input.tool !== 'move' && input.tool !== 'submit_circuit') onAction('use_item', { item_id: selectedItemId, target_id: input.targetId });
    else if (input.tool === 'move') onAction('move', { destination_id: input.targetId });
    else if (input.tool === 'inspect') onAction('inspect', { object_id: input.targetId });
    else {
      const affordance = state.objects.find(value => value.object_id === input.targetId)?.actions.find(action => action.tool === input.tool);
      if (affordance) onAction(affordance.tool, affordance.arguments);
    }
  };
  return <section className="visual-room room2-room" aria-label="设备实验室游戏">
    <RoomHud state={state} onNotebook={props.onNotebook} onAssistant={props.onAssistant} onMenu={props.onMenu}/>
    <GameCanvas projection={{ state, view: object?.object_id || null, disabled, animation: props.animation }} onInput={onInput}>
      {login && <form className="login-form crt-login" onSubmit={event => { event.preventDefault(); onAction('submit_login', { ...login.arguments, username: props.loginCredentials.username, password: props.loginCredentials.password }); }}>
        <h3>LAB TERMINAL</h3><label htmlFor="terminal-username">USER</label><input id="terminal-username" name="username" autoComplete="off" spellCheck={false} value={props.loginCredentials.username} disabled={disabled} onChange={event => props.onLogin('username', event.target.value)}/>
        <label htmlFor="terminal-password">PASS</label><input id="terminal-password" name="password" type="password" autoComplete="off" value={props.loginCredentials.password} disabled={disabled} onChange={event => props.onLogin('password', event.target.value)}/>
        <button className="button" data-scene-action="submit_login" data-target-id="r2_monitor" disabled={disabled}>[ AUTHENTICATE ]</button>
      </form>}
    </GameCanvas>
    {object && <div className="closeup-controls room2-controls">
      <button className="button closeup-back" onClick={() => props.onView(null)}>← 返回房间</button><span className="closeup-title">{object.name}</span>
      <div className="closeup-actions">{object.actions.filter(action => ['inspect', 'take', 'interact'].includes(action.tool)).map(action => <button key={action.tool} className="button" data-scene-action={action.tool} data-target-id={object.object_id} disabled={disabled} onClick={() => onAction(action.tool, action.arguments)}>{action.label}</button>)}
        {object.object_id === 'r2_door' && state.exits.some(exit => exit.destination_id === 'R3' && exit.unlocked) && <button className="button exit-button" data-scene-action="move" data-target-id="R3" disabled={disabled} onClick={() => onAction('move', { destination_id: 'R3' })}>进入出口控制室 →</button>}
        {selectedItemId && <button className="button use-button" disabled={disabled} onClick={() => onAction('use_item', { item_id: selectedItemId, target_id: object.object_id })}>使用物品 ↗</button>}
        {circuit && <button className="button circuit-submit" data-scene-action="submit_circuit" data-target-id={circuit.target_id} disabled={disabled || circuit.status === 'completed'} onClick={() => { const submit = object.actions.find(action => action.tool === 'submit_circuit'); if (submit) onAction(submit.tool, submit.arguments); }}>提交线路</button>}
      </div>
      {clue && <article className="closeup-reading"><small>{clue.title}</small><p>{clue.text}</p></article>}
      {!clue && !login && <p className="closeup-description">{object.description}</p>}
      {circuit && <p className="circuit-instruction">{circuit.status === 'completed' ? '线路已通过检查。' : '点击线路模块，顺时针旋转90°；调整完成后提交检查。'}</p>}
    </div>}
    <InventoryBar state={state} selectedItemId={selectedItemId} disabled={disabled} onItem={props.onItem}/>
  </section>;
}
