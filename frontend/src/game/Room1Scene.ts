import Phaser from 'phaser';
import { room1Assets, room1Layout } from '../assets/manifest';
import { GameBridge, type SceneInput, type SceneProjection } from './bridge';

export interface SceneHotspot { id: string; label: string; box: [number, number, number, number]; input: SceneInput }
const children = new Set(['r1_symbols', 'r1_fuse', 'r1_photo']);
const childBoxes: Record<string, [number, number, number, number]> = {
  r1_symbols: [830, 240, 260, 150], r1_fuse: [590, 420, 270, 160], r1_photo: [600, 570, 260, 140],
};
export function sceneHotspots(projection: SceneProjection): SceneHotspot[] {
  const { state, view } = projection;
  const expand = (hotspots: SceneHotspot[]) => hotspots.map(hotspot => {
    const [x, y, width, height] = hotspot.box; const size = projection.minHitArea || 44;
    const w = Math.max(width, size), h = Math.max(height, size);
    return { ...hotspot, box: [Math.max(0, x - (w - width) / 2), Math.max(0, y - (h - height) / 2), w, h] as [number, number, number, number] };
  });
  if (!view) return expand(state.objects.filter(object => !children.has(object.object_id) && room1Layout[object.object_id]).map(object => ({
    id: object.object_id, label: object.name, box: room1Layout[object.object_id], input: { kind: 'object', objectId: object.object_id },
  })));
  const object = state.objects.find(value => value.object_id === view);
  if (!object) return [];
  const hotspots: SceneHotspot[] = [];
  if (view === 'r1_cabinet') for (const child of state.objects.filter(value => children.has(value.object_id))) {
    hotspots.push({ id: child.object_id, label: child.name, box: childBoxes[child.object_id], input: { kind: 'object', objectId: child.object_id } });
  }
  const next = object.actions.find(action => action.tool === 'interact' || action.tool === 'take');
  if (next) hotspots.push({ id: view, label: next.label, box: view === 'r1_cabinet' ? [1120, 280, 190, 250] : [530, 320, 540, 330],
    input: { kind: 'action', tool: next.tool as 'interact' | 'take', targetId: view } });
  else if (view === 'r1_door' && state.exits.some(exit => exit.destination_id === 'R2' && exit.unlocked)) {
    hotspots.push({ id: view, label: '进入设备实验室', box: [530, 220, 540, 500], input: { kind: 'action', tool: 'move', targetId: 'R2' } });
  } else if (view === 'r1_microscope') {
    hotspots.push({ id: view, label: '查看目镜', box: [530, 240, 540, 350], input: { kind: 'action', tool: 'inspect', targetId: view } });
  }
  return expand(hotspots);
}

export default class Room1Scene extends Phaser.Scene {
  private bridge: GameBridge;
  private onReady: (renderer: string, missing: string[]) => void;
  private onAnimation: (marker: string) => void;
  private previous: SceneProjection | null = null;
  private lastReceipt: string | null = null;
  private objects = new Map<string, Phaser.GameObjects.Image>();
  private ready = false;
  constructor(bridge: GameBridge, onReady: (renderer: string, missing: string[]) => void, onAnimation: (marker: string) => void) {
    super('Room1'); this.bridge = bridge; this.onReady = onReady; this.onAnimation = onAnimation;
  }
  preload() {
    for (const [key, url] of Object.entries(room1Assets)) {
      // Vite may inline SVG using a percent-encoded data URI. Phaser's data loader expects base64.
      const comma = url.indexOf(',');
      const source = url.startsWith('data:') && !url.slice(0, comma).includes(';base64')
        ? `${url.slice(0, comma)};base64,${btoa(String.fromCharCode(...new TextEncoder().encode(decodeURIComponent(url.slice(comma + 1)))))}` : url;
      this.load.svg(key, source, { scale: 1 });
    }
  }
  create() {
    this.ready = true;
    this.onReady(this.game.renderer.type === Phaser.WEBGL ? 'webgl' : 'canvas', Object.keys(room1Assets).filter(key => !this.textures.exists(key)));
    this.sync(this.bridge.projection);
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => { this.ready = false; this.tweens.killAll(); this.objects.clear(); });
  }
  activate(input: SceneInput) { this.bridge.emit(input); }
  private image(key: string, box: [number, number, number, number], id?: string) {
    if (!this.textures.exists(key)) return null;
    const [x, y, width, height] = box;
    const image = this.add.image(x, y, key).setOrigin(0).setDisplaySize(width, height);
    if (id) { image.setAlpha(0.94); this.objects.set(id, image); }
    return image;
  }
  sync(projection: SceneProjection) {
    if (!this.ready) return;
    const old = this.previous;
    this.tweens.killAll(); this.children.removeAll(true); this.objects.clear();
    const { state, view } = projection;
    const cabinet = state.device_states?.cabinet;
    const microscope = state.puzzle_states?.microscope;
    const doorOpen = state.exits.some(exit => exit.destination_id === 'R2' && exit.unlocked);
    this.image('background', [0, 0, 1600, 900]);
    if (!view) {
      this.image('r1_workbench', room1Layout.r1_workbench || [420, 380, 760, 300]);
      for (const object of state.objects.filter(object => !children.has(object.object_id))) {
        const id = object.object_id; const box = room1Layout[id]; if (!box) continue;
        let key = id === 'r1_cabinet' ? 'r1_cabinet_locked' : id === 'r1_microscope' ? 'r1_microscope_empty' : id === 'r1_door' ? 'r1_door_closed' : id;
        if (id === 'r1_cabinet') key = cabinet === 'CODE_ACCEPTED' ? 'r1_cabinet_accepted' : cabinet === 'OPEN' ? 'r1_cabinet_open' : cabinet === 'ITEM_TAKEN' ? 'r1_cabinet_empty' : 'r1_cabinet_locked';
        if (id === 'r1_microscope' && microscope === 'SLIDE_PLACED') key = 'r1_microscope_slide';
        if (id === 'r1_door' && doorOpen) key = 'r1_door_unlatched';
        this.image(key, box, id);
      }
    } else {
      this.add.rectangle(800, 450, 1600, 900, 0x111b20, 0.88);
      let key = `closeup_${view}`;
      if (view === 'r1_cabinet') key = cabinet === 'OPEN' || cabinet === 'ITEM_TAKEN' ? 'closeup_cabinet_open' : 'closeup_cabinet_locked';
      if (view === 'r1_microscope') key = microscope === 'SLIDE_PLACED' ? 'closeup_microscope_slide' : 'closeup_microscope_empty';
      if (view === 'r1_microscope' && state.clues.some(clue => clue.object_id === view)) key = 'microscope_view';
      if (view === 'r1_clock') key = 'closeup_clock';
      if (view === 'r1_record') key = 'closeup_record';
      if (view === 'r1_plaque') key = 'closeup_plaque';
      if (view === 'r1_photo') key = 'photo_closeup';
      if (this.textures.exists(key)) this.image(key, [0, 0, 1600, 900], view);
      else this.image(view, [530, 230, 540, 400], view);
      if (view === 'r1_cabinet') for (const child of state.objects.filter(object => children.has(object.object_id))) this.image(child.object_id, childBoxes[child.object_id], child.object_id);
    }
    for (const hotspot of sceneHotspots(projection)) {
      const [x, y, width, height] = hotspot.box;
      const zone = this.add.zone(x, y, width, height).setOrigin(0).setInteractive({ useHandCursor: true });
      zone.on('pointerdown', () => this.activate(hotspot.input));
      zone.on('pointerover', () => { this.objects.get(hotspot.id)?.setAlpha(1); });
      zone.on('pointerout', () => { this.objects.get(hotspot.id)?.setAlpha(0.94); });
      if (projection.disabled) zone.disableInteractive();
    }
    const receipt = projection.animation;
    const animate = receipt && receipt.event_id !== this.lastReceipt && old && receipt.generation === state.generation
      && old.state.generation === state.generation && receipt.revision_after === state.revision && receipt.changed;
    if (receipt) this.lastReceipt = receipt.event_id;
    if (animate && ['take', 'use_item', 'interact', 'submit_code'].includes(receipt.tool) && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const target = String(receipt.arguments.target_id || receipt.arguments.item_id || '');
      const image = this.objects.get(target) || (view ? this.objects.get(view) : undefined);
      this.onAnimation(receipt.tool);
      if (receipt.tool === 'take') {
        const objectId = target === 'fuse' ? 'r1_fuse' : target;
        const start: [number, number, number, number] = old.view ? [650, 350, 240, 160] : room1Layout[objectId];
        const ghost = start ? this.image(objectId, start) : null;
        if (ghost) this.tweens.add({ targets: ghost, x: 780, y: 870, scaleX: ghost.scaleX * 0.15, scaleY: ghost.scaleY * 0.15, alpha: 0, duration: 340, onComplete: () => { ghost.destroy(); this.onAnimation('idle'); } });
        else this.time.delayedCall(340, () => this.onAnimation('idle'));
      } else if (receipt.tool === 'interact' && target === 'r1_cabinet' && state.device_states?.cabinet === 'OPEN' && view === target) {
        const left = this.add.rectangle(335, 170, 390, 485, 0x79847a).setOrigin(0).setStrokeStyle(5, 0x3e4a44);
        const right = this.add.rectangle(1115, 170, 390, 485, 0x79847a).setOrigin(1, 0).setStrokeStyle(5, 0x3e4a44);
        this.tweens.add({ targets: [left, right], scaleX: 0.08, alpha: 0, duration: 420, ease: 'Sine.easeOut', onComplete: () => { left.destroy(); right.destroy(); this.onAnimation('idle'); } });
      } else if (receipt.tool === 'use_item' && target === 'r1_microscope') {
        const ghost = this.image('sample_slide', [740, 820, 180, 90]);
        if (ghost) this.tweens.add({ targets: ghost, x: 750, y: 470, scaleX: ghost.scaleX * 0.65, scaleY: ghost.scaleY * 0.65, alpha: 0, duration: 320, ease: 'Sine.easeOut', onComplete: () => { ghost.destroy(); this.onAnimation('idle'); } });
        else this.time.delayedCall(320, () => this.onAnimation('idle'));
      } else if (image) {
        const alpha = image.alpha; image.setAlpha(0.65);
        const x = image.x; if (receipt.tool === 'interact') image.x -= 18;
        this.tweens.add({ targets: image, alpha, x, duration: receipt.tool === 'interact' ? 400 : 280, onComplete: () => this.onAnimation('idle') });
      } else this.time.delayedCall(280, () => this.onAnimation('idle'));
    } else this.onAnimation('idle');
    this.previous = projection;
  }
}
