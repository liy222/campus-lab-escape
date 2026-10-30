import catalog from '../../assets/generated-catalog.json';
import rainyAstronomy from '../../assets/themes/rainy-astronomy/manifest.json';
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
  created_at?: string | null;
  theme?: string | null;
  room: { name: string; background_id?: string | null; background_art_id?: string | null };
  objects: SceneObjectInput[];
};

type LegacyAsset = { id: string; url: string; width: number; height: number; bbox: { x: number; y: number; width: number; height: number } };

const legacyAssets = catalog.assets as LegacyAsset[];

/** The legacy catalogue painted the key as an old fuse; use the neutral brass key instead. */
const brassKey = rainyAstronomy.objects.key['key-brass'];
const neutralKey = { id: 'key', url: brassKey.src, width: brassKey.width, height: brassKey.height, bbox: brassKey.bbox };

function neutralAsset(role: string): LegacyAsset {
  return role === 'key' ? neutralKey : legacyAssets.find(candidate => candidate.id === role) ?? legacyAssets.find(candidate => candidate.id === 'note')!;
}

function legacyObject(object: SceneObjectInput, index: number, slotIndex: number): SceneObject {
  const asset = neutralAsset(object.art_id);
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
    closeup: object.art_id === 'key' ? brassKey.closeup : asset.url,
    closeupBox: object.art_id === 'key' ? brassKey.closeup_bbox : asset.bbox,
    variantId: null,
    fallback: null,
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
  const { background, slots } = packBackground(pack, input.room.background_id || input.room.background_art_id, { level_id: input.level_id, created_at: input.created_at });
  const themed: SceneObject[] = [];
  const extras: { key: string; src: string }[] = [];
  objects.forEach(({ object, index }) => {
    const slotIndex = Math.max(0, Math.min(slots.length - 1, Number.isFinite(object.slot) ? object.slot : 0));
    const slot = slots[slotIndex];
    const resolved = object.art_id === 'note'
      ? noteVariantFor(pack, object.name, `${input.level_id}:${object.object_id}`, input.created_at)
      : variantFor(pack, object.art_id, `${input.level_id}:${object.object_id}`, Boolean(object.completed), input.created_at);
    if (!resolved || !slot) {
      themed.push(legacyObject(object, index, slotIndex));
      return;
    }
    const { id, variant } = resolved;
    const neutral = neutralAsset(object.art_id);
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
      fallback: neutral.url === variant.src ? null : { key: `fallback:${neutral.id}`, src: neutral.url, bbox: neutral.bbox },
    });
  });
  // Load only the paired state of the design selected for each current device.
  const used = new Set(themed.map(object => object.key));
  input.objects.filter(object => object.art_id !== 'note').forEach(object => {
    const other = variantFor(pack, object.art_id, `${input.level_id}:${object.object_id}`, !object.completed, input.created_at);
    if (!other) return;
    const key = `theme:${other.id}`;
    if (used.has(key)) return;
    used.add(key);
    extras.push({ key, src: other.variant.src });
  });
  const neutralBackground = legacyAssets.find(candidate => candidate.id === (input.room.background_id || input.room.background_art_id)) ?? legacyAssets.find(candidate => candidate.id === 'neutral_lab')!;
  return {
    themeId: pack.theme_id,
    themeName: pack.display_name,
    background: { key: `theme:background:${background.src}`, src: background.src, fallback: { key: `fallback:background:${neutralBackground.id}`, src: neutralBackground.url } },
    objects: themed,
    extras,
  };
}
