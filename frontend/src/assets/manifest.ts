// Hand-painted PNGs are served as original bytes. Metadata owns the source-pixel crop.
import paintedMetadata from './painted-metadata.json';
export type RoomBox = [number, number, number, number];
export const paintedAssets = paintedMetadata;
function assetsFor(room: string): Record<string, string> {
  return Object.fromEntries(Object.entries(paintedMetadata).filter(([, asset]) => asset.url.includes(`/${room}/`)).map(([key, asset]) => [key, asset.url]));
}
export const room1Assets: Record<string, string> = { ...assetsFor('room1'), background: paintedMetadata.r1_background.url };
export const room2Assets: Record<string, string> = { ...assetsFor('room2'), r2_background_dark: paintedMetadata.r2_background_dark.url, r2_background_on: paintedMetadata.r2_background_on.url };
export const room3Assets: Record<string, string> = { ...assetsFor('room3'), r3_background: paintedMetadata.r3_background.url, r3_background_off: paintedMetadata.r3_background_off.url };
export const room1Viewport = { width: 1600, height: 900 } as const;
// Boxes enclose the visible, cropped artwork rather than the transparent PNG canvas.
export const room1Layout: Record<string, RoomBox> = {
  r1_clock: [670, 90, 145, 145], r1_plaque: [1250, 190, 190, 82],
  r1_workbench: [415, 505, 770, 315], r1_microscope: [635, 360, 230, 250],
  r1_record: [940, 472, 145, 150], sample_slide: [520, 565, 110, 35],
  r1_cabinet: [65, 540, 330, 270], r1_door: [1260, 325, 230, 475],
  r1_symbols: [245, 603, 94, 40], r1_fuse: [157, 704, 110, 30], r1_photo: [180, 689, 105, 72],
};
export const room2Layout: Record<string, RoomBox> = {
  r2_return_door: [25, 285, 200, 505], r2_powerbox: [232, 327, 260, 305],
  r2_maintenance: [527, 444, 145, 110], r2_monitor: [871, 300, 286, 270],
  r2_door: [1290, 330, 225, 460], r2_tray: [867, 568, 310, 100],
  research_strip: [893, 590, 145, 47], access_card: [1060, 590, 99, 58],
  r2_service_label: [440, 575, 110, 55], r2_workbench: [490, 475, 725, 310],
};
export const room3Layout: Record<string, RoomBox> = {
  r3_legend: [290, 210, 250, 290], r3_panel: [660, 245, 320, 535],
  exit_door: [1175, 285, 285, 525], r3_return_door: [35, 285, 225, 525],
};
