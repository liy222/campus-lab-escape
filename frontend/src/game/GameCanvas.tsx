import { useEffect, useRef, useState, type ReactNode } from 'react';
import Phaser from 'phaser';
import { GameBridge, type SceneInput, type SceneProjection } from './bridge';
import Room1Scene, { sceneHotspots } from './Room1Scene';
import Room2Scene, { room2Hotspots, type Room2Hotspot } from './Room2Scene';

interface Props { projection: SceneProjection; onInput: (input: SceneInput) => void; children?: ReactNode }
export default function GameCanvas({ projection, onInput, children }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const scene = useRef<Room1Scene | Room2Scene | null>(null);
  const bridge = useRef<GameBridge | null>(null);
  const latest = useRef({ projection, onInput }); latest.current = { projection, onInput };
  const [ready, setReady] = useState(false);
  const [renderer, setRenderer] = useState('loading');
  const [missing, setMissing] = useState<string[]>([]);
  const [animation, setAnimation] = useState('idle');
  const [minHitArea, setMinHitArea] = useState(44);
  const displayProjection = { ...projection, minHitArea };
  const roomId = projection.state.room.room_id;
  const hotspots: Room2Hotspot[] = roomId === 'R2' ? room2Hotspots(displayProjection) : sceneHotspots(displayProjection);
  useEffect(() => {
    const observer = new ResizeObserver(entries => { const width = entries[0]?.contentRect.width; if (width) setMinHitArea(44 * 1600 / width); });
    if (host.current) observer.observe(host.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    let disposed = false;
    setReady(false); setMissing([]); setAnimation('idle');
    const channel = new GameBridge(latest.current.projection, input => latest.current.onInput(input)); bridge.current = channel;
    const Scene = roomId === 'R2' ? Room2Scene : Room1Scene;
    const room = new Scene(channel, (type, absent) => { if (!disposed) { setRenderer(type); setMissing(absent); setReady(true); } }, marker => { if (!disposed) setAnimation(marker); });
    scene.current = room;
    const game = new Phaser.Game({ type: Phaser.CANVAS, parent: host.current!, width: 1600, height: 900,
      backgroundColor: '#1b242b', scene: [room], audio: { noAudio: true }, render: { antialias: true },
      input: { windowEvents: false },
      scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH, width: 1600, height: 900 } });
    return () => { disposed = true; scene.current = null; bridge.current = null; game.destroy(true); };
  }, [roomId]);
  useEffect(() => {
    if (bridge.current) bridge.current.projection = displayProjection;
    scene.current?.sync(displayProjection);
  }, [projection.state, projection.view, projection.disabled, projection.animation, minHitArea]);
  return <div className="game-canvas-host" data-room={roomId} data-view={projection.view || 'room'} data-assets-ready={ready && missing.length === 0}
    data-renderer={renderer} data-animation={animation} data-cabinet-state={projection.state.device_states?.cabinet}
    data-microscope-state={projection.state.puzzle_states?.microscope}
    data-powerbox-state={projection.state.device_states?.powerbox} data-computer-state={projection.state.device_states?.computer}
    data-circuit-status={projection.state.minigames?.circuit?.status} aria-label={`${projection.state.room.name}画面`}>
    <div ref={host} className="phaser-mount"/>
    {!ready && <div className="canvas-loading" role="status">正在打开{projection.state.room.name}…</div>}
    {missing.length > 0 && <div className="canvas-loading" role="alert">部分画面未能载入，请刷新页面。</div>}
    <div className="scene-keyboard-layer" aria-label="房间物件键盘操作">
      {hotspots.map(hotspot => <button key={`${hotspot.id}-${hotspot.input.kind}`} type="button" className="scene-keyboard-hotspot"
        data-object-id={hotspot.id} data-bounds={hotspot.box.join(',')} data-scene-action={hotspot.input.kind === 'action' ? hotspot.input.tool : hotspot.input.kind === 'circuit-module' ? 'rotate_circuit' : 'object'}
        data-module-id={hotspot.moduleId} data-rotation={hotspot.rotation} data-target-id={hotspot.input.kind === 'object' ? undefined : hotspot.input.targetId}
        aria-label={hotspot.label} disabled={!ready || projection.disabled || hotspot.disabled}
        style={{ left: `${hotspot.box[0] / 16}%`, top: `${hotspot.box[1] / 9}%`, width: `${hotspot.box[2] / 16}%`, height: `${hotspot.box[3] / 9}%` }}
        onClick={() => scene.current?.activate(hotspot.input)}><span>{hotspot.label}</span></button>)}
    </div>
    {children}
  </div>;
}
