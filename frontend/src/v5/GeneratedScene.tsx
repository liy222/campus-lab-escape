import { useEffect, useRef, useState } from 'react';
import Phaser from 'phaser';
import type { SceneModel, SceneObject } from './visual/types';

export type GeneratedObject = SceneObject;

type Props = {
  model: SceneModel;
  disabled: boolean;
  onObject: (id: string) => void;
  roomName: string;
};

export default function GeneratedScene({ model, disabled, onObject, roomName }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const scene = useRef<Phaser.Scene | null>(null);
  const textureAliases = useRef(new Map<string, string>());
  const current = useRef(model);
  current.current = model;
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  const [textures, setTextures] = useState<string[]>([]);

  function draw(target: Phaser.Scene) {
    target.children.list.slice().forEach(child => child.destroy());
    const active = current.current;
    const loadedKey = (key: string) => { const resolved = textureAliases.current.get(key) ?? key; return target.textures.exists(resolved) ? resolved : null; };
    const backgroundKey = loadedKey(active.background.key) ?? (active.background.fallback && loadedKey(active.background.fallback.key));
    if (backgroundKey) {
      target.add.image(800, 450, backgroundKey).setDisplaySize(1600, 900);
    } else {
      target.add.rectangle(800, 450, 1600, 900, 0x16242c);
    }
    active.objects.forEach(object => {
      const primaryKey = loadedKey(object.key);
      const key = primaryKey ?? (object.fallback && loadedKey(object.fallback.key));
      if (!key) {
        // The named, accessible hotspot remains usable when every image fails.
        target.add.rectangle(object.x, object.y - object.renderHeight / 2, 240, 115, 0x344539, 0.9).setStrokeStyle(2, 0xe8c07c);
        target.add.text(object.x, object.y - object.renderHeight / 2, `${object.name}\n图像暂缺`, { fontFamily: 'sans-serif', fontSize: '23px', color: '#f3e5c7', align: 'center', wordWrap: { width: 220 } }).setOrigin(.5);
        return;
      }
      const bbox = primaryKey ? object.bbox : object.fallback!.bbox;
      const texture = target.textures.get(key);
      const crop = `${key}-crop-${bbox.x}-${bbox.y}-${bbox.width}-${bbox.height}`;
      if (!texture.has(crop)) texture.add(crop, 0, bbox.x, bbox.y, bbox.width, bbox.height);
      const scale = object.renderHeight / bbox.height;
      const width = bbox.width * scale;
      target.add.ellipse(object.x, object.y + 6, width * 0.92, Math.max(16, width * 0.16), 0x08110f, 0.42);
      target.add.image(object.x, object.y, key, crop).setOrigin(0.5, 1).setScale(scale);
      if (object.completed) {
        target.add.ellipse(object.x, object.y - object.renderHeight - 26, 34, 34, 0x2f5445, 0.92).setStrokeStyle(2, 0xdfc78c);
      }
    });
  }

  useEffect(() => {
    if (!host.current) return;
    let mounted = true;
    setReady(false);
    setFailed(false);
    const active = current.current;
    class GeneratedRoom extends Phaser.Scene {
      constructor() { super('generated-studio'); }
      preload() {
        const resources = [active.background, ...(active.background.fallback ? [active.background.fallback] : []),
          ...active.objects.flatMap(object => [{ key: object.key, src: object.src }, ...(object.fallback ? [object.fallback] : [])]), ...active.extras];
        const urls = new Map<string, string>();
        textureAliases.current = new Map();
        resources.forEach(resource => {
          const existing = urls.get(resource.src);
          textureAliases.current.set(resource.key, existing ?? resource.key);
          if (existing) return;
          urls.set(resource.src, resource.key);
          this.load.image(resource.key, resource.src);
        });
        this.load.on('loaderror', () => { if (mounted) setFailed(true); });
      }
      create() {
        scene.current = this;
        draw(this);
        if (mounted) {
          setTextures(this.textures.getTextureKeys().filter(key => key.startsWith('theme:') || key.startsWith('legacy:') || key.startsWith('fallback:')));
          setReady(true);
        }
      }
    }
    const game = new Phaser.Game({
      type: Phaser.CANVAS,
      parent: host.current,
      width: 1600,
      height: 900,
      backgroundColor: '#101c24',
      scene: GeneratedRoom,
      scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
      audio: { noAudio: true },
      banner: false,
    });
    return () => { mounted = false; scene.current = null; game.destroy(true); };
  }, [retry, model.background.key]);

  useEffect(() => { if (ready && scene.current) draw(scene.current); }, [model, ready]);

  return <div className="v5-scene" aria-label={`${roomName}固定视角场景`} data-theme={model.themeId ?? 'generic'} data-background={model.background.src} data-textures={textures.join(' ')}>
    <div ref={host} className="v5-phaser" />
    {!ready && !failed && <p className="v5-scene-status" role="status">正在铺开场景…</p>}
    {failed && <div className="v5-scene-status" role="alert">部分素材未加载，已使用可用资源或文字标记。<button onClick={() => setRetry(value => value + 1)}>重试加载</button></div>}
    <div className="v5-hotspots" aria-label="场景内可见物件">
      {model.objects.map(object => {
        const left = Math.min(89, Math.max(11, (object.hotspot.x + object.hotspot.width / 2) / 16));
        const top = Math.min(92, Math.max(9, (object.hotspot.y + object.hotspot.height * 0.72) / 9));
        return <button key={object.object_id} disabled={disabled || !ready} style={{ left: `${left}%`, top: `${top}%` }}
          onClick={() => onObject(object.object_id)} aria-label={`查看${object.name}${object.completed ? '（已完成）' : ''}`}
          className={object.completed ? 'is-done' : ''} data-variant={object.variantId ?? 'generic'} data-object={object.object_id}>
          <span className="v5-hotspot-dot" aria-hidden="true">{object.completed ? '✓' : ''}</span>
          <span className="v5-hotspot-name">{object.name}</span>
        </button>;
      })}
    </div>
  </div>;
}
