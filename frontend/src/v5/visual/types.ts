import type { GameObject, VisibleState } from '../../api';

export type GeneratedObject = GameObject & { art_id: string; slot: number; target_id?: string | null; completed?: boolean; mechanism?: string | null };

export type GeneratedState = Omit<VisibleState, 'objects' | 'room' | 'minigames'> & {
  mode: 'generated';
  level_id: string;
  definition_hash: string;
  room: VisibleState['room'] & { background_id?: string; background_art_id?: string };
  objects: GeneratedObject[];
  minigames?: VisibleState['minigames'] & {
    circuits?: NonNullable<VisibleState['minigames']>['circuit'][];
    sequences?: NonNullable<VisibleState['minigames']>['sequence'][];
  };
};

export type Box = { x: number; y: number; width: number; height: number };

export type ThemeVariant = {
  role: string;
  state: 'default' | 'completed';
  note_style: string | null;
  src: string;
  closeup: string;
  width: number;
  height: number;
  bbox: Box;
  closeup_width: number;
  closeup_height: number;
  closeup_bbox: Box;
};

export type ThemeSlot = { x: number; y: number; height: number; hotspot: Box };

export type ThemePack = {
  schema_version: 1;
  theme_id: string;
  pack_version: string;
  display_name: string;
  coverage?: string;
  backgrounds: Record<string, { src: string; width: number; height: number }>;
  objects: Record<string, Record<string, ThemeVariant>>;
  slot_layout: Record<string, ThemeSlot[]>;
};

/** One object as it is actually painted in the scene. */
export type SceneObject = {
  object_id: string;
  name: string;
  completed: boolean;
  kind: string;
  key: string;
  src: string;
  bbox: Box;
  x: number;
  y: number;
  renderHeight: number;
  hotspot: Box;
  closeup: string | null;
  closeupBox: Box | null;
  variantId: string | null;
  fallback: { key: string; src: string; bbox: Box } | null;
};

export type SceneModel = {
  themeId: string | null;
  themeName: string | null;
  background: { key: string; src: string; fallback?: { key: string; src: string } };
  objects: SceneObject[];
  /** Other variants of the roles in this room, so a completion can swap art without a reload. */
  extras: { key: string; src: string }[];
};
