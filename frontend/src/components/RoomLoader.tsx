import { useEffect, useState, type ComponentProps, type ComponentType } from 'react';
type Props = ComponentProps<typeof import('./Room1').default> & ComponentProps<typeof import('./Room2').default> & ComponentProps<typeof import('./Room3').default> & { onReset: () => void; onRecords: () => void };
export default function RoomLoader(props: Props) {
  const mode = props.state.status === 'won' ? 'EXIT' : props.state.room.room_id;
  const [loaded, setLoaded] = useState<{ mode: string; Component: ComponentType<Props> } | null>(null);
  const [failed, setFailed] = useState(false), [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let cancelled = false; setFailed(false);
    const pending = mode === 'EXIT' ? import('./Settlement') : mode === 'R3' ? import('./Room3') : mode === 'R2' ? import('./Room2') : import('./Room1');
    void pending.then(module => { if (!cancelled) setLoaded({ mode, Component: module.default }); }).catch(() => { if (!cancelled) setFailed(true); });
    return () => { cancelled = true; };
  }, [mode, attempt]);
  if (failed) return <section className="room-loading" role="alert"><p>房间暂时未能打开，请重试。</p><button className="button room-retry" onClick={() => setAttempt(value => value + 1)}>重新载入画面</button></section>;
  if (!loaded || loaded.mode !== mode) return <section className="room-loading" role="status">正在打开房间…</section>;
  const Component = loaded.Component; return <Component {...props}/>;
}
