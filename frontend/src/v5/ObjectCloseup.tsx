import { useState } from 'react';
import type { SceneObject } from './visual/types';

/** A finite, deduplicated image chain; errors never retry the failed URL. */
export default function ObjectCloseup({ object }: { object: SceneObject }) {
  const candidates = [...new Set([object.closeup, object.src, object.fallback?.src].filter((src): src is string => Boolean(src)))];
  const [failed, setFailed] = useState<string[]>([]);
  const source = candidates.find(candidate => !failed.includes(candidate));
  return <div className={`v5-closeup ${object.variantId ?? 'generic'}`}>
    {source ? <img key={source} src={source} alt={`${object.name}的物件特写`} data-closeup-src={source} onError={() => setFailed(previous => previous.includes(source) ? previous : [...previous, source])} />
      : <p className="v5-image-fallback" role="status"><strong>{object.name}</strong><span>图片暂时无法显示。请阅读下方物件说明与线索，仍可继续操作。</span></p>}
  </div>;
}
