import Phaser from 'phaser';
import { paintedImage, paintedText, knownClue, beginPaintFrame } from './painted';
import { room3Assets, room3Layout } from '../assets/manifest';
import { GameBridge, sameSceneInput, type SceneInput, type SceneProjection } from './bridge';
import type { Room2Hotspot } from './Room2Scene';

const exitSuffix = { LOCKED: 'locked', CARD_ACCEPTED: 'card_accepted', FINAL_CHECK: 'final_check', UNLOCKED: 'unlocked', OPEN: 'open' };
// Enlarge the painted operation plate with its buttons, instead of overlapping transparent hit areas.
const panelZoom = (projection: SceneProjection) => Math.max(1, Math.ceil(projection.minHitArea || 44) / 130);
function panelBox(projection: SceneProjection, box: [number, number, number, number]): [number, number, number, number] {
  const zoom = panelZoom(projection), x = zoom > 1 ? 260 : 590;
  return [x + (box[0] - 590) * zoom, 445 + (box[1] - 445) * zoom, box[2] * zoom, box[3] * zoom];
}
const buttonBox = (projection: SceneProjection, index: number): [number, number, number, number] => panelBox(projection, [590 + (index % 2) * 235, 445 + Math.floor(index / 2) * 130, 230, 130]);
function panelSuffix(projection: SceneProjection) {
  if (projection.state.progress.check_done) return 'passed';
  if (projection.state.device_states?.exit === 'FINAL_CHECK') return 'final_check';
  return projection.state.puzzle_states?.panel === 'STRIP_INSERTED' ? 'strip_inserted' : 'empty';
}
export function room3Hotspots(projection: SceneProjection): Room2Hotspot[] {
  const { state, view } = projection;
  let spots: Room2Hotspot[] = [];
  if (!view) {
    spots = state.objects.filter(object => room3Layout[object.object_id]).map(object => ({ id: object.object_id, label: object.name, box: room3Layout[object.object_id], input: { kind: 'object', objectId: object.object_id } }));
    if (state.exits.some(exit => exit.destination_id === 'R2' && exit.unlocked)) spots.push({ id: 'return_R2', label: '返回设备实验室', box: room3Layout.r3_return_door, input: { kind: 'action', tool: 'move', targetId: 'R2' } });
  } else {
    const object = state.objects.find(object => object.object_id === view);
    if (!object) return [];
    if (view === 'r3_panel') {
      const sequence = state.minigames?.sequence;
      if (sequence) sequence.devices.forEach((device, index) => spots.push({ id: device.device_id, label: `将${device.label}（${device.symbol}）加入当前顺序草稿`, box: buttonBox(projection, index), input: { kind: 'sequence-device', targetId: sequence.target_id, deviceId: device.device_id }, disabled: sequence.status === 'completed' || (projection.sequenceDraft?.length || 0) >= sequence.length }));
      else spots.push({ id: view, label: '终检窄纸槽', box: panelBox(projection, [645, 285, 445, 65]), input: { kind: 'action', tool: 'inspect', targetId: view } });
    }
    if (view === 'exit_door') {
      const next = object.actions.find(action => action.tool === 'interact');
      if (next) spots.push({ id: view, label: next.label, box: [795, 110, 390, 625], input: { kind: 'action', tool: 'interact', targetId: view } });
      else if (state.exits.some(exit => exit.destination_id === 'EXIT' && exit.unlocked)) spots.push({ id: view, label: '走出实验室', box: [795, 110, 390, 625], input: { kind: 'action', tool: 'move', targetId: 'EXIT' } });
      else spots.push({ id: view, label: '出口读卡器', box: [1135, 310, 130, 160], input: { kind: 'action', tool: 'inspect', targetId: view } });
    }
  }
  return spots.map(spot => {
    const [x, y, width, height] = spot.box, minimum = projection.minHitArea || 44, w = Math.max(width, minimum), h = Math.max(height, minimum);
    return { ...spot, box: [Math.max(0, Math.min(1600 - w, x - (w - width) / 2)), Math.max(0, Math.min(900 - h, y - (h - height) / 2)), w, h] as [number, number, number, number] };
  });
}
export default class Room3Scene extends Phaser.Scene {
  private ready = false;
  private previous: SceneProjection | null = null;
  private lastReceipt: string | null = null;
  private opening = false;
  private lamps = new Map<string, Phaser.GameObjects.Arc>();
  constructor(private bridge: GameBridge, private onReady: (renderer: string, missing: string[]) => void, private onAnimation: (marker: string) => void) { super('Room3'); }
  preload() {
    for (const [key, url] of Object.entries(room3Assets)) this.load.image(key, url);
  }
  create() {
    this.ready = true;
    this.onReady(this.game.renderer.type === Phaser.WEBGL ? 'webgl' : 'canvas', Object.keys(room3Assets).filter(key => !this.textures.exists(key)));
    this.sync(this.bridge.projection);
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => { this.ready = false; this.tweens.killAll(); this.time.removeAllEvents(); this.lamps.clear(); });
  }
  activate(input: SceneInput) { if (!this.opening && room3Hotspots(this.bridge.projection).some(spot => !spot.disabled && sameSceneInput(spot.input, input))) this.bridge.emit(input); }
  private image(key: string, box: [number, number, number, number]) {
    if (!this.textures.exists(key)) return null;
    return paintedImage(this, key, box);
  }
  private text(x: number, y: number, content: string, size = 30, color = '#c9d5bb') {
    return this.add.text(x, y, content, { fontFamily: 'Consolas, Microsoft YaHei, monospace', fontSize: `${size}px`, color, lineSpacing: 14 });
  }
  sync(projection: SceneProjection) {
    if (!this.ready) return;
    this.input.enabled = !projection.disabled;
    const old = this.previous;
    if (old && old.state === projection.state && old.view === projection.view && old.sequenceDraft === projection.sequenceDraft && old.reducedMotion === projection.reducedMotion && old.minHitArea === projection.minHitArea) { this.previous = projection; return; }
    this.opening = false; this.tweens.killAll(); this.time.removeAllEvents(); for (const child of [...this.children.list]) child.destroy(); beginPaintFrame(this); this.lamps.clear(); this.onAnimation('idle');
    const { state, view } = projection, exit = state.device_states?.exit || 'LOCKED', panel = panelSuffix(projection);
    this.image(state.progress.power_on ? 'r3_background' : 'r3_background_off', [0, 0, 1600, 900]);
    if (!view) {
      this.image('r3_return_door', room3Layout.r3_return_door);
      for (const object of state.objects) {
        const key = object.object_id === 'r3_panel' ? `r3_panel_${panel}` : object.object_id === 'exit_door' ? `r3_exit_door_${exitSuffix[exit]}` : object.object_id;
        this.image(key, room3Layout[object.object_id]);
      }
    } else {
      this.add.rectangle(800, 450, 1600, 900, 0x101b20, .8);
      this.image(view === 'r3_panel' ? `r3_closeup_panel_${panel}` : view === 'exit_door' ? `r3_closeup_exit_door_${exitSuffix[exit]}` : 'r3_closeup_legend', view === 'r3_panel' ? panelBox(projection, [-330, -185, 2400, 1350]) : [0, 0, 1600, 900]);
      const sequence = view === 'r3_panel' ? state.minigames?.sequence : null;
      if (sequence) {
        sequence.devices.forEach((device, index) => {
          const [x, y, w, h] = buttonBox(projection, index);
          this.add.rectangle(x + w / 2, y + h / 2, w - 8, h - 8, 0x344440).setStrokeStyle(2, sequence.status === 'completed' ? 0x98ae87 : 0x87917a);
          const zoom = panelZoom(projection); this.text(x + 25 * zoom, y + 48 * zoom, `${device.symbol} ${device.label}`, 36 * zoom);
          this.lamps.set(device.device_id, this.add.circle(x + w - 25 * zoom, y + 25 * zoom, 9 * zoom, sequence.status === 'completed' ? 0xb4c78d : 0x4f675c));
        });
        const zoom = panelZoom(projection);
        // The compact camera focuses on the operation plate; its paper slot carries the same local draft.
        const draftY = zoom > 1 ? 307 : 108;
        for (let index = 0; index < sequence.length; index++) {
          const id = projection.sequenceDraft?.[index], device = sequence.devices.find(device => device.device_id === id);
          const [x, y, w, h] = panelBox(projection, [684 + index * 93, draftY - 16, 86, 38]);
          this.add.rectangle(x + w / 2, y + h / 2, w, h, zoom > 1 ? 0xd7c5a1 : 0x14262a);
          this.text(x + 6 * zoom, y + 4 * zoom, sequence.status === 'completed' ? '✓' : device ? `${index + 1} ${device.symbol}` : `${index + 1} ·`, 23 * zoom, zoom > 1 ? '#433d2c' : '#c9d5bb');
        }
        if (zoom === 1) this.text(715, 140, sequence.status === 'completed' ? '终检通过' : '设备顺序', 20);
      } else if (view === 'r3_panel' && panelZoom(projection) === 1) this.text(715, 108, state.puzzle_states?.panel === 'STRIP_INSERTED' ? '窄纸已固定' : '状态灯熄灭', 25);
      if (view === 'exit_door') this.text(1095, 200, { LOCKED: '读卡器待机', CARD_ACCEPTED: '门禁已接受\n状态灯待机', FINAL_CHECK: state.progress.check_done ? '终检已通过' : '等待终检', UNLOCKED: '门锁已解除', OPEN: '通道已打开' }[exit], 25);
    }
    const clue = view ? knownClue(state, view) : null;
    if (clue && view === 'r3_legend') {
      const rows = clue.text.split('。')[0].split('；');
      rows.forEach((row, index) => paintedText(this, [505, 218 + index * 159, 605, 100], row, 44));
    }
    for (const spot of room3Hotspots(projection)) {
      const [x, y, w, h] = spot.box;
      const zone = this.add.zone(x, y, w, h).setOrigin(0).setInteractive({ useHandCursor: true }); zone.on('pointerdown', () => this.activate(spot.input));
      if (spot.disabled) zone.disableInteractive();
    }
    const receipt = projection.animation;
    const animate = receipt && receipt.event_id !== this.lastReceipt && old && receipt.generation === state.generation && old.state.generation === state.generation && receipt.revision_after === state.revision && receipt.changed && !projection.reducedMotion;
    if (receipt) this.lastReceipt = receipt.event_id;
    if (animate) {
      const target = String(receipt.arguments.target_id || '');
      if (receipt.tool === 'interact' && target === 'exit_door' && exit === 'OPEN') {
        this.opening = true; this.onAnimation('door_open');
        const door = this.image(view === 'exit_door' ? 'r3_closeup_exit_door_unlocked' : 'r3_exit_door_unlocked', view === 'exit_door' ? [0, 0, 1600, 900] : room3Layout.exit_door);
        if (door && view === 'exit_door') door.setCrop(790, 80, 470, 770);
        if (door) this.tweens.add({ targets: door, x: door.x + 90, alpha: 0, duration: 1000, ease: 'Sine.easeInOut', onComplete: () => { this.opening = false; door.destroy(); this.onAnimation('idle'); } });
        else this.time.delayedCall(1000, () => { this.opening = false; this.onAnimation('idle'); });
      } else if (receipt.tool === 'submit_sequence' && view === 'r3_panel') {
        this.onAnimation('submit_sequence');
        const ids = Array.isArray(receipt.arguments.device_ids) ? receipt.arguments.device_ids : [];
        for (const lamp of this.lamps.values()) lamp.setFillStyle(0x4f675c);
        ids.forEach((id, index) => this.time.delayedCall(index * 160, () => this.lamps.get(id)?.setFillStyle(0xb4c78d)));
        this.time.delayedCall(700, () => this.onAnimation('idle'));
      } else if (receipt.tool === 'use_item' && target === 'r3_panel') {
        this.onAnimation('use_item');
        const strip = this.add.rectangle(800, 810, 420, 45, 0xd8cfb4).setStrokeStyle(2, 0x8b9379);
        this.tweens.add({ targets: strip, y: 320, scaleY: .1, alpha: 0, duration: 380, onComplete: () => { strip.destroy(); this.onAnimation('idle'); } });
      } else if (target === 'exit_door') {
        this.onAnimation(receipt.tool);
        const glow = this.add.rectangle(view ? 1175 : 1400, view ? 370 : 450, 80, 45, 0xc9d6a4, .7);
        this.tweens.add({ targets: glow, alpha: 0, duration: 300, onComplete: () => { glow.destroy(); this.onAnimation('idle'); } });
      }
    }
    this.previous = projection;
  }
}
