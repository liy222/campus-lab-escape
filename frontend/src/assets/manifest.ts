// Original R1 SVG assets. Coordinates are top-left CSS pixels in a 1600x900 room viewport.
export const room1Assets: Record<string, string> = {
  background: new URL('r1_background.svg', import.meta.url).href,
  clock: new URL('r1_clock.svg', import.meta.url).href,
  record: new URL('r1_record.svg', import.meta.url).href,
  plaque: new URL('r1_plaque.svg', import.meta.url).href,
  microscope_empty: new URL('r1_microscope_empty.svg', import.meta.url).href,
  microscope_slide: new URL('r1_microscope_slide.svg', import.meta.url).href,
  cabinet_locked: new URL('r1_cabinet_locked.svg', import.meta.url).href,
  cabinet_accepted: new URL('r1_cabinet_accepted.svg', import.meta.url).href,
  cabinet_open: new URL('r1_cabinet_open.svg', import.meta.url).href,
  cabinet_empty: new URL('r1_cabinet_empty.svg', import.meta.url).href,
  cabinet_symbols: new URL('r1_symbols.svg', import.meta.url).href,
  fuse: new URL('r1_fuse.svg', import.meta.url).href,
  photo_revealed: new URL('r1_photo.svg', import.meta.url).href,
  door_closed: new URL('r1_door_closed.svg', import.meta.url).href,
  door_unlatched: new URL('r1_door_unlatched.svg', import.meta.url).href,
  closeup_clock: new URL('closeup_clock.svg', import.meta.url).href,
  closeup_record: new URL('closeup_record.svg', import.meta.url).href,
  closeup_plaque: new URL('closeup_plaque.svg', import.meta.url).href,
  closeup_microscope_empty: new URL('closeup_microscope_empty.svg', import.meta.url).href,
  closeup_microscope_slide: new URL('closeup_microscope_slide.svg', import.meta.url).href,
  microscope_view: new URL('microscope_view.svg', import.meta.url).href,
  closeup_cabinet_locked: new URL('closeup_cabinet_locked.svg', import.meta.url).href,
  closeup_cabinet_open: new URL('closeup_cabinet_open.svg', import.meta.url).href,
  photo_closeup: new URL('photo_closeup.svg', import.meta.url).href,
  'r1_background': new URL('r1_background.svg', import.meta.url).href,
  'r1_cabinet_accepted': new URL('r1_cabinet_accepted.svg', import.meta.url).href,
  'r1_cabinet_empty': new URL('r1_cabinet_empty.svg', import.meta.url).href,
  'r1_cabinet_locked': new URL('r1_cabinet_locked.svg', import.meta.url).href,
  'r1_cabinet_open': new URL('r1_cabinet_open.svg', import.meta.url).href,
  'r1_clock': new URL('r1_clock.svg', import.meta.url).href,
  'r1_door_closed': new URL('r1_door_closed.svg', import.meta.url).href,
  'r1_door_unlatched': new URL('r1_door_unlatched.svg', import.meta.url).href,
  'r1_fuse': new URL('r1_fuse.svg', import.meta.url).href,
  'r1_microscope_empty': new URL('r1_microscope_empty.svg', import.meta.url).href,
  'r1_microscope_slide': new URL('r1_microscope_slide.svg', import.meta.url).href,
  'r1_photo': new URL('r1_photo.svg', import.meta.url).href,
  'r1_plaque': new URL('r1_plaque.svg', import.meta.url).href,
  'r1_record': new URL('r1_record.svg', import.meta.url).href,
  'r1_symbols': new URL('r1_symbols.svg', import.meta.url).href,
  'r1_workbench': new URL('r1_workbench.svg', import.meta.url).href,
  'sample_slide': new URL('sample_slide.svg', import.meta.url).href,
};

export const room1Layout: Record<string, [number, number, number, number]> = {
  "r1_clock": [
    650,
    70,
    150,
    150
  ],
  "r1_plaque": [
    1250,
    160,
    170,
    85
  ],
  "r1_workbench": [
    420,
    380,
    760,
    300
  ],
  "r1_microscope": [
    670,
    400,
    250,
    230
  ],
  "r1_record": [
    910,
    475,
    170,
    125
  ],
  "sample_slide": [
    570,
    535,
    110,
    35
  ],
  "r1_cabinet": [
    90,
    590,
    300,
    240
  ],
  "r1_door": [
    1260,
    390,
    250,
    410
  ],
  "r1_symbols": [
    155,
    635,
    150,
    80
  ],
  "r1_fuse": [
    190,
    725,
    70,
    35
  ],
  "r1_photo": [
    175,
    660,
    130,
    100
  ]
};

export const room1Viewport = { width: 1600, height: 900 } as const;
