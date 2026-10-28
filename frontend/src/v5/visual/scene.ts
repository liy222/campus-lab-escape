import catalog from '../../assets/generated-catalog.json';
import { noteVariantFor, packBackground, themePackFor, variantFor } from './registry';
import type { SceneModel, SceneObject } from './types';

/** Legacy eight-slot grid, kept only for levels without a supported theme pack. */
const legacyPositions = [[210, 290], [600, 290], [1000, 290], [1390, 290], [210, 635], [600, 635], [1000, 635], [1390, 635]];

export type SceneObjectInput = {
  object_id: string;
  name: string;
  kind: string;
  art_id: string;
  slot: number;
  completed?: boolean;
};

export type SceneInput = {
  level_id: string;
  theme?: string | null;
  room: { name: string; background_id?: string | null; background_art_id?: string | null };
  objects: SceneObjectInput[];
};

type LegacyAsset = { id: string; url: string; width: number; height: number; bbox: { x: number; y: number; width: number; height: number } };

const legacyAssets = catalog.assets as LegacyAsset[];

/** The legacy catalogue painted the key as an old fuse; use the neutral brass key instead. */
const neutralKey = {
  id: 'key',
  url: '/art-themes/rainy-astronomy/objects/key-brass.png',
  width: 640,
  height: 512,
  bbox: { x: 112, y: 96, width: 430, height: 300 },
};

function legacyObject(object: SceneObjectInput, index: number, slotIndex: number): SceneObject {
  const asset = object.art_id === 'key'
    ? neutralKey
    : legacyAssets.find(candidate => candidate.id === object.art_id) ?? legacyAssets.find(candidate => candidate.id === 'note')!;
  const [x, y] = legacyPositions[Math.max(0, Math.min(7, slotIndex))] ?? legacyPositions[0];
  const scale = Math.min(310 / asset.bbox.width, 245 / asset.bbox.height);
  const width = asset.bbox.width * scale;
  return {
    object_id: object.object_id,
    name: object.name,
    completed: Boolean(object.completed),
    kind: object.kind,
    key: `legacy:${asset.id}:${index}`,
    src: asset.url,
    bbox: asset.bbox,
    x,
    y: y + 27,
    renderHeight: asset.bbox.height * scale,
    hotspot: { x: x - width / 2, y: y + 27 - asset.bbox.height * scale, width, height: asset.bbox.height * scale + 24 },
    closeup: null,
    closeupBox: null,
    variantId: null,
  };
}

export function buildSceneModel(input: SceneInput): SceneModel {
  const pack = themePackFor(input.theme);
  const objects = input.objects.map((object, index) => ({ object, index }));
  if (!pack) {
    const backgroundId = input.room.background_art_id || input.room.background_id || 'neutral_lab';
    const asset = legacyAssets.find(candidate => candidate.id === backgroundId) ?? legacyAssets.find(candidate => candidate.id === 'neutral_lab')!;
    return {
      themeId: null,
      themeName: null,
      background: { key: 'legacy:background', src: asset.url },
      objects: objects.map(({ object, index }) => legacyObject(object, index, object.slot)),
      extras: [],
    };
  }
  const { background, slots } = packBackground(pack, input.room.background_id || input.room.background_art_id);
  const themed: SceneObject[] = [];
  const extras: { key: string; src: string }[] = [];
  objects.forEach(({ object, index }) => {
    const slotIndex = Math.max(0, Math.min(slots.length - 1, Number.isFinite(object.slot) ? object.slot : 0));
    const slot = slots[slotIndex];
    const resolved = object.art_id === 'note'
      ? noteVariantFor(pack, object.name, `${input.level_id}:${object.object_id}`)
      : variantFor(pack, object.art_id, `${input.level_id}:${object.object_id}`, Boolean(object.completed));
    if (!resolved || !slot) {
      themed.push(legacyObject(object, index, slotIndex));
      return;
    }
    const { id, variant } = resolved;
    const fitHeight = slot.height / variant.bbox.height;
    const fitWidth = (slot.hotspot.width * 1.02) / variant.bbox.width;
    const scale = Math.min(fitHeight, fitWidth);
    themed.push({
      object_id: object.object_id,
      name: object.name,
      completed: Boolean(object.completed),
      kind: object.kind,
      key: `theme:${id}`,
      src: variant.src,
      bbox: variant.bbox,
      x: slot.x,
      y: slot.y,
      renderHeight: variant.bbox.height * scale,
      hotspot: slot.hotspot,
      closeup: variant.closeup,
      closeupBox: variant.closeup_bbox,
      variantId: id,
    });
  });
  // Preload the other state of every role present, so completion swaps art on screen.
  const used = new Set(themed.map(object => object.key));
  input.objects.forEach(object => {
    for (const [id, variant] of Object.entries(pack.objects[object.art_id] ?? {})) {
      const key = `theme:${id}`;
      if (used.has(key)) continue;
      used.add(key);
      extras.push({ key, src: variant.src });
    }
  });
  return {
    themeId: pack.theme_id,
    themeName: pack.display_name,
    background: { key: `theme:background:${background.src}`, src: background.src },
    objects: themed,
    extras,
  };
}
