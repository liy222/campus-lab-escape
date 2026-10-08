import type { Receipt, VisibleState } from '../api';

export type SceneInput = { kind: 'object'; objectId: string } | { kind: 'action'; tool: 'inspect' | 'take' | 'interact' | 'move' | 'submit_circuit'; targetId: string } | { kind: 'circuit-module'; targetId: string; moduleId: string } | { kind: 'sequence-device'; targetId: string; deviceId: string };
export function sameSceneInput(left: SceneInput, right: SceneInput): boolean {
  if (left.kind === 'object') return right.kind === 'object' && left.objectId === right.objectId;
  if (left.kind === 'action') return right.kind === 'action' && left.tool === right.tool && left.targetId === right.targetId;
  if (left.kind === 'circuit-module') return right.kind === 'circuit-module' && left.targetId === right.targetId && left.moduleId === right.moduleId;
  return right.kind === 'sequence-device' && left.targetId === right.targetId && left.deviceId === right.deviceId;
}

export interface SceneProjection {
  state: VisibleState;
  view: string | null;
  disabled: boolean;
  animation: Receipt | null;
  minHitArea?: number;
  sequenceDraft?: string[];
  reducedMotion?: boolean;
}
// The bridge carries public snapshots and intents. It never owns game rules or credentials.
export class GameBridge {
  projection: SceneProjection;
  onInput: (input: SceneInput) => void;
  constructor(projection: SceneProjection, onInput: (input: SceneInput) => void) {
    this.projection = projection;
    this.onInput = onInput;
  }
  emit(input: SceneInput) { if (!this.projection.disabled) this.onInput(input); }
}
