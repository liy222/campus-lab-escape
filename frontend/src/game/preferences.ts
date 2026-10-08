import { useEffect, useRef, useState } from 'react';
import type { Receipt, VisibleState } from '../api';

type Cue = 'paper' | 'metal' | 'button' | 'power' | 'success' | 'error' | 'door';
// Audio is local presentation: it never sends requests or changes game state.
export function useGamePresentation(receipt: Receipt | null, state: VisibleState | null) {
  const [muted, setMuted] = useState(false);
  const [systemReduced, setSystemReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const [manualReduced, setManualReduced] = useState(false);
  const [audioState, setAudioState] = useState('locked');
  const [cueCount, setCueCount] = useState(0);
  const [lastCue, setLastCue] = useState<string>('none');
  const context = useRef<AudioContext | null>(null), mutedRef = useRef(muted), seen = useRef(new Set<string>());
  mutedRef.current = muted;
  const reducedMotion = systemReduced || manualReduced;
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setSystemReduced(query.matches); query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);
  useEffect(() => {
    const unlock = (event: Event) => {
      if (!event.isTrusted || mutedRef.current) return;
      try {
        context.current ||= new AudioContext();
        void context.current.resume().then(() => setAudioState('ready')).catch(() => setAudioState('unavailable'));
      } catch { setAudioState('unavailable'); }
    };
    window.addEventListener('pointerdown', unlock, true); window.addEventListener('keydown', unlock, true);
    return () => { window.removeEventListener('pointerdown', unlock, true); window.removeEventListener('keydown', unlock, true); void context.current?.close(); };
  }, []);
  function play(cue: Cue) {
    const ctx = context.current;
    if (!ctx || ctx.state !== 'running' || mutedRef.current) return;
    const start = ctx.currentTime, osc = ctx.createOscillator(), gain = ctx.createGain();
    const values: Record<Cue, [number, number, number]> = { paper: [850, 300, .09], metal: [170, 85, .12], button: [470, 360, .06], power: [90, 160, .28], success: [440, 660, .22], error: [220, 150, .13], door: [95, 48, .65] };
    const [from, to, length] = values[cue]; osc.type = cue === 'paper' ? 'triangle' : 'sine';
    osc.frequency.setValueAtTime(from, start); osc.frequency.exponentialRampToValueAtTime(to, start + length);
    gain.gain.setValueAtTime(0, start); gain.gain.linearRampToValueAtTime(.028, start + .012); gain.gain.exponentialRampToValueAtTime(.0001, start + length);
    osc.connect(gain); gain.connect(ctx.destination); osc.start(); osc.stop(start + length + .03);
    osc.onended = () => { osc.disconnect(); gain.disconnect(); };
    setCueCount(count => count + 1); setLastCue(cue);
  }
  useEffect(() => {
    if (!receipt || !state || receipt.generation !== state.generation || receipt.revision_after !== state.revision || !receipt.changed || seen.current.has(receipt.event_id)) return;
    seen.current.add(receipt.event_id);
    const target = String(receipt.arguments.target_id || receipt.arguments.item_id || receipt.arguments.object_id || '');
    if (receipt.tool === 'move') play('door');
    else if (receipt.tool === 'take' || receipt.tool === 'inspect' || target === 'r3_panel' && receipt.tool === 'use_item') play('paper');
    else if (receipt.tool === 'rotate_circuit') play('button');
    else if (['submit_code', 'submit_login', 'submit_circuit', 'submit_sequence'].includes(receipt.tool)) play('success');
    else if (target === 'r2_powerbox') play('power');
    else if (target === 'exit_door' && state.device_states?.exit === 'OPEN') play('door');
    else play('metal');
  }, [receipt, state]);
  useEffect(() => {
    const ctx = context.current;
    if (!ctx || audioState !== 'ready' || muted || state?.status !== 'playing' || state.level_version !== '3.4.0') return;
    const noise = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate), values = noise.getChannelData(0);
    for (let i = 0; i < values.length; i++) values[i] = (Math.random() * 2 - 1) * .3;
    const source = ctx.createBufferSource(), filter = ctx.createBiquadFilter(), gain = ctx.createGain();
    source.buffer = noise; source.loop = true; filter.type = 'lowpass'; filter.frequency.value = state.room.room_id === 'R2' ? 220 : 110;
    gain.gain.value = .012; source.connect(filter); filter.connect(gain); gain.connect(ctx.destination); source.start();
    return () => { source.stop(); source.disconnect(); filter.disconnect(); gain.disconnect(); };
  }, [audioState, muted, state?.room.room_id, state?.status, state?.level_version]);
  return { muted, setMuted, reducedMotion, manualReduced, setManualReduced, systemReduced, audioState: muted ? 'muted' : audioState, cueCount, lastCue, play };
}
