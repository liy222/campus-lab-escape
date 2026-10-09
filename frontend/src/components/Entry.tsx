import PaintedObject from './PaintedObject';
import { paintedAssets } from '../assets/manifest';
import { room1Assets, room1Layout } from '../assets/manifest';
export default function Entry({ hasSession, disabled, onStart, onContinue }: { hasSession: boolean; disabled: boolean; onStart: () => void; onContinue: () => void }) {
  const objects = ['r1_workbench', 'r1_clock', 'r1_microscope', 'r1_cabinet', 'r1_door'];
  const textures: Record<string, string> = { r1_microscope: 'r1_microscope_empty', r1_cabinet: 'r1_cabinet_locked', r1_door: 'r1_door_closed' };
  return <section className="welcome quiet-entry" aria-label="实验室入口"><div className="entry-room" aria-hidden="true" style={{ backgroundImage: `url(${room1Assets.background})` }}>{objects.map(id => { const box = room1Layout[id]; return box ? <PaintedObject key={id} assetKey={(textures[id] || id) as keyof typeof paintedAssets} box={box}/> : null; })}</div><div className="entry-shade"/><div className="entry-copy"><p className="eyebrow">CAMPUS LAB · NIGHT</p><h1>逃离校园实验室</h1><p>实验室的灯，还亮着。</p><div className="welcome-buttons"><button className="button primary" disabled={disabled} onClick={onStart}>开始新游戏 →</button>{hasSession && <button className="button" disabled={disabled} onClick={onContinue}>继续当前游戏</button>}</div><small>仔细观察，寻找门外的光。</small></div></section>;
}
