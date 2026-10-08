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


// Additive R2 SVG assets. The accepted R1 exports and assets remain unchanged.
export const room2Assets: Record<string, string> = {
  r2_access_card: new URL('r2_access_card.svg', import.meta.url).href,
  r2_background_dark: new URL('r2_background_dark.svg', import.meta.url).href,
  r2_closeup_maintenance: new URL('r2_closeup_maintenance.svg', import.meta.url).href,
  r2_closeup_monitor_booting: new URL('r2_closeup_monitor_booting.svg', import.meta.url).href,
  r2_closeup_monitor_data_read: new URL('r2_closeup_monitor_data_read.svg', import.meta.url).href,
  r2_closeup_monitor_login_locked: new URL('r2_closeup_monitor_login_locked.svg', import.meta.url).href,
  r2_closeup_monitor_off: new URL('r2_closeup_monitor_off.svg', import.meta.url).href,
  r2_closeup_monitor_unlocked: new URL('r2_closeup_monitor_unlocked.svg', import.meta.url).href,
  r2_closeup_powerbox_circuit_ready: new URL('r2_closeup_powerbox_circuit_ready.svg', import.meta.url).href,
  r2_closeup_powerbox_closed: new URL('r2_closeup_powerbox_closed.svg', import.meta.url).href,
  r2_closeup_powerbox_fuse_installed: new URL('r2_closeup_powerbox_fuse_installed.svg', import.meta.url).href,
  r2_closeup_powerbox_missing_fuse: new URL('r2_closeup_powerbox_missing_fuse.svg', import.meta.url).href,
  r2_closeup_powerbox_open: new URL('r2_closeup_powerbox_open.svg', import.meta.url).href,
  r2_closeup_powerbox_power_on: new URL('r2_closeup_powerbox_power_on.svg', import.meta.url).href,
  r2_closeup_service_label: new URL('r2_closeup_service_label.svg', import.meta.url).href,
  r2_door_closed: new URL('r2_door_closed.svg', import.meta.url).href,
  r2_door_unlatched: new URL('r2_door_unlatched.svg', import.meta.url).href,
  r2_light_overlay_on: new URL('r2_light_overlay_on.svg', import.meta.url).href,
  r2_maintenance: new URL('r2_maintenance.svg', import.meta.url).href,
  r2_monitor_booting: new URL('r2_monitor_booting.svg', import.meta.url).href,
  r2_monitor_data_read: new URL('r2_monitor_data_read.svg', import.meta.url).href,
  r2_monitor_login_locked: new URL('r2_monitor_login_locked.svg', import.meta.url).href,
  r2_monitor_off: new URL('r2_monitor_off.svg', import.meta.url).href,
  r2_monitor_unlocked: new URL('r2_monitor_unlocked.svg', import.meta.url).href,
  r2_powerbox_circuit_ready: new URL('r2_powerbox_circuit_ready.svg', import.meta.url).href,
  r2_powerbox_closed: new URL('r2_powerbox_closed.svg', import.meta.url).href,
  r2_powerbox_fuse_installed: new URL('r2_powerbox_fuse_installed.svg', import.meta.url).href,
  r2_powerbox_missing_fuse: new URL('r2_powerbox_missing_fuse.svg', import.meta.url).href,
  r2_powerbox_open: new URL('r2_powerbox_open.svg', import.meta.url).href,
  r2_powerbox_power_on: new URL('r2_powerbox_power_on.svg', import.meta.url).href,
  r2_research_strip: new URL('r2_research_strip.svg', import.meta.url).href,
  r2_return_door: new URL('r2_return_door.svg', import.meta.url).href,
  r2_service_label: new URL('r2_service_label.svg', import.meta.url).href,
  r2_tray: new URL('r2_tray.svg', import.meta.url).href,
  r2_workbench: new URL('r2_workbench.svg', import.meta.url).href,
};

export const room2Layout: Record<string, [number, number, number, number]> = {
  r2_return_door: [28, 365, 165, 375],
  r2_powerbox: [218, 382, 232, 250],
  r2_maintenance: [478, 422, 150, 100],
  r2_monitor: [868, 319, 272, 232],
  r2_door: [1288, 350, 238, 410],
  r2_tray: [850, 536, 318, 112],
  research_strip: [887, 566, 145, 68],
  access_card: [1041, 565, 110, 72],
  r2_service_label: [429, 480, 108, 58],
  r2_workbench: [376, 402, 775, 300],
};


// Additive R3 SVG assets. The accepted R1/R2 exports and assets remain unchanged.
export const room3Assets: Record<string, string> = {
  r3_background: new URL('r3_background.svg', import.meta.url).href,
  r3_legend: new URL('r3_legend.svg', import.meta.url).href,
  r3_panel_empty: new URL('r3_panel_empty.svg', import.meta.url).href,
  r3_panel_strip_inserted: new URL('r3_panel_strip_inserted.svg', import.meta.url).href,
  r3_panel_final_check: new URL('r3_panel_final_check.svg', import.meta.url).href,
  r3_panel_passed: new URL('r3_panel_passed.svg', import.meta.url).href,
  r3_exit_door_locked: new URL('r3_exit_door_locked.svg', import.meta.url).href,
  r3_exit_door_card_accepted: new URL('r3_exit_door_card_accepted.svg', import.meta.url).href,
  r3_exit_door_final_check: new URL('r3_exit_door_final_check.svg', import.meta.url).href,
  r3_exit_door_unlocked: new URL('r3_exit_door_unlocked.svg', import.meta.url).href,
  r3_exit_door_open: new URL('r3_exit_door_open.svg', import.meta.url).href,
  r3_return_door: new URL('r3_return_door.svg', import.meta.url).href,
  r3_closeup_legend: new URL('r3_closeup_legend.svg', import.meta.url).href,
  r3_closeup_panel_empty: new URL('r3_closeup_panel_empty.svg', import.meta.url).href,
  r3_closeup_panel_strip_inserted: new URL('r3_closeup_panel_strip_inserted.svg', import.meta.url).href,
  r3_closeup_panel_final_check: new URL('r3_closeup_panel_final_check.svg', import.meta.url).href,
  r3_closeup_panel_passed: new URL('r3_closeup_panel_passed.svg', import.meta.url).href,
  r3_closeup_exit_door_locked: new URL('r3_closeup_exit_door_locked.svg', import.meta.url).href,
  r3_closeup_exit_door_card_accepted: new URL('r3_closeup_exit_door_card_accepted.svg', import.meta.url).href,
  r3_closeup_exit_door_final_check: new URL('r3_closeup_exit_door_final_check.svg', import.meta.url).href,
  r3_closeup_exit_door_unlocked: new URL('r3_closeup_exit_door_unlocked.svg', import.meta.url).href,
  r3_closeup_exit_door_open: new URL('r3_closeup_exit_door_open.svg', import.meta.url).href,
  r3_victory_background: new URL('r3_victory_background.svg', import.meta.url).href,
};

export const room3Layout: Record<string, [number, number, number, number]> = {
  r3_legend: [280, 200, 330, 245],
  r3_panel: [690, 285, 335, 390],
  exit_door: [1195, 280, 270, 525],
  r3_return_door: [35, 330, 145, 390],
};
