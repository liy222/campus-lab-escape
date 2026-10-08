import { useEffect, useRef, useState, type ReactNode } from 'react';
import { GameBridge, type SceneInput, type SceneProjection } from './bridge';
import type { Room2Hotspot } from './Room2Scene';

type RoomScene = { sync: (projection: SceneProjection) => void; activate: (input: SceneInput) => void; input: { enabled: boolean } };
type Hotspots = (projection: SceneProjection) => Room2Hotspot[];
interface Props { projection: SceneProjection; onInput: (input: SceneInput) => void; children?: ReactNode; onAvailability?: (ready: boolean) => void; onAnimation?: (marker: string) => void }
export default function GameCanvas({ projection, onInput, children, onAvailability, onAnimation }: Props) {
  const host = useRef<HTMLDivElement>(null), scene = useRef<RoomScene | null>(null), bridge = useRef<GameBridge | null>(null);
  const latest = useRef({ projection, onInput, onAvailability, onAnimation }); latest.current = { projection, onInput, onAvailability, onAnimation };
  const [ready, setReady] = useState(false), [renderer, setRenderer] = useState('loading'), [missing, setMissing] = useState<string[]>([]);
  const [failure, setFailure] = useState(''), [attempt, setAttempt] = useState(0), [animation, setAnimation] = useState('idle');
  const [minHitArea, setMinHitArea] = useState(44), [hotspotFactory, setHotspotFactory] = useState<Hotspots | null>(null);
  const available = ready && missing.length === 0 && !failure;
  const displayProjection = { ...projection, minHitArea, disabled: projection.disabled || !available };
  const roomId = projection.state.room.room_id, hotspots = hotspotFactory?.(displayProjection) || [];
  useEffect(() => {
    const observer = new ResizeObserver(entries => { const width = entries[0]?.contentRect.width; if (width) setMinHitArea(44 * 1600 / width); });
    if (host.current) observer.observe(host.current); return () => observer.disconnect();
  }, []);
  useEffect(() => {
    let disposed = false; let game: { destroy: (removeCanvas: boolean) => void } | null = null;
    setReady(false); setMissing([]); setFailure(''); setRenderer('loading'); setAnimation('idle'); setHotspotFactory(null); latest.current.onAvailability?.(false);
    const channel = new GameBridge({ ...latest.current.projection, disabled: true }, input => latest.current.onInput(input)); bridge.current = channel;
    async function start() {
      try {
        const [engine, module] = await Promise.all([import('phaser'), roomId === 'R3' ? import('./Room3Scene') : roomId === 'R2' ? import('./Room2Scene') : import('./Room1Scene')]);
        if (disposed) return;
        const Phaser = engine.default;
        const factory: Hotspots = 'room3Hotspots' in module ? module.room3Hotspots : 'room2Hotspots' in module ? module.room2Hotspots : module.sceneHotspots;
        setHotspotFactory(() => factory);
        const room = new module.default(channel, (type: string, absent: string[]) => {
          if (disposed) return; setRenderer(type); setMissing(absent); setReady(true); latest.current.onAvailability?.(absent.length === 0);
        }, (marker: string) => { if (!disposed) { setAnimation(marker); latest.current.onAnimation?.(marker); } });
        scene.current = room;
        game = new Phaser.Game({ type: Phaser.CANVAS, parent: host.current!, width: 1600, height: 900,
          backgroundColor: '#1b242b', scene: [room], audio: { noAudio: true }, render: { antialias: true }, input: { windowEvents: false },
          scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH, width: 1600, height: 900 } });
      } catch { if (!disposed) { setFailure('画面暂时未能打开，请重试。'); latest.current.onAvailability?.(false); } }
    }
    void start();
    return () => { disposed = true; scene.current = null; bridge.current = null; game?.destroy(true); };
  }, [roomId, attempt]);
  useEffect(() => {
    if (bridge.current) bridge.current.projection = displayProjection;
    if (scene.current?.input) { scene.current.input.enabled = !displayProjection.disabled; scene.current.sync(displayProjection); }
  }, [projection.state, projection.view, projection.disabled, projection.animation, projection.sequenceDraft, projection.reducedMotion, minHitArea, available]);
  return <div className="game-canvas-host" data-room={roomId} data-view={projection.view || 'room'} data-assets-ready={!!available}
    data-renderer={renderer} data-animation={animation} data-cabinet-state={projection.state.device_states?.cabinet}
    data-microscope-state={projection.state.puzzle_states?.microscope} data-panel-state={projection.state.puzzle_states?.panel} data-exit-state={projection.state.device_states?.exit}
    data-powerbox-state={projection.state.device_states?.powerbox} data-computer-state={projection.state.device_states?.computer}
    data-circuit-status={projection.state.minigames?.circuit?.status} data-sequence-status={projection.state.minigames?.sequence?.status} aria-label={`${projection.state.room.name}画面`}>
    <div ref={host} className="phaser-mount"/>
    {!ready && !failure && <div className="canvas-loading" role="status">正在打开{projection.state.room.name}…</div>}
    {(failure || missing.length > 0) && <div className="canvas-loading canvas-error" role="alert"><p>{failure || '部分画面未能载入，请重试。'}</p><button className="button canvas-retry" disabled={projection.disabled} onClick={() => { latest.current.onAvailability?.(false); setAttempt(value => value + 1); }}>重新载入画面</button></div>}
    <div className="scene-keyboard-layer" aria-label="房间物件键盘操作">
      {hotspots.map(hotspot => <button key={`${hotspot.id}-${hotspot.input.kind}`} type="button" className="scene-keyboard-hotspot"
        data-object-id={hotspot.id} data-bounds={hotspot.box.join(',')} data-scene-action={hotspot.input.kind === 'action' ? hotspot.input.tool : hotspot.input.kind === 'circuit-module' ? 'rotate_circuit' : hotspot.input.kind === 'sequence-device' ? 'sequence_device' : 'object'}
        data-module-id={hotspot.moduleId} data-rotation={hotspot.rotation} data-device-id={hotspot.input.kind === 'sequence-device' ? hotspot.input.deviceId : undefined} data-target-id={hotspot.input.kind === 'object' ? undefined : hotspot.input.targetId}
        aria-label={hotspot.label} disabled={!available || projection.disabled || hotspot.disabled || animation === 'door_open'}
        style={{ left: `${hotspot.box[0] / 16}%`, top: `${hotspot.box[1] / 9}%`, width: `${hotspot.box[2] / 16}%`, height: `${hotspot.box[3] / 9}%` }}
        onClick={() => scene.current?.activate(hotspot.input)}><span>{hotspot.label}</span></button>)}
    </div>
    {children}
  </div>;
}
