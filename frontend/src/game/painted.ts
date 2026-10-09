import Phaser from 'phaser';
import { paintedAssets, type RoomBox } from '../assets/manifest';
import type { VisibleState } from '../api';

type Metadata = { width: number; height: number; bbox: { x: number; y: number; width: number; height: number } };
const metadata = paintedAssets as Record<string, Metadata>;
const sourceKey = (key: string) => key === 'background' ? 'r1_background' : key;
/** Crop once in source pixels; scaling the cropped frame preserves object proportions and shadows. */
export function paintedImage(scene: Phaser.Scene, key: string, box: RoomBox) {
  if (!scene.textures.exists(key)) return null;
  const asset = metadata[sourceKey(key)];
  if (!asset) return null;
  const texture = scene.textures.get(key), frame = '__painted_visible';
  const { x, y, width, height } = asset.bbox;
  if (!texture.has(frame)) texture.add(frame, 0, x, y, width, height);
  const scale = Math.min(box[2] / width, box[3] / height);
  const image = scene.add.image(box[0] + (box[2] - width * scale) / 2, box[1] + (box[3] - height * scale) / 2, key, frame)
    .setOrigin(0).setScale(scale);
  const canvas = scene.game.canvas;
  const frames = JSON.parse(canvas.dataset.paintedFrames || '[]') as object[];
  frames.push({ key, box: [image.x, image.y, width * scale, height * scale], source: [x, y, width, height] });
  canvas.dataset.paintedFrames = JSON.stringify(frames);
  return image;
}
export function paintedText(scene: Phaser.Scene, box: RoomBox, text: string, size = 30, color = '#443d2c', align: 'left' | 'center' = 'left') {
  return scene.add.text(box[0], box[1], text, { fontFamily: 'Microsoft YaHei, Consolas, sans-serif', fontSize: `${size}px`, color,
    wordWrap: { width: box[2], useAdvancedWrap: true }, lineSpacing: size * .25, align }).setFixedSize(box[2], box[3]);
}
export function knownClue(state: VisibleState, objectId: string) { return state.clues.find(clue => clue.object_id === objectId); }
/** Generated hands are decorative; a clean dial is the sole accurate time display. */
export function clockFace(scene: Phaser.Scene, box: RoomBox) {
  const cx = box[0] + box[2] / 2, cy = box[1] + box[3] / 2, r = Math.min(box[2], box[3]) / 2;
  // Reuse an unmarked patch of the original painted dial, with uniform scale and a circular mask.
  // No PNG is altered and no generated needle or lettering remains as puzzle authority.
  const texture = scene.textures.get('closeup_clock'), paperFrame = '__clock_paper';
  if (!texture.has(paperFrame)) texture.add(paperFrame, 0, 730, 250, 190, 80);
  const maskShape = scene.add.graphics().setVisible(false); maskShape.fillStyle(0xffffff).fillCircle(cx, cy, r);
  const mask = maskShape.createGeometryMask(), scale = r * 2 / 190, stripHeight = 80 * scale;
  for (let y = cy - r; y < cy + r; y += stripHeight) scene.add.image(cx - r, y, 'closeup_clock', paperFrame).setOrigin(0).setScale(scale).setMask(mask);
  const g = scene.add.graphics(); g.lineStyle(Math.max(2, r / 60), 0x514737, .85);
  for (let index = 0; index < 12; index++) { const a = index * Math.PI / 6; g.lineBetween(cx + Math.sin(a) * r * .82, cy - Math.cos(a) * r * .82, cx + Math.sin(a) * r * .92, cy - Math.cos(a) * r * .92); }
  for (const [angle, length, width] of [[102, .73, .025], [278.5, .47, .04]]) { const a = angle * Math.PI / 180; g.lineStyle(Math.max(2, r * width), 0x393a31, 1); g.lineBetween(cx, cy, cx + Math.sin(a) * r * length, cy - Math.cos(a) * r * length); }
  g.fillStyle(0x393a31, 1); g.fillCircle(cx, cy, r * .04);
}
/** Keep generated symbols covered until the canonical clue has actually been inspected. */
export function symbolLabel(scene: Phaser.Scene, box: RoomBox, state: VisibleState) {
  paintedImage(scene, 'r1_symbols', box);
  scene.add.rectangle(box[0] + box[2] / 2, box[1] + box[3] / 2, box[2] * .94, box[3] * .75, 0xd7c5a1);
  const clue = knownClue(state, 'r1_symbols');
  if (clue) paintedText(scene, [box[0] + 8, box[1] + box[3] * .2, box[2] - 16, box[3] * .65], clue.text.match(/[▲●■★]/g)?.join('  ') || '', Math.min(42, box[3] * .46), '#463e2d', 'center');
}

export function beginPaintFrame(scene: Phaser.Scene) { scene.game.canvas.dataset.paintedFrames = '[]'; }
