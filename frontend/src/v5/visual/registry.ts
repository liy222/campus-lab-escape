import rainyAstronomy from '../../assets/themes/rainy-astronomy/manifest.json';
import libraryArchive from '../../assets/themes/library-archive/manifest.json';
import chemistryLab from '../../assets/themes/chemistry-lab/manifest.json';
import computerRoom from '../../assets/themes/computer-room/manifest.json';
import campusBroadcast from '../../assets/themes/campus-broadcast/manifest.json';
import type { ThemePack } from './types';

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

const CHART_NAME = /星图|星座|星象|天球|chart/i;
const SEALED_NAME = /便笺|便条|封存|信封|封条|便函|note/i;

/** Paper objects keep an identity that matches their published name. */
export function noteVariantFor(
  pack: ThemePack,
  name: string,
  seed: string,
): { id: string; variant: ThemePack['objects'][string][string] } | null {
  const variants = Object.entries(pack.objects.note ?? {}).filter(([, variant]) => variant.state === 'default');
  if (!variants.length) return null;
  const wanted = CHART_NAME.test(name) ? 'star-chart' : SEALED_NAME.test(name) ? 'sealed-note' : null;
  const preferred = variants.find(([, variant]) => variant.note_style === wanted) ?? variants.find(([, variant]) => variant.note_style === 'logbook');
  const [id, variant] = preferred ?? variants[stableHash(`${seed}`) % variants.length];
  return { id, variant };
}

export function variantFor(
  pack: ThemePack,
  role: string,
  seed: string,
  completed: boolean,
): { id: string; variant: ThemePack['objects'][string][string] } | null {
  const variants = Object.entries(pack.objects[role] ?? {}).sort(([a], [b]) => a.localeCompare(b));
  if (!variants.length) return null;
  const defaults = variants.filter(([, variant]) => variant.state === 'default');
  const completedVariants = variants.filter(([, variant]) => variant.state === 'completed');
  if (completed && completedVariants.length) {
    const [id, variant] = completedVariants[0];
    return { id, variant };
  }
  const pool = defaults.length ? defaults : variants;
  const [id, variant] = pool[stableHash(`${role}:${seed}`) % pool.length];
  return { id, variant };
}

export function packBackground(pack: ThemePack, backgroundId?: string | null) {
  const id = backgroundId && pack.backgrounds[backgroundId] ? backgroundId : 'neutral_lab';
  return { id, background: pack.backgrounds[id], slots: pack.slot_layout[id] ?? pack.slot_layout.neutral_lab };
}
