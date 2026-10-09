import { paintedAssets, type RoomBox } from '../assets/manifest';
export default function PaintedObject({ assetKey, box, className = '' }: { assetKey: keyof typeof paintedAssets; box?: RoomBox; className?: string }) {
  const asset = paintedAssets[assetKey], b = asset.bbox;
  const scale = box ? Math.min(box[2] / b.width, box[3] / b.height) : 1;
  const outer = box ? { left: `${(box[0] + (box[2] - b.width * scale) / 2) / 16}%`, top: `${(box[1] + (box[3] - b.height * scale) / 2) / 9}%`, width: `${b.width * scale / 16}%`, height: `${b.height * scale / 9}%` } : { width: '100%', aspectRatio: `${b.width}/${b.height}` };
  return <span className={`painted-object ${box ? 'painted-placed' : ''} ${className}`} aria-hidden="true" style={outer}><img src={asset.url} alt="" draggable={false} style={{ position: 'absolute', width: `${asset.width / b.width * 100}%`, height: `${asset.height / b.height * 100}%`, left: `${-b.x / b.width * 100}%`, top: `${-b.y / b.height * 100}%`, maxWidth: 'none' }}/></span>;
}
