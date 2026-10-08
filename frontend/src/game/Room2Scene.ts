import Phaser from 'phaser';
import { room2Assets, room2Layout } from '../assets/manifest';
import { GameBridge, type SceneInput, type SceneProjection } from './bridge';
import type { CircuitPuzzle } from '../api';

export interface Room2Hotspot {
  id: string; label: string; box: [number, number, number, number]; input: SceneInput;
  moduleId?: string; rotation?: number; disabled?: boolean;
}
const powerSuffix = { CLOSED: 'closed', OPEN: 'open', MISSING_FUSE: 'missing_fuse', FUSE_INSTALLED: 'fuse_installed', CIRCUIT_READY: 'circuit_ready', POWER_ON: 'power_on' };
const monitorSuffix = { OFF: 'off', BOOTING: 'booting', LOGIN_LOCKED: 'login_locked', UNLOCKED: 'unlocked', DATA_READ: 'data_read' };
const trayIds = new Set(['research_strip', 'access_card']);
const childBoxes: Record<string, [number, number, number, number]> = {
  research_strip: [545, 635, 250, 95], access_card: [860, 625, 175, 105], r2_service_label: [135, 230, 180, 250],
};
const objectTexture: Record<string, string> = { research_strip: 'r2_research_strip', access_card: 'r2_access_card' };
const moduleBox = (row: number, column: number): [number, number, number, number] => [520 + column * 200, 200 + row * 180, 200, 180];
export function room2Hotspots(projection: SceneProjection): Room2Hotspot[] {
  const { state, view } = projection;
  const expand = (hotspots: Room2Hotspot[]) => hotspots.map(hotspot => {
    const [x, y, width, height] = hotspot.box, size = projection.minHitArea || 44;
    const w = Math.max(width, size), h = Math.max(height, size);
    return { ...hotspot, box: [Math.max(0, x - (w - width) / 2), Math.max(0, y - (h - height) / 2), w, h] as [number, number, number, number] };
  });
  if (!view) {
    const hotspots: Room2Hotspot[] = state.objects.filter(object => room2Layout[object.object_id]).map(object => ({
      id: object.object_id, label: object.name, box: room2Layout[object.object_id], input: { kind: 'object', objectId: object.object_id },
    }));
    if (state.exits.some(exit => exit.destination_id === 'R1' && exit.unlocked)) hotspots.push({ id: 'return_R1', label: '返回实验准备室', box: room2Layout.r2_return_door, input: { kind: 'action', tool: 'move', targetId: 'R1' } });
    return expand(hotspots);
  }
  const object = state.objects.find(value => value.object_id === view);
  if (!object) return [];
  const hotspots: Room2Hotspot[] = [];
  if (view === 'r2_monitor') for (const child of state.objects.filter(value => trayIds.has(value.object_id))) {
    hotspots.push({ id: child.object_id, label: child.name, box: childBoxes[child.object_id], input: { kind: 'object', objectId: child.object_id } });
  }
  if (view === 'r2_powerbox') {
    const label = state.objects.find(value => value.object_id === 'r2_service_label');
    if (label) hotspots.push({ id: label.object_id, label: label.name, box: childBoxes.r2_service_label, input: { kind: 'object', objectId: label.object_id } });
    const circuit = state.minigames?.circuit;
    if (circuit) for (const module of circuit.modules) hotspots.push({ id: module.module_id, label: `旋转线路模块 ${module.module_id} 顺时针90度`, box: moduleBox(module.row, module.column),
      input: { kind: 'circuit-module', targetId: circuit.target_id, moduleId: module.module_id }, moduleId: module.module_id, rotation: module.rotation, disabled: circuit.status === 'completed' });
    else if (state.device_states?.powerbox === 'MISSING_FUSE') hotspots.push({ id: view, label: '保险丝触点', box: [540, 320, 500, 280], input: { kind: 'action', tool: 'inspect', targetId: view } });
  }
  const next = object.actions.find(action => action.tool === 'interact' || action.tool === 'take');
  if (next) hotspots.push({ id: view, label: next.label, box: view === 'r2_powerbox' ? [1200, 280, 150, 320] : view === 'r2_monitor' ? [420, 160, 760, 430] : [530, 250, 540, 400], input: { kind: 'action', tool: next.tool as 'interact' | 'take', targetId: view } });
  else if (view === 'r2_door' && state.exits.some(exit => exit.destination_id === 'R3' && exit.unlocked)) hotspots.push({ id: view, label: '进入出口控制室', box: [580, 120, 400, 650], input: { kind: 'action', tool: 'move', targetId: 'R3' } });
  return expand(hotspots);
}

export default class Room2Scene extends Phaser.Scene {
  private previous: SceneProjection | null = null;
  private lastReceipt: string | null = null;
  private objects = new Map<string, Phaser.GameObjects.Image>();
  private modules = new Map<string, Phaser.GameObjects.Graphics>();
  private ready = false;
  constructor(private bridge: GameBridge, private onReady: (renderer: string, missing: string[]) => void, private onAnimation: (marker: string) => void) { super('Room2'); }
  preload() {
    for (const [key, url] of Object.entries(room2Assets)) {
      const comma = url.indexOf(',');
      const source = url.startsWith('data:') && !url.slice(0, comma).includes(';base64')
        ? `${url.slice(0, comma)};base64,${btoa(String.fromCharCode(...new TextEncoder().encode(decodeURIComponent(url.slice(comma + 1)))))}` : url;
      this.load.svg(key, source, { scale: 1 });
    }
  }
  create() {
    this.ready = true;
    this.onReady(this.game.renderer.type === Phaser.WEBGL ? 'webgl' : 'canvas', Object.keys(room2Assets).filter(key => !this.textures.exists(key)));
    this.sync(this.bridge.projection);
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => { this.ready = false; this.tweens.killAll(); this.objects.clear(); this.modules.clear(); });
  }
  activate(input: SceneInput) { this.bridge.emit(input); }
  private image(key: string, box: [number, number, number, number], id?: string) {
    if (!this.textures.exists(key)) return null;
    const [x, y, width, height] = box;
    const image = this.add.image(x, y, key).setOrigin(0).setDisplaySize(width, height);
    if (id) { image.setAlpha(0.94); this.objects.set(id, image); }
    return image;
  }
  private text(x: number, y: number, content: string, size = 26, color = '#b2c5ac') {
    return this.add.text(x, y, content, { fontFamily: 'Consolas, Microsoft YaHei, monospace', fontSize: `${size}px`, color, lineSpacing: 15 });
  }
  private circuit(board: CircuitPuzzle) {
    for (const module of board.modules) {
      const [x, y, width, height] = moduleBox(module.row, module.column), cx = x + width / 2, cy = y + height / 2;
      this.add.rectangle(cx, cy, width - 16, height - 16, 0x263b3b).setStrokeStyle(3, board.status === 'completed' ? 0x819b7c : 0x627b78);
      const wire = this.add.graphics({ x: cx, y: cy });
      wire.lineStyle(13, board.status === 'completed' ? 0x98b187 : 0xc5c49b, 1);
      wire.beginPath(); wire.moveTo(0, -62); wire.lineTo(0, 0); wire.lineTo(module.shape === 'I' ? 0 : 70, module.shape === 'I' ? 62 : 0); wire.strokePath();
      wire.fillStyle(0xcfc9a0, 1); wire.fillCircle(0, -62, 8); wire.fillCircle(module.shape === 'I' ? 0 : 70, module.shape === 'I' ? 62 : 0, 8);
      wire.setRotation(module.rotation * Math.PI / 2); this.modules.set(module.module_id, wire);
      this.text(x + 14, y + 11, module.module_id, 16, '#91a9a6');
    }
    for (const [terminal, label] of [[board.source, '电源端'], [board.sink, '主系统']] as const) {
      const module = board.modules.find(value => value.module_id === terminal.module_id); if (!module) continue;
      const [x, y, w, h] = moduleBox(module.row, module.column);
      const offset: Record<string, [number, number]> = { N: [w / 2, -12], E: [w + 10, h / 2], S: [w / 2, h + 10], W: [-12, h / 2] };
      const [dx, dy] = offset[terminal.side]; this.add.circle(x + dx, y + dy, 10, 0xcfbd80);
      this.text(terminal === board.source ? 330 : 1140, terminal === board.source ? 165 : 680, `${label} ${terminal.side}`, 22, '#d2c595');
    }
  }
  sync(projection: SceneProjection) {
    if (!this.ready) return;
    const old = this.previous;
    this.tweens.killAll(); this.children.removeAll(true); this.objects.clear(); this.modules.clear();
    const { state, view } = projection;
    const powered = state.progress.power_on;
    const power = state.device_states?.powerbox || 'CLOSED', computer = state.device_states?.computer || 'OFF';
    const doorOpen = state.exits.some(exit => exit.destination_id === 'R3' && exit.unlocked);
    this.image('r2_background_dark', [0, 0, 1600, 900]);
    if (powered) this.image('r2_light_overlay_on', [0, 0, 1600, 900]);
    if (!view) {
      this.image('r2_workbench', room2Layout.r2_workbench);
      this.image('r2_return_door', room2Layout.r2_return_door);
      if (computer === 'DATA_READ') this.image('r2_tray', room2Layout.r2_tray);
      for (const object of state.objects) {
        const id = object.object_id, box = room2Layout[id]; if (!box) continue;
        const key = id === 'r2_powerbox' ? `r2_powerbox_${powerSuffix[power]}` : id === 'r2_monitor' ? `r2_monitor_${monitorSuffix[computer]}` : id === 'r2_door' ? `r2_door_${doorOpen ? 'unlatched' : 'closed'}` : objectTexture[id] || id;
        this.image(key, box, id);
      }
    } else {
      this.add.rectangle(800, 450, 1600, 900, 0x0d171d, 0.87);
      const key = view === 'r2_powerbox' ? `r2_closeup_powerbox_${powerSuffix[power]}` : view === 'r2_monitor' ? `r2_closeup_monitor_${monitorSuffix[computer]}` : `r2_closeup_${view.replace(/^r2_/, '')}`;
      if (this.textures.exists(key)) this.image(key, [0, 0, 1600, 900], view);
      else this.image(view === 'r2_door' ? `r2_door_${doorOpen ? 'unlatched' : 'closed'}` : objectTexture[view] || view, view === 'r2_door' ? [580, 120, 400, 650] : [520, 230, 560, 360], view);
      if (view === 'r2_powerbox') {
        if (state.minigames?.circuit) this.circuit(state.minigames.circuit);
        if (state.objects.some(object => object.object_id === 'r2_service_label')) this.image('r2_service_label', [135, 300, 180, 96], 'r2_service_label');
      }
      if (view === 'r2_monitor') {
        const content = { OFF: '', BOOTING: 'LAB SYSTEM\n\nBOOT...', LOGIN_LOCKED: '', UNLOCKED: 'AUTH OK\n\nARCHIVED RESEARCH RECORD\n\n[ OPEN ]', DATA_READ: 'ARCHIVE OPEN\n\nRESEARCH RECORD AVAILABLE' }[computer];
        if (content) this.text(465, 220, content, 31);
        if (computer === 'DATA_READ') this.image('r2_tray', [475, 600, 610, 155]);
        for (const child of state.objects.filter(object => trayIds.has(object.object_id))) this.image(objectTexture[child.object_id], childBoxes[child.object_id], child.object_id);
      }
    }
    for (const hotspot of room2Hotspots(projection)) {
      const [x, y, width, height] = hotspot.box;
      const zone = this.add.zone(x, y, width, height).setOrigin(0).setInteractive({ useHandCursor: true });
      zone.on('pointerdown', () => this.activate(hotspot.input));
      zone.on('pointerover', () => this.objects.get(hotspot.id)?.setAlpha(1));
      zone.on('pointerout', () => this.objects.get(hotspot.id)?.setAlpha(0.94));
      if (projection.disabled || hotspot.disabled) zone.disableInteractive();
    }
    const receipt = projection.animation;
    const animate = receipt && receipt.event_id !== this.lastReceipt && old && receipt.generation === state.generation && old.state.generation === state.generation && receipt.revision_after === state.revision && receipt.changed;
    if (receipt) this.lastReceipt = receipt.event_id;
    if (animate && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const target = String(receipt.arguments.target_id || receipt.arguments.item_id || '');
      this.onAnimation(receipt.tool);
      if (receipt.tool === 'rotate_circuit') {
        const moduleId = String(receipt.arguments.module_id), wire = this.modules.get(moduleId), previous = old.state.minigames?.circuit?.modules.find(module => module.module_id === moduleId);
        if (wire && previous) { wire.setRotation(previous.rotation * Math.PI / 2); this.tweens.add({ targets: wire, rotation: (previous.rotation + 1) * Math.PI / 2, duration: 180, onComplete: () => this.onAnimation('idle') }); }
        else this.time.delayedCall(180, () => this.onAnimation('idle'));
      } else if (receipt.tool === 'interact' && target === 'r2_powerbox' && powered) {
        const shade = this.add.rectangle(800, 450, 1600, 900, 0x101e2b, 0.6);
        this.tweens.add({ targets: shade, alpha: 0, duration: 650, ease: 'Sine.easeOut', onComplete: () => { shade.destroy(); this.onAnimation('idle'); } });
      } else if (receipt.tool === 'take') {
        const box: [number, number, number, number] = old.view === target ? [520, 230, 560, 360] : old.view ? childBoxes[target] || [600, 330, 300, 180] : room2Layout[target];
        const ghost = box ? this.image(objectTexture[target] || target, box) : null;
        if (ghost) this.tweens.add({ targets: ghost, x: 800, y: 880, scaleX: ghost.scaleX * 0.15, scaleY: ghost.scaleY * 0.15, alpha: 0, duration: 340, onComplete: () => { ghost.destroy(); this.onAnimation('idle'); } });
        else this.time.delayedCall(340, () => this.onAnimation('idle'));
      } else if (receipt.tool === 'use_item' && target === 'r2_powerbox') {
        const ghost = this.add.rectangle(800, 770, 210, 40, 0xc9d3c5).setStrokeStyle(8, 0x74837e);
        this.tweens.add({ targets: ghost, y: 405, scaleX: 0.5, scaleY: 0.5, alpha: 0, duration: 350, onComplete: () => { ghost.destroy(); this.onAnimation('idle'); } });
      } else {
        const image = this.objects.get(target) || (view ? this.objects.get(view) : undefined);
        if (image && ['interact', 'submit_login', 'submit_circuit'].includes(receipt.tool)) { const alpha = image.alpha; image.setAlpha(0.65); this.tweens.add({ targets: image, alpha, duration: receipt.tool === 'interact' && target === 'r2_monitor' ? 600 : 350, onComplete: () => this.onAnimation('idle') }); }
        else this.onAnimation('idle');
      }
    } else this.onAnimation('idle');
    this.previous = projection;
  }
}
