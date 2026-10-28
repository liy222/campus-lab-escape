import { useEffect, useRef, useState } from 'react';
import Phaser from 'phaser';
import catalog from '../assets/generated-catalog.json';
import type { GameObject, VisibleState } from '../api';
export type GeneratedObject = GameObject & { art_id: string; slot: number; target_id?: string | null; completed?: boolean; canonical_overlay?: string };
export type GeneratedState = Omit<VisibleState, 'objects' | 'room' | 'minigames'> & { mode: 'generated'; level_id: string; definition_hash: string; room: VisibleState['room'] & { background_id?: string; background_art_id?: string }; objects: GeneratedObject[]; minigames?: VisibleState['minigames'] & { circuits?: NonNullable<VisibleState['minigames']>['circuit'][]; sequences?: NonNullable<VisibleState['minigames']>['sequence'][] } };
const positions = [[210, 290], [600, 290], [1000, 290], [1390, 290], [210, 635], [600, 635], [1000, 635], [1390, 635]];
export default function GeneratedScene({ state, disabled, onObject }: { state: GeneratedState; disabled: boolean; onObject: (id: string) => void }) {
  const host = useRef<HTMLDivElement>(null), scene = useRef<Phaser.Scene | null>(null), current = useRef(state); current.current = state;
  const [ready, setReady] = useState(false), [failed, setFailed] = useState(false), [retry, setRetry] = useState(0);
  function draw(s: Phaser.Scene) {
    s.children.list.slice().forEach(child => child.destroy());
    const st = current.current;
    const background = st.room.background_art_id || st.room.background_id || 'neutral_lab';
    if (s.textures.exists(background)) s.add.image(800, 450, background).setDisplaySize(1600, 900);
    s.add.rectangle(800, 450, 1600, 900, 0x142829, .19);
    s.add.rectangle(800, 32, 1600, 64, 0x122522, .48);
    st.objects.forEach(object => {
      const asset = catalog.assets.find(asset => asset.id === object.art_id && asset.role === 'object');
      const position = positions[Math.max(0, Math.min(7, object.slot))] || positions[0];
      // Keep the published slot positions; only the hand-painted presentation changes.
      s.add.ellipse(position[0], position[1] + 117, 290, 55, 0x0e211f, .48);
      s.add.ellipse(position[0], position[1] + 38, 305, 230, 0xf2dba5, .11);
      if (asset && s.textures.exists(asset.id)) {
        const texture = s.textures.get(asset.id), crop = `${asset.id}-crop`;
        if (!texture.has(crop)) texture.add(crop, 0, asset.bbox.x, asset.bbox.y, asset.bbox.width, asset.bbox.height);
        const scale = Math.min(310 / asset.bbox.width, 245 / asset.bbox.height);
        s.add.image(position[0], position[1] + 27, asset.id, crop).setScale(scale);
        if (asset.mask_content) s.add.rectangle(position[0], position[1] + 27, 160, 190, 0xd7c9a9).setStrokeStyle(3, 0x9d8d69);
      }
      if (object.completed) s.add.text(position[0], position[1] - 115, '✓ 已完成', { fontFamily: 'sans-serif', fontSize: '23px', color: '#fff0bd', backgroundColor: '#315749', padding: { x: 14, y: 7 } }).setOrigin(.5);
    });
  }
  useEffect(() => {
    if (!host.current) return;
    let mounted = true;
    setReady(false); setFailed(false);
    class Generic extends Phaser.Scene {
      constructor() { super('generated-campus'); }
      preload() { catalog.assets.forEach(asset => this.load.image(asset.id, asset.url)); this.load.on('loaderror', () => { if (mounted) setFailed(true); }); }
      create() { scene.current = this; draw(this); if (mounted) setReady(true); }
    }
    const game = new Phaser.Game({ type: Phaser.CANVAS, parent: host.current, width: 1600, height: 900, backgroundColor: '#203831', scene: Generic, scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH }, audio: { noAudio: true }, banner: false });
    return () => { mounted = false; scene.current = null; game.destroy(true); };
  }, [retry]);
  useEffect(() => { if (ready && scene.current) draw(scene.current); }, [state, ready]);
  return <div className="v5-scene" aria-label={`${state.room.name}固定视角场景`}>
    <div ref={host} className="v5-phaser" />
    <div className="v5-scene-caption" aria-hidden="true"><span>现场勘察</span><span>点击物件 · 查看细节</span></div>
    {!ready && <p className="v5-scene-status" role="status">正在加载已有手绘材料…</p>}
    {failed && <div className="v5-scene-status" role="alert">部分材料未加载。<button onClick={() => setRetry(value => value + 1)}>重试加载</button></div>}
    <div className="v5-hotspots" aria-label="可见物件">{state.objects.map(object => {
      const position = positions[Math.max(0, Math.min(7, object.slot))] || positions[0];
      return <button key={object.object_id} disabled={disabled || !ready} style={{ left: `${position[0] / 16}%`, top: `${(position[1] + 150) / 9}%` }} onClick={() => onObject(object.object_id)} aria-label={`查看${object.name}`}><span className="v5-hotspot-dot" aria-hidden="true">{object.completed ? '✓' : '◇'}</span><span>{object.name}</span></button>;
    })}</div>
  </div>;
}
