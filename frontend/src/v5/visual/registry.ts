import rainyAstronomy from '../../assets/themes/rainy-astronomy/manifest.json';
import libraryArchive from '../../assets/themes/library-archive/manifest.json';
import chemistryLab from '../../assets/themes/chemistry-lab/manifest.json';
import computerRoom from '../../assets/themes/computer-room/manifest.json';
import campusBroadcast from '../../assets/themes/campus-broadcast/manifest.json';
import type { ThemePack, ThemeSelection } from './types';

type PackEntry = { pack: ThemePack; match: RegExp; keywords: string[] };

/**
 * Local theme packs. Only metadata is bundled; the artwork itself is requested
 * per room, so an unsupported theme never downloads a themed image.
 */
const entries: PackEntry[] = [
  {
    pack: rainyAstronomy as ThemePack,
    keywords: ['天文社', '天文', '观星', '星图', '星座', '望远镜', '天文台', '流星', '银河'],
    match: /天文|观星|星图|星座|望远镜|天文台|流星|银河|星野|astronom|observator|telescope|stargaz|star[\s-]?chart|constellation|planetarium/i,
  },
  {
    pack: libraryArchive as ThemePack,
    keywords: ['图书馆', '阅览室', '借阅室', '校史馆', '档案馆'],
    match: /图书馆|阅览室|借阅室|校史馆|档案馆|(?:图书|借阅)档案|\blibrar(?:y|ies)\b|\breading[\s-]+room\b|\b(?:library|school)[\s-]+archive\b/i,
  },
  {
    pack: chemistryLab as ThemePack,
    keywords: ['化学实验室', '化学教室', '化学准备室', '化学'],
    match: /化学|\bchemistry\b|\bchemical[\s-]+(?:lab(?:oratory)?|room)\b/i,
  },
  {
    pack: computerRoom as ThemePack,
    keywords: ['计算机', '电脑室', '机房', '微机室', '信息技术教室'],
    match: /计算机|电脑室|机房|微机室|信息技术教室|\bcomputer(?:s)?\b|\bcomputing[\s-]+(?:lab(?:oratory)?|room)\b/i,
  },
  {
    pack: campusBroadcast as ThemePack,
    keywords: ['广播室', '广播站', '广播台', '校园广播', '广播社'],
    match: /广播室|广播站|广播台|校园广播|广播社|\bbroadcast(?:ing)?\b|\bradio[\s-]+(?:station|room)\b/i,
  },
];

export type ThemeCoverage = {
  pack: ThemePack | null;
  name: string | null;
  /** True when the free text is close to a supported theme but not matched. */
  related: boolean;
};

export function themeCoverage(theme?: string | null): ThemeCoverage {
  const text = (theme ?? '').trim();
  if (!text) return { pack: null, name: null, related: false };
  // Choose the earliest explicit theme mention, rather than registry order.
  // No global regexes or random choice: mixed descriptions resolve identically on reload.
  let matched: PackEntry | null = null;
  let firstIndex = Infinity;
  for (const entry of entries) {
    const index = text.search(entry.match);
    if (index >= 0 && index < firstIndex) { matched = entry; firstIndex = index; }
  }
  const related = !matched && /观测|记录|雨夜|活动室|封存|档案/.test(text);
  return { pack: matched?.pack ?? null, name: matched?.pack.display_name ?? null, related };
}

export function themePackFor(theme?: string | null): ThemePack | null {
  return themeCoverage(theme).pack;
}

export function packKeywords(pack: ThemePack): string[] {
  return entries.find(entry => entry.pack.theme_id === pack.theme_id)?.keywords ?? [];
}

/** FNV-1a: stable variant choice that never changes between renders or reloads. */
export function stableHash(value: string): number {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

/** Mix both halves before small-pool modulo; fixed suffixes must not lock binary choices together. */
function visualIndex(seed: string, length: number): number {
  let hash = stableHash(seed);
  hash ^= hash >>> 16;
  hash = Math.imul(hash, 0x85ebca6b);
  hash ^= hash >>> 13;
  hash = Math.imul(hash, 0xc2b2ae35);
  hash ^= hash >>> 16;
  return (hash >>> 0) % length;
}

/** Only complete ISO timestamps are metadata; malformed dates keep legacy art. */
function selectionTime(value?: string | null): number | null {
  if (!value) return null;
  const parts = /^(\d{4}-\d{2}-\d{2})T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/.exec(value);
  if (!parts) return null;
  const date = Date.parse(`${parts[1]}T00:00:00Z`), time = Date.parse(value);
  if (!Number.isFinite(date) || !Number.isFinite(time) || new Date(date).toISOString().slice(0, 10) !== parts[1]) return null;
  return time;
}

function availableAt(candidate: { available_from?: string }, createdAt?: string | null): boolean {
  if (candidate.available_from === undefined) return true;
  const created = selectionTime(createdAt), available = selectionTime(candidate.available_from);
  return created !== null && available !== null && created >= available;
}

const CHART_NAME = /星图|星座|星象|天球|chart/i;
const SEALED_NAME = /便笺|便条|封存|信封|封条|便函|note/i;

/** Resolve the existing paper category first, then choose an eligible design within it. */
export function noteVariantFor(
  pack: ThemePack,
  name: string,
  seed: string,
  createdAt?: string | null,
): { id: string; variant: ThemePack['objects'][string][string] } | null {
  const variants = Object.entries(pack.objects.note ?? {}).filter(([, variant]) => variant.state === 'default' && availableAt(variant, createdAt));
  if (!variants.length) return null;
  const wanted = CHART_NAME.test(name) ? 'star-chart' : SEALED_NAME.test(name) ? 'sealed-note' : null;
  const preferred = variants.find(([, variant]) => variant.note_style === wanted) ?? variants.find(([, variant]) => variant.note_style === 'logbook');
  const pool = preferred ? variants.filter(([, variant]) => variant.note_style === preferred[1].note_style) : variants;
  const [id, variant] = pool[visualIndex(seed, pool.length)];
  return { id, variant };
}

export function variantFor(
  pack: ThemePack,
  role: string,
  seed: string,
  completed: boolean,
  createdAt?: string | null,
): { id: string; variant: ThemePack['objects'][string][string] } | null {
  const variants = Object.entries(pack.objects[role] ?? {}).filter(([, variant]) => availableAt(variant, createdAt)).sort(([a], [b]) => a.localeCompare(b));
  if (!variants.length) return null;
  const defaults = variants.filter(([, variant]) => variant.state === 'default');
  const completedVariants = variants.filter(([, variant]) => variant.state === 'completed');
  const pool = defaults.length ? defaults : variants;
  const selected = pool[visualIndex(`${role}:${seed}`, pool.length)];
  // Completion changes state on the selected machine, never its appearance family.
  // Old manifests without family keep their previous single completed-state behavior.
  const finished = completed ? (selected[1].family
    ? completedVariants.find(([, variant]) => variant.family === selected[1].family)
    : completedVariants[0]) : undefined;
  const [id, variant] = finished ?? selected;
  return { id, variant };
}

export function packBackground(pack: ThemePack, backgroundId?: string | null, selection?: ThemeSelection) {
  const id = backgroundId && pack.backgrounds[backgroundId] ? backgroundId : 'neutral_lab';
  const base = { id, variantId: id, background: pack.backgrounds[id], slots: pack.slot_layout[id] ?? pack.slot_layout.neutral_lab };
  if (!selection?.level_id || selectionTime(selection.created_at) === null) return base;
  const pool = (pack.background_variants?.[id] ?? []).filter(candidate => availableAt(candidate, selection.created_at));
  if (!pool.length) return base;
  const selected = pool[visualIndex(`${selection.level_id}:${id}`, pool.length)];
  return { id, variantId: selected.id, background: selected.background, slots: selected.slots };
}
