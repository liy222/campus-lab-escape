import fs from 'node:fs/promises';
import fsSync from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { createRequire } from 'node:module';
import { randomUUID } from 'node:crypto';
import zlib from 'node:zlib';
import http from 'node:http';
import net from 'node:net';
import { spawn, execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const root = process.cwd();
const stage = path.join(root, 'evidence/project/stages/v5-theme-variation/automated');
const started = new Date().toISOString();
const runId = randomUUID();
const out = path.join(stage, `qa-${started.replace(/[:.]/g, '-')}-${runId.slice(0, 8)}`);
const cutoff = '2026-10-30T04:44:56.276Z';
const themes = ['rainy-astronomy', 'library-archive', 'chemistry-lab', 'computer-room', 'campus-broadcast'];
const deviceRoles = ['terminal', 'cabinet', 'circuit', 'panel'];
const records = [];
const screenshots = [];
const issues = [];
let server = null, browserTemp = null, externalRequests = 0, serverStopped = true;
const check = (name, actual, expected, pass, scope = 'model/static') => {
  const item = {name, actual, expected, pass: !!pass, scope, observed_at_utc: new Date().toISOString()};
  records.push(item);
  if (process.env.THEME_VARIATION_FORMAL === '1' && fsSync.existsSync(out)) fsSync.appendFileSync(path.join(out, 'records.jsonl'), JSON.stringify(item) + '\n', 'utf8');
};

function paeth(a, b, c) { const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c); return pa <= pb && pa <= pc ? a : pb <= pc ? b : c; }
async function pngInfo(file) {
  const bytes = await fs.readFile(file);
  if (bytes.length < 33 || !bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) throw Error('PNG signature invalid');
  let pos = 8, width, height, depth, color, interlace, palette = null, transparency = null;
  const idats = [];
  while (pos + 12 <= bytes.length) {
    const len = bytes.readUInt32BE(pos), type = bytes.toString('ascii', pos + 4, pos + 8), data = bytes.subarray(pos + 8, pos + 8 + len); pos += len + 12;
    if (type === 'IHDR') { width = data.readUInt32BE(0); height = data.readUInt32BE(4); depth = data[8]; color = data[9]; interlace = data[12]; }
    else if (type === 'PLTE') palette = data;
    else if (type === 'tRNS') transparency = data;
    else if (type === 'IDAT') idats.push(data);
    else if (type === 'IEND') break;
  }
  if (depth !== 8 || interlace !== 0 || ![0, 2, 3, 4, 6].includes(color)) throw Error(`Unsupported PNG encoding ${depth}/${color}/${interlace}`);
  const channels = ({0: 1, 2: 3, 3: 1, 4: 2, 6: 4})[color], bpp = channels, rowSize = width * channels;
  const raw = zlib.inflateSync(Buffer.concat(idats));
  let previous = Buffer.alloc(rowSize), transparent = 0, nontransparent = 0, minX = width, minY = height, maxX = -1, maxY = -1, offset = 0;
  for (let y = 0; y < height; y++) {
    const filter = raw[offset++], row = Buffer.from(raw.subarray(offset, offset + rowSize)); offset += rowSize;
    for (let i = 0; i < rowSize; i++) {
      const left = i >= bpp ? row[i - bpp] : 0, up = previous[i], ul = i >= bpp ? previous[i - bpp] : 0;
      if (filter === 1) row[i] = (row[i] + left) & 255;
      else if (filter === 2) row[i] = (row[i] + up) & 255;
      else if (filter === 3) row[i] = (row[i] + Math.floor((left + up) / 2)) & 255;
      else if (filter === 4) row[i] = (row[i] + paeth(left, up, ul)) & 255;
      else if (filter !== 0) throw Error('Unknown PNG filter');
    }
    for (let x = 0; x < width; x++) {
      let alpha = 255;
      if (color === 6) alpha = row[x * 4 + 3];
      else if (color === 4) alpha = row[x * 2 + 1];
      else if (color === 3) alpha = transparency?.[row[x]] ?? 255;
      if (alpha === 0) transparent++;
      else { nontransparent++; minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y); }
    }
    previous = row;
  }
  return {width, height, alpha: {transparent, nontransparent}, alpha_bbox: maxX < 0 ? null : {x: minX, y: minY, width: maxX - minX + 1, height: maxY - minY + 1}};
}
function validBox(box, width, height) {
  return !!box && [box.x, box.y, box.width, box.height].every(Number.isFinite) && box.x >= 0 && box.y >= 0 && box.width > 0 && box.height > 0 && box.x + box.width <= width && box.y + box.height <= height;
}
function overlaps(a, b) { return !!a && !!b && a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height; }
function packPath(theme) { return path.join(root, 'frontend/src/assets/themes', theme, 'manifest.json'); }
async function readPacks() { return Promise.all(themes.map(async theme => [theme, JSON.parse(await fs.readFile(packPath(theme), 'utf8'))])); }
function srcOf(entry) { return entry?.background?.src ?? entry?.src ?? null; }
function collectNewAssets(packs) {
  const found = new Map();
  for (const [theme, pack] of packs) {
    for (const [baseId, entries] of Object.entries(pack.background_variants ?? {})) {
      for (const entry of entries) if (entry.available_from) found.set(srcOf(entry), {theme, kind: 'background', role: baseId, id: entry.id, available_from: entry.available_from, metadata: entry.background ?? entry});
    }
    for (const [role, variants] of Object.entries(pack.objects ?? {})) {
      for (const [id, variant] of Object.entries(variants)) if (variant.available_from) found.set(variant.src, {theme, kind: 'object', role, id, available_from: variant.available_from, metadata: variant});
    }
  }
  return [...found.values()];
}
async function staticAudit(packs) {
  let bgCount = 0;
  const assets = collectNewAssets(packs);
  for (const [theme, pack] of packs) {
    const backgrounds = pack.background_variants ?? {};
    const themeBgCount = Object.values(backgrounds).flat().filter(x => x.available_from).length;
    bgCount += themeBgCount;
    check(`${theme} has 3 dated background candidates`, themeBgCount, 3, themeBgCount === 3);
    let themeLogbooks = 0;
    for (const [role, variants] of Object.entries(pack.objects ?? {})) {
      for (const variant of Object.values(variants)) {
        if (role === 'note' && variant.available_from && variant.note_style === 'logbook') themeLogbooks++;
      }
    }
    check(`${theme} adds one dated logbook image`, themeLogbooks, 1, themeLogbooks === 1);
    for (const [baseId, candidates] of Object.entries(backgrounds)) {
      for (const candidate of candidates) {
        const bg = candidate.background ?? candidate;
        const slots = candidate.slots;
        const layoutOk = Array.isArray(slots) && slots.length === 8 && slots.every(slot => [slot.x, slot.y, slot.height, slot.hotspot?.x, slot.hotspot?.y, slot.hotspot?.width, slot.hotspot?.height].every(Number.isFinite) && slot.x >= 0 && slot.x <= 1920 && slot.y >= 0 && slot.y <= 1080 && slot.y - slot.height >= 0 && slot.height > 0 && slot.hotspot.width > 0 && slot.hotspot.height > 0 && slot.hotspot.x >= 0 && slot.hotspot.y >= 0 && slot.hotspot.x + slot.hotspot.width <= 1920 && slot.hotspot.y + slot.hotspot.height <= 1080);
        check(`${theme}/${baseId}/${candidate.id} background layout`, {dated: candidate.available_from ?? null, slots: slots?.length ?? 0, valid: layoutOk}, {valid: true}, layoutOk);
      }
    }
  }
  check('31 unique new source images', [...new Set(assets.map(x => x.metadata?.src).filter(Boolean))].length, 31, new Set(assets.map(x => x.metadata?.src).filter(Boolean)).size === 31);
  check('15 dated backgrounds', bgCount, 15, bgCount === 15);
  check('16 dated object images', assets.filter(x => x.kind === 'object').length, 16, assets.filter(x => x.kind === 'object').length === 16);
  check('all 31 resources share the stage availability timestamp', [...new Set(assets.map(x => x.available_from))], [cutoff], assets.length === 31 && assets.every(x => x.available_from === cutoff));
  for (const asset of assets) {
    const src = asset.metadata?.src;
    if (!src || !src.startsWith('/art-themes/')) { check(`${asset.theme}/${asset.id} safe local image path`, src, 'local /art-themes path', false); continue; }
    const local = path.resolve(root, 'frontend/public', src.replace(/^\//, ''));
    if (!local.startsWith(path.resolve(root, 'frontend/public') + path.sep)) { check(`${asset.theme}/${asset.id} path containment`, src, 'under frontend/public', false); continue; }
    const info = await pngInfo(local);
    const bboxOk = asset.kind === 'background' || !asset.metadata.bbox || (validBox(asset.metadata.bbox, info.width, info.height) && overlaps(info.alpha_bbox, asset.metadata.bbox));
    const sizeOk = info.width === asset.metadata.width && info.height === asset.metadata.height;
    const alphaOk = info.alpha.nontransparent > 0 && (asset.kind === 'background' || info.alpha.transparent > 0);
    check(`${asset.theme}/${asset.role}/${asset.id} PNG pixels and metadata`, {src, ...info, declared_width: asset.metadata.width, declared_height: asset.metadata.height, bbox: asset.metadata.bbox ?? null}, {dimensions_match: true, alpha_valid: true, bbox_in_bounds: true}, sizeOk && alphaOk && bboxOk);
  }
  if (process.env.THEME_VARIATION_FORMAL === '1') await fs.writeFile(path.join(out, 'static-assets.json'), JSON.stringify({theme_count: packs.length, new_source_count: assets.length, assets: assets.map(x => ({theme: x.theme, kind: x.kind, role: x.role, id: x.id, ...x.metadata}))}, null, 2) + '\n', {flag: 'wx'});
  return assets;
}

function sceneInputs(themeName, levelId, createdAt, baseId, completedRole = null, noteName = '记录本') {
  return {
    level_id: levelId,
    theme: themeName,
    created_at: createdAt,
    room: {name: baseId, background_id: baseId},
    objects: [
      {object_id: 'qa-note', name: noteName, kind: 'clue', art_id: 'note', slot: 0},
      ...deviceRoles.map((role, index) => ({object_id: `qa-${role}`, name: `校验${role}`, kind: role === 'terminal' || role === 'circuit' ? 'puzzle' : 'prop', art_id: role, slot: index + 1, completed: completedRole === role})),
      {object_id: 'qa-key', name: '黄铜钥匙', kind: 'item', art_id: 'key', slot: 5},
    ],
  };
}
function compactScene(model) {
  return {themeId: model.themeId, background: model.background, objects: model.objects.map(x => ({object_id: x.object_id, src: x.src, variantId: x.variantId})), extras: model.extras};
}
async function makeProbe(tempDir) {
  const source = `import { buildSceneModel } from ${JSON.stringify(path.join(root, 'frontend/src/v5/visual/scene.ts'))};\nimport { themePackFor } from ${JSON.stringify(path.join(root, 'frontend/src/v5/visual/registry.ts'))};\nexport { buildSceneModel, themePackFor };\nexport function appendFuture(theme, stamp) { const pack=themePackFor(theme); for (const [base, pool] of Object.entries(pack.background_variants ?? {})) pool.push({id:'qa-future-'+base,available_from:stamp,background:{...pack.backgrounds[base],src:'/qa-future-background.png'},slots:pack.slot_layout[base]}); for (const role of ['terminal','cabinet','circuit','panel']) { const variants=pack.objects[role] ?? {}; const old=Object.values(variants)[0]; if (!old) continue; variants['qa-future-default-'+role]={...old,src:'/qa-future-'+role+'-off.png',closeup:'/qa-future-'+role+'-off.png',family:'qa-future-'+role,state:'default',available_from:stamp}; variants['qa-future-completed-'+role]={...old,src:'/qa-future-'+role+'-on.png',closeup:'/qa-future-'+role+'-on.png',family:'qa-future-'+role,state:'completed',available_from:stamp}; } for (const role of ['note','key']) { const variants=pack.objects[role] ?? {}; const old=Object.values(variants)[0]; if (!old) continue; for (const style of (role==='note'?['logbook','sealed-note','star-chart']:[null])) { if(role==='note'&&!Object.values(variants).some(x=>x.note_style===style)) continue; const id='qa-future-'+role+'-'+(style||'key'); variants[id]={...old,src:'/qa-future-'+role+'-'+(style||'key')+'.png',closeup:'/qa-future-'+role+'-'+(style||'key')+'.png',family:'qa-future-'+role+'-'+(style||'key'),state:'default',note_style:style,available_from:stamp}; } } }`;
  const entry = path.join(tempDir, 'scene-probe.cjs');
  const esbuild = createRequire(path.join(root, 'frontend/package.json'))('esbuild');
  await esbuild.build({stdin: {contents: source, resolveDir: root, sourcefile: 'scene-probe.ts'}, outfile: entry, bundle: true, platform: 'node', format: 'cjs', loader: {'.json': 'json'}, logLevel: 'silent'});
  return createRequire(entry)(entry);
}
function createdAllowed(meta, createdAt) { return !meta?.available_from || (Number.isFinite(Date.parse(createdAt)) && Date.parse(meta.available_from) <= Date.parse(createdAt)); }
function expectedMate(pack, role, variant) {
  if (!variant?.family) return null;
  const wanted = variant.state === 'completed' ? 'default' : 'completed';
  return Object.entries(pack.objects[role] ?? {}).find(([, x]) => x.family === variant.family && x.state === wanted)?.[0] ?? null;
}
function sceneInputsForDone(input, role) { return {...input, objects: input.objects.map(x => x.art_id === role ? {...x, completed: true} : x)}; }

async function modelChecks(packs, probe) {
  const referenceTime = '2026-10-30T05:10:23.123456Z';
  const sampleCount = 64;
  for (const [theme, pack] of packs) {
    const display = pack.display_name;
    const bases = Object.keys(pack.backgrounds);
    const baseline = JSON.parse(await fs.readFile(path.join(root, 'output/art-concepts/theme-variation', `${theme}-manifest-base.json`), 'utf8'));
    const sourceSelections = new Map(bases.map(x => [x, new Set()]));
    const stabilityFailures = new Map(bases.map(x => [x, 0]));
    const geometryFailures = new Map(bases.map(x => [x, 0]));
    const pairingFailures = new Map(deviceRoles.map(x => [x, 0]));
    const preloadFailures = new Map(deviceRoles.map(x => [x, 0]));
    const candidateSelections = new Map(deviceRoles.map(x => [x, new Set()]));
    const logbookSelections = new Set();
    const vectors = new Map(Array.from({length: sampleCount}, (_, seed) => [seed, {}]));
    for (const baseId of bases) {
      for (let seed = 0; seed < sampleCount; seed++) {
        const input = sceneInputs(display, `variation-${theme}-${seed}`, referenceTime, baseId);
        const first = probe.buildSceneModel(input), second = probe.buildSceneModel(input);
        sourceSelections.get(baseId).add(first.background.src);
        vectors.get(seed)[baseId] = first.background.src;
        if (JSON.stringify(compactScene(second)) !== JSON.stringify(compactScene(first))) stabilityFailures.set(baseId, stabilityFailures.get(baseId) + 1);
        const backgroundCandidate = (pack.background_variants?.[baseId] ?? []).find(x => (x.background ?? x).src === first.background.src);
        const slots = backgroundCandidate?.slots ?? pack.slot_layout[baseId] ?? [];
        const inputById = new Map(input.objects.map(x => [x.object_id, x]));
        for (const object of first.objects) {
          const source = inputById.get(object.object_id);
          const slot = slots[Math.max(0, Math.min(slots.length - 1, source?.slot ?? 0))];
          const boundsOk = !!slot && object.x === slot.x && object.y === slot.y && object.y <= 1080 && object.y - object.renderHeight >= 0 && object.renderHeight > 0 && object.renderHeight <= slot.height + 0.01 && JSON.stringify(object.hotspot) === JSON.stringify(slot.hotspot);
          if (!boundsOk) geometryFailures.set(baseId, geometryFailures.get(baseId) + 1);
        }
        for (const role of deviceRoles) {
          const obj = first.objects.find(x => x.object_id === `qa-${role}`), meta = pack.objects[role]?.[obj?.variantId];
          if (meta) candidateSelections.get(role).add(meta.family ?? obj.variantId);
          const done = probe.buildSceneModel(sceneInputsForDone(input, role));
          const doneObj = done.objects.find(x => x.object_id === `qa-${role}`), doneMeta = pack.objects[role]?.[doneObj?.variantId];
          if (!meta || !doneMeta || meta.family !== doneMeta.family || meta.state !== 'default' || doneMeta.state !== 'completed') pairingFailures.set(role, pairingFailures.get(role) + 1);
          const mate = expectedMate(pack, role, meta);
          const expectedExtra = mate ? `theme:${mate}` : null;
          const actualExtras = first.extras.filter(x => x.key.startsWith('theme:') && pack.objects[role]?.[x.key.slice(6)]);
          if (expectedExtra ? actualExtras.length !== 1 || actualExtras[0].key !== expectedExtra : actualExtras.length !== 0) preloadFailures.set(role, preloadFailures.get(role) + 1);
        }
        const logbookInput = {...input, objects: input.objects.filter(x => x.art_id === 'note').map(x => ({...x, name: '日常记录本'}))};
        const logbook = probe.buildSceneModel(logbookInput).objects.find(x => x.object_id === 'qa-note');
        const logbookMeta = pack.objects.note?.[logbook?.variantId];
        if (logbookMeta?.note_style === 'logbook') logbookSelections.add(logbook.variantId);
      }
      const bgPool = [pack.backgrounds[baseId], ...(pack.background_variants?.[baseId] ?? []).map(x => x.background ?? x)].filter(Boolean);
      const selected = sourceSelections.get(baseId), expected = new Set(bgPool.map(x => x.src));
      check(`${theme}/${baseId} stable background pool coverage`, {selected: [...selected], stability_failures: stabilityFailures.get(baseId), geometry_failures: geometryFailures.get(baseId)}, {pool: [...expected], stability_failures: 0, geometry_failures: 0}, bgPool.length >= 2 && selected.size === expected.size && [...selected].every(src => expected.has(src)) && stabilityFailures.get(baseId) === 0 && geometryFailures.get(baseId) === 0);
    }
    const distinctVectors = new Set([...vectors.values()].map(vector => JSON.stringify(bases.map(id => vector[id]))));
    check(`${theme} seed sampling produces multiple three-room background vectors`, {seed_count: sampleCount, distinct_vectors: distinctVectors.size}, {minimum_distinct_vectors: 4}, distinctVectors.size >= 4);
    for (const role of deviceRoles) {
      const families = new Set(Object.values(pack.objects[role] ?? {}).filter(x => x.state === 'default').map(x => x.family).filter(Boolean));
      check(`${theme}/${role} selection covers multiple families and pairs`, {selected_families: [...candidateSelections.get(role)], pairing_failures: pairingFailures.get(role), preload_failures: preloadFailures.get(role)}, {families: [...families], pairing_failures: 0, preload_failures: 0}, families.size >= 2 && candidateSelections.get(role).size === families.size && [...candidateSelections.get(role)].every(family => families.has(family)) && pairingFailures.get(role) === 0 && preloadFailures.get(role) === 0);
    }
    const expectedLogbooks = new Set(Object.entries(pack.objects.note ?? {}).filter(([, x]) => x.state === 'default' && x.note_style === 'logbook').map(([id]) => id));
    check(`${theme} seeded logbook variants cover style pool`, [...logbookSelections], [...expectedLogbooks], expectedLogbooks.size >= 2 && logbookSelections.size === expectedLogbooks.size && [...logbookSelections].every(id => expectedLogbooks.has(id)));
    for (const [name, wanted] of [['完整星图', 'star-chart'], ['封存便笺', 'sealed-note'], ['值日记录本', 'logbook']]) {
      const defaults = Object.entries(pack.objects.note ?? {}).filter(([, x]) => x.state === 'default');
      const styles = new Set(defaults.map(([, x]) => x.note_style));
      const expectedStyle = styles.has(wanted) ? wanted : styles.has('logbook') ? 'logbook' : defaults[0]?.[1].note_style;
      const model = probe.buildSceneModel({...sceneInputs(display, `note-style-${theme}`, referenceTime, bases[0], null, name), objects: [{object_id: 'qa-note', name, kind: 'clue', art_id: 'note', slot: 0}]});
      const selected = model.objects[0], selectedMeta = pack.objects.note?.[selected.variantId];
      check(`${theme} note style preference and fallback`, {requested_name: name, selected_style: selectedMeta?.note_style ?? null}, expectedStyle, selectedMeta?.note_style === expectedStyle);
    }
    const beforeZ = '2026-10-30T04:44:56.275999Z';
    const beforeOffset = '2026-10-30T04:44:56.275999+00:00';
    const equalZ = '2026-10-30T04:44:56.276000Z';
    const equalOffset = '2026-10-30T04:44:56.276000+00:00';
    const currentZ = '2026-10-30T05:10:23.123456Z';
    const currentOffset = '2026-10-30T05:10:23.123456+00:00';
    const beforeInput = sceneInputs(display, `compat-${theme}-same`, beforeZ, bases[0]);
    const beforeScene = probe.buildSceneModel(beforeInput);
    const beforeCompact = compactScene(beforeScene);
    const dateEquivalences = [
      [beforeZ, beforeOffset],
      [equalZ, equalOffset],
      [currentZ, currentOffset],
    ].map(([a, b]) => JSON.stringify(compactScene(probe.buildSceneModel({...beforeInput, created_at: a}))) === JSON.stringify(compactScene(probe.buildSceneModel({...beforeInput, created_at: b}))));
    check(`${theme} Python UTC microsecond Z/+00:00 timestamps are equivalent`, dateEquivalences, [true, true, true], dateEquivalences.every(Boolean));
    const missingDate = probe.buildSceneModel({...beforeInput, created_at: undefined});
    const invalidDate = probe.buildSceneModel({...beforeInput, created_at: 'not-a-date'});
    check(`${theme} missing/invalid created_at uses old compatibility pool`, {missing: compactScene(missingDate), invalid: compactScene(invalidDate)}, beforeCompact, JSON.stringify(compactScene(missingDate)) === JSON.stringify(beforeCompact) && JSON.stringify(compactScene(invalidDate)) === JSON.stringify(beforeCompact));
    check(`${theme} old background source matches manifest snapshot`, beforeScene.background.src, baseline.backgrounds[bases[0]].src, beforeScene.background.src === baseline.backgrounds[bases[0]].src);
    const roleByObject = new Map(beforeInput.objects.map(x => [x.object_id, x.art_id]));
    const oldObjectResults = beforeScene.objects.map(object => {
      const role = roleByObject.get(object.object_id);
      const oldVariants = baseline.objects[role] ?? {};
      const old = oldVariants[object.variantId];
      return {object_id: object.object_id, role, variant_id: object.variantId, src: object.src, expected_src: old?.src ?? null, closeup: object.closeup, expected_closeup: old?.closeup ?? null, matches_snapshot: !!old && object.src === old.src && object.closeup === old.closeup};
    });
    check(`${theme} old created_at object art matches baseline snapshots`, oldObjectResults, 'all selected IDs and image paths exist unchanged in old manifest', oldObjectResults.length === beforeInput.objects.length && oldObjectResults.every(x => x.matches_snapshot));
    const oldSceneExtraIds = beforeScene.extras.map(x => x.key.slice(6)).sort();
    const expectedOldMates = deviceRoles.map(role => Object.entries(baseline.objects[role] ?? {}).find(([, variant]) => variant.state === 'completed')?.[0]).filter(Boolean).sort();
    check(`${theme} old created_at preloads only old matching family mates`, oldSceneExtraIds, expectedOldMates, JSON.stringify(oldSceneExtraIds) === JSON.stringify(expectedOldMates));
    const oldGeometry = beforeScene.objects.map(object => {
      const role = roleByObject.get(object.object_id), source = beforeInput.objects.find(x => x.object_id === object.object_id);
      const baseVariant = baseline.objects[role]?.[object.variantId], slot = baseline.slot_layout[bases[0]]?.[source.slot];
      if (!baseVariant || !slot) return {object_id: object.object_id, valid: false};
      const scale = Math.min(slot.height / baseVariant.bbox.height, (slot.hotspot.width * 1.02) / baseVariant.bbox.width);
      const expectedHeight = baseVariant.bbox.height * scale;
      return {object_id: object.object_id, valid: object.x === slot.x && object.y === slot.y && Math.abs(object.renderHeight - expectedHeight) < 0.01 && JSON.stringify(object.hotspot) === JSON.stringify(slot.hotspot) && object.y - object.renderHeight >= 0 && object.y <= 1080};
    });
    check(`${theme} old created_at object placement matches baseline layout`, oldGeometry, 'all old anchors, heights, and hotspots unchanged', oldGeometry.every(x => x.valid));
    const oldBg = pack.background_variants?.[bases[0]]?.find(x => (x.background ?? x).src === beforeScene.background.src);
    check(`${theme} old sample background excludes later variations`, oldBg?.available_from ?? null, `<= ${beforeZ} or legacy`, createdAllowed(oldBg, beforeZ));
    const boundaryInput = {...beforeInput, created_at: equalOffset};
    const boundaryBefore = compactScene(probe.buildSceneModel(boundaryInput));
    probe.appendFuture(display, '2099-01-01T00:00:00.000Z');
    const oldAfterFutureAppend = compactScene(probe.buildSceneModel(beforeInput));
    check(`${theme} future appended variants do not change old sample`, oldAfterFutureAppend, beforeCompact, JSON.stringify(oldAfterFutureAppend) === JSON.stringify(beforeCompact));
    const boundaryAfter = compactScene(probe.buildSceneModel({...beforeInput, created_at: equalZ}));
    check(`${theme} future append does not change exact-cutoff sample`, boundaryAfter, boundaryBefore, JSON.stringify(boundaryAfter) === JSON.stringify(boundaryBefore));
  }
}

async function browserAudit(newAssets, packs, probe) {
  const port = net.createServer();
  await new Promise((resolve, reject) => { port.once('error', reject); port.listen(8002, '127.0.0.1', () => port.close(resolve)); });
  browserTemp = await fs.mkdtemp(path.join(os.tmpdir(), 'campus-visual-theme-variation-'));
  const db = path.join(browserTemp, 'game-v5.sqlite');
  server = spawn('C:/Users/liyh/.conda/envs/1/python.exe', ['-B', '-X', 'utf8', '-m', 'uvicorn', 'tests.v5.theme_variation_fixture_server:app', '--host', '127.0.0.1', '--port', '8002', '--no-access-log'], {cwd: root, env: {...process.env, SQLITE_PATH: db, GAMEPLAY_VERSION: 'v5', AI_PROVIDER: 'mock', PYTHONDONTWRITEBYTECODE: '1'}, stdio: 'ignore', windowsHide: true});
  let ready = false;
  for (let i = 0; i < 100 && !ready; i++) {
    ready = await new Promise(resolve => { const req = http.get({hostname: '127.0.0.1', port: 8002, path: '/health', headers: {host: '127.0.0.1:8001'}}, res => {res.resume(); resolve(res.statusCode === 200);}); req.on('error', () => resolve(false)); req.setTimeout(700, () => req.destroy()); });
    if (!ready) await new Promise(resolve => setTimeout(resolve, 100));
  }
  if (!ready) throw Error('Owned theme variation fixture service failed readiness');
  const {chromium} = createRequire(path.join(root, 'frontend/package.json'))('@playwright/test');
  const browser = await chromium.launch({headless: true, channel: 'chrome'});
  let context, fileContext;
  try {
    context = await browser.newContext({viewport: {width: 1280, height: 720}});
    const base = 'http://127.0.0.1:8001';
    await context.route('**/*', async route => {
      const req = route.request(), url = new URL(req.url());
      if (['data:', 'blob:'].includes(url.protocol)) return route.continue();
      if (url.origin !== base) { externalRequests++; return route.abort(); }
      return route.fetch({url: req.url().replace(base, 'http://127.0.0.1:8002'), headers: {...req.headers(), host: '127.0.0.1:8001'}}).then(response => route.fulfill({response}));
    });
    const page = await context.newPage();
    let visibleState = null;
    page.setDefaultTimeout(15000);
    page.on('response', async response => {
      if (!new URL(response.url()).pathname.includes('/sessions/')) return;
      try { const body = await response.json(); if (body.data?.visible_state) visibleState = body.data.visible_state; } catch {}
    });
    await page.goto(base);
    await page.getByRole('button', {name: '第一次来？注册本地账户', exact: true}).click();
    await page.getByLabel('用户名（3–24位字母、数字或下划线）', {exact: true}).fill(`variation_${runId.slice(0, 8)}`);
    await page.getByLabel('密码（12–128位）', {exact: true}).fill('Synthetic-Variation-only!');
    await page.getByRole('button', {name: '注册并进入', exact: true}).click();
    await page.getByRole('heading', {name: '我的关卡', exact: true}).waitFor();
    await page.getByLabel(/校园主题/).fill('图书馆档案主题变化合成样例');
    await page.getByLabel(/^房间数量/).selectOption('3');
    await page.getByLabel(/^难度/).selectOption('hard');
    await page.getByLabel(/本次生成的 DeepSeek API Key/).fill('SYNTHETIC-ONLY-NOT-A-REAL-KEY');
    const submitted = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname.endsWith('/level-generations'));
    await page.getByRole('button', {name: /^生成关卡/}).click();
    const jobResponse = await submitted, job = (await jobResponse.json()).data?.job;
    if (!job?.job_id) throw Error('Synthetic variation job was not accepted');
    check('browser synthetic job accepted', {status: job.status}, 'accepted', true, 'browser');
    let serviceJob = null;
    for (let i = 0; i < 80; i++) {
      serviceJob = await page.evaluate(async id => { const response = await fetch(`/api/v2/level-generations/${encodeURIComponent(id)}`); if (!response.ok) return {http_status: response.status}; const body = await response.json(); const item = body.data?.job; return item ? {job_id: item.job_id, status: item.status, error_code: item.error_code ?? null} : null; }, job.job_id);
      if (serviceJob?.status === 'ready' || serviceJob?.status === 'failed' || serviceJob?.status === 'unknown') break;
      await new Promise(resolve => setTimeout(resolve, 250));
    }
    check('browser synthetic job public status', serviceJob, {status: 'ready', error_code: null}, serviceJob?.status === 'ready' && serviceJob?.job_id === job.job_id, 'browser');
    if (serviceJob?.status !== 'ready') throw Error(`Synthetic variation job status ${serviceJob?.status || 'unavailable'}${serviceJob?.error_code ? ` / ${serviceJob.error_code}` : ''}`);
    const levelsResponse = page.waitForResponse(r => r.request().method() === 'GET' && new URL(r.url()).pathname.endsWith('/levels'));
    await page.getByRole('button', {name: '刷新列表', exact: true}).click();
    await levelsResponse;
    const card = page.locator('.v5-level-card').filter({hasText: '图书馆档案'}).first();
    await card.waitFor();
    await card.getByRole('button', {name: /探索/}).click();
    await page.locator('.v5-hotspots button:enabled').first().waitFor();
    await page.waitForFunction(() => document.querySelector('.v5-scene')?.dataset.loadingTextures === 'false', null, {timeout: 20000});
    const readScene = () => page.locator('.v5-scene').evaluate(el => ({theme: el.dataset.theme, background: el.dataset.background, missing: Number(el.dataset.missingTextures), loading: el.dataset.loadingTextures, textures: (el.dataset.textures || '').split(/\s+/).filter(Boolean), variants: [...el.querySelectorAll('.v5-hotspots button[data-object]')].map(x => ({id: x.dataset.object, variant: x.dataset.variant}))}));
    const scene = await readScene();
    const expectedPaths = new Set(newAssets.map(x => x.metadata.src));
    const variantSources = new Map();
    for (const [, pack] of packs) for (const [role, variants] of Object.entries(pack.objects ?? {})) for (const [id, variant] of Object.entries(variants)) variantSources.set(id, {role, src: variant.src});
    const selectedNew = [
      ...(expectedPaths.has(scene.background) ? [{role: 'background', variant: null, src: scene.background}] : []),
      ...scene.variants.map(x => ({...x, ...(variantSources.get(x.variant) ?? {})})).filter(x => expectedPaths.has(x.src)),
    ];
    const unmappedVariants = scene.variants.filter(x => !variantSources.has(x.variant));
    check('browser current scene theme and texture queue', {...scene, selected_new_resources: selectedNew, unmapped_variants: unmappedVariants}, {theme: 'library-archive', missing: 0, loading: 'false', all_variants_mapped: true}, scene.theme === 'library-archive' && scene.missing === 0 && scene.loading === 'false' && unmappedVariants.length === 0, 'browser');
    await page.screenshot({path: path.join(out, 'game-ui-1280x720.png')});
    screenshots.push('game-ui-1280x720.png');
    await page.setViewportSize({width: 1920, height: 1080});
    await new Promise(resolve => setTimeout(resolve, 150));
    const wideScene = await readScene();
    check('browser 1920x1080 retains fully loaded scene', {theme: wideScene.theme, background: wideScene.background, missing: wideScene.missing, loading: wideScene.loading}, {theme: 'library-archive', missing: 0, loading: 'false'}, wideScene.theme === 'library-archive' && wideScene.missing === 0 && wideScene.loading === 'false', 'browser');
    await page.screenshot({path: path.join(out, 'game-ui-1920x1080.png')});
    screenshots.push('game-ui-1920x1080.png');
    await page.reload();
    await page.getByRole('heading', {name: '我的关卡', exact: true}).waitFor();
    const resumedCard = page.locator('.v5-level-card').filter({hasText: '图书馆档案'}).first();
    await resumedCard.getByRole('button', {name: /探索/}).click();
    await page.locator('.v5-hotspots button:enabled').first().waitFor();
    await page.waitForFunction(() => document.querySelector('.v5-scene')?.dataset.loadingTextures === 'false', null, {timeout: 20000});
    const reloadedScene = await readScene();
    check('browser reload preserves variation selection', reloadedScene, wideScene, JSON.stringify(reloadedScene) === JSON.stringify(wideScene), 'browser');

    await page.goto(`${base}/art-themes/campus-theme-library.html`);
    await page.locator('main').waitFor();
    const gallery = await page.locator('img').evaluateAll(async images => { for (const image of images) image.loading = 'eager'; await Promise.all(images.map(image => image.decode().catch(() => null))); return images.map(image => ({src: new URL(image.src).pathname, complete: image.complete, width: image.naturalWidth, height: image.naturalHeight})); });
    const galleryPaths = new Set(gallery.map(x => x.src));
    const missingNewImages = [...expectedPaths].filter(src => !galleryPaths.has(src));
    const distinctGallerySources = galleryPaths.size;
    const galleryOk = gallery.length === 86 && distinctGallerySources === 74 && gallery.every(x => x.complete && x.width > 0 && x.height > 0) && missingNewImages.length === 0;
    check('HTTP gallery shows original/new images without missing sources', {img_elements: gallery.length, distinct_sources: distinctGallerySources, loaded: gallery.filter(x => x.complete && x.width > 0 && x.height > 0).length, missing_new_paths: missingNewImages}, {img_elements: 86, distinct_sources: 74, new_sources_present: expectedPaths.size}, galleryOk, 'browser-gallery-http');
    const libraryPack = packs.find(([theme]) => theme === 'library-archive')[1];
    const selectedBackground = newAssets.find(x => x.kind === 'background');
    const terminalDefault = Object.entries(libraryPack.objects.terminal).find(([, x]) => x.available_from && x.state === 'default');
    const terminalMate = terminalDefault && Object.entries(libraryPack.objects.terminal).find(([, x]) => x.family === terminalDefault[1].family && x.state === 'completed');
    for (const [label, asset] of [['new-background', selectedBackground], ['terminal-default', terminalDefault && {metadata: terminalDefault[1]}], ['terminal-completed', terminalMate && {metadata: terminalMate[1]}]]) {
      const src = asset?.metadata?.src;
      const index = src ? await page.locator('img').evaluateAll((imgs, wanted) => imgs.findIndex(img => new URL(img.src).pathname === wanted), src) : -1;
      const image = index >= 0 ? page.locator('img').nth(index) : null;
      const loaded = !!image && await image.evaluate(img => img.complete && img.naturalWidth > 0 && img.naturalHeight > 0);
      check(`gallery representative ${label} visible`, {src, loaded}, 'loaded image from expected family', loaded, 'browser-gallery-http');
      if (loaded) { await image.screenshot({path: path.join(out, `gallery-${label}.png`)}); screenshots.push(`gallery-${label}.png`); }
    }

    const probeTheme = libraryPack.display_name;
    let previewPair = null;
    for (let seed = 0; seed < 256 && !previewPair; seed++) {
      const input = sceneInputs(probeTheme, `probe-library-${seed}`, '2026-10-30T05:10:23.123456Z', 'neutral_lab');
      const initial = probe.buildSceneModel(input);
      const term = initial.objects.find(x => x.object_id === 'qa-terminal');
      const terminalMeta = libraryPack.objects.terminal[term?.variantId];
      const backgroundMeta = (libraryPack.background_variants.neutral_lab ?? []).find(x => (x.background ?? x).src === initial.background.src);
      if (!terminalMeta?.available_from || !backgroundMeta?.available_from || !terminalMeta.family) continue;
      const completed = probe.buildSceneModel(sceneInputsForDone(input, 'terminal'));
      const completedTerm = completed.objects.find(x => x.object_id === 'qa-terminal');
      const completedMeta = libraryPack.objects.terminal[completedTerm?.variantId];
      if (completedMeta?.family === terminalMeta.family && completedMeta.state === 'completed') previewPair = {seed, input, initial, completed, terminalMeta, completedMeta, backgroundMeta, terminalVariantId: term.variantId, completedTerminalVariantId: completedTerm.variantId};
    }
    check('model probe finds new background and new paired device sample', previewPair ? {seed: previewPair.seed, background: previewPair.initial.background.src, terminal_default: previewPair.terminalVariantId, family: previewPair.terminalMeta.family, terminal_completed: previewPair.completedTerminalVariantId} : null, 'new dated background + same-family new terminal default/completed', !!previewPair, 'model-probe');
    if (previewPair) {
      const renderProbe = async (model, terminalState, filename, width, height) => {
        const deviceObjects = model.objects.map(object => {
          const sourceInput = previewPair.input.objects.find(x => x.object_id === object.object_id);
          const role = sourceInput?.art_id;
          const meta = libraryPack.objects[role]?.[object.variantId];
          if (!meta) return '';
          const scale = object.renderHeight / object.bbox.height;
          return `<div class="object" style="left:${object.x}px;top:${object.y}px;width:${object.bbox.width * scale}px;height:${object.renderHeight}px"><img src="${meta.src}" style="left:${-object.bbox.x * scale}px;top:${-object.bbox.y * scale}px;width:${meta.width * scale}px;height:${meta.height * scale}px"><span>${object.name}</span></div>`;
        }).join('');
        await page.setViewportSize({width, height});
        await page.setContent(`<!doctype html><meta charset="utf-8"><style>*{box-sizing:border-box}body{margin:0;background:#081116;color:#fff;font:18px system-ui;overflow:hidden}.frame{position:absolute;width:1600px;height:900px;left:50%;top:50%;transform:translate(-50%,-50%) scale(${Math.min(width / 1600, height / 900)});transform-origin:center;background:#14242b;overflow:hidden}.bg{position:absolute;inset:0;width:1600px;height:900px}.object{position:absolute;transform:translate(-50%,-100%);overflow:visible;filter:drop-shadow(0 8px 10px #0009)}.object img{position:absolute;max-width:none}.object span{position:absolute;left:50%;top:100%;transform:translate(-50%,0);padding:4px 9px;border-radius:5px;background:#182d27dd;color:#f3e5c7;white-space:nowrap;font-size:16px}.tag{position:fixed;left:16px;top:16px;padding:8px 12px;background:#081116dd;border:1px solid #d4b979;border-radius:5px;z-index:2}</style><div class="tag">模型探针预览 · Synthetic · ${terminalState}</div><div class="frame"><img class="bg" src="${model.background.src}">${deviceObjects}</div>`);
        const loaded = await page.locator('.frame img').evaluateAll(imgs => imgs.map(x => ({src: new URL(x.src).pathname, loaded: x.complete && x.naturalWidth > 0 && x.naturalHeight > 0})));
        const ok = loaded.length === model.objects.length + 1 && loaded.every(x => x.loaded);
        check(`model probe ${terminalState} actual image loads`, {image_count: loaded.length, loaded: loaded.filter(x => x.loaded).length, background: loaded[0]?.src}, {all_loaded: true}, ok, 'model-probe');
        if (ok) { await page.screenshot({path: path.join(out, filename)}); screenshots.push(filename); }
      };
      await renderProbe(previewPair.initial, 'default', 'model-probe-1280x720-default.png', 1280, 720);
      await renderProbe(previewPair.completed, 'same-family-completed', 'model-probe-1920x1080-completed.png', 1920, 1080);
    }

    fileContext = await browser.newContext({viewport: {width: 1280, height: 720}});
    const filePage = await fileContext.newPage();
    const fileHttpRequests = [], fileApiRequests = [];
    filePage.on('request', request => { const u = request.url(); if (/^https?:/i.test(u)) { const parsed = new URL(u); fileHttpRequests.push({method: request.method(), path: parsed.pathname}); if (/\/api(?:\/|$)/i.test(parsed.pathname) || request.method() !== 'GET') fileApiRequests.push({method: request.method(), path: parsed.pathname}); } });
    const rootFile = pathToFileURL(path.join(root, '美术图集.html')).href;
    await filePage.goto(rootFile, {waitUntil: 'domcontentloaded', timeout: 30000});
    await filePage.locator('main').waitFor({timeout: 20000});
    const fileGallery = await filePage.locator('img').evaluateAll(async images => { for (const image of images) image.loading = 'eager'; await Promise.all(images.map(image => image.decode().catch(() => null))); return images.map(image => ({src: new URL(image.src).pathname, complete: image.complete, width: image.naturalWidth, height: image.naturalHeight})); });
    await filePage.screenshot({path: path.join(out, 'root-file-gallery.png')});
    screenshots.push('root-file-gallery.png');
    const fileDistinct = new Set(fileGallery.map(x => x.src)).size;
    const fileOk = filePage.url().startsWith('file:') && filePage.url().endsWith('/frontend/public/art-themes/campus-theme-library.html') && fileGallery.length === 86 && fileDistinct === 74 && fileGallery.every(x => x.complete && x.width > 0 && x.height > 0) && fileHttpRequests.length === 0 && fileApiRequests.length === 0;
    check('root file HTML redirects locally and loads gallery without HTTP', {actual_url: filePage.url(), img_elements: fileGallery.length, distinct_sources: fileDistinct, loaded: fileGallery.filter(x => x.complete && x.width > 0 && x.height > 0).length, http_requests: fileHttpRequests.length, api_or_post: fileApiRequests.length}, {local_file_canonical: true, img_elements: 86, distinct_sources: 74, all_loaded: true, http_requests: 0, api_or_post: 0}, fileOk, 'browser-gallery-file');
    check('no external requests outside local app fixture', externalRequests, 0, externalRequests === 0, 'browser');
  } finally {
    try { await context?.unrouteAll({behavior: 'ignoreErrors'}); } catch {}
    try { await context?.close(); } catch {}
    try { await fileContext?.close(); } catch {}
    try { await browser.close(); } catch {}
  }
}

async function main() {
  await fs.mkdir(out, {recursive: true});
  if (process.env.THEME_VARIATION_FORMAL === '1') await fs.writeFile(path.join(out, 'records.jsonl'), '', {flag: 'wx'});
  const packs = await readPacks();
  const assets = await staticAudit(packs);
  const temp = await fs.mkdtemp(path.join(os.tmpdir(), 'campus-visual-theme-variation-'));
  const probe = await makeProbe(temp);
  await modelChecks(packs, probe);
  if (process.env.THEME_VARIATION_FORMAL === '1') await browserAudit(assets, packs, probe);
}

let exit = 0;
try { await main(); }
catch (error) { issues.push({type: error?.constructor?.name || 'Error', message: String(error?.message || 'unknown').split('\n')[0].slice(0, 180)}); exit = 1; }
finally {
  if (server) serverStopped = await new Promise(resolve => {
    if (server.exitCode !== null || server.signalCode !== null) return resolve(true);
    server.once('close', () => resolve(true));
    server.kill();
    setTimeout(() => resolve(false), 4000);
  });
  exit = exit || (records.some(x => !x.pass) || !serverStopped ? 1 : 0);
  const result = {run_id: runId, command: 'node tests/v5/run_theme_variation_browser.mjs', formal: process.env.THEME_VARIATION_FORMAL === '1', started_at_utc: started, finished_at_utc: new Date().toISOString(), scope: '31-art metadata/pixel/layout audit, bounded buildSceneModel variation/date matrix, one representative Synthetic UI scene and variation gallery', browser_TEMP: browserTemp ? path.basename(browserTemp) : null, server_port: 8002, server_stopped: serverStopped, external_requests: externalRequests, screenshots, records, issues, paid_calls: 0, real_model_calls: 0, player_database_access: false, exit_code: exit};
  // Formal runs use this unique output path; preparation itself does not create a result record.
  if (process.env.THEME_VARIATION_FORMAL === '1') {
    await fs.mkdir(out, {recursive: true});
    await fs.writeFile(path.join(out, 'result.json'), JSON.stringify(result, null, 2) + '\n', {flag: 'wx'});
  }
  process.exitCode = exit;
}
