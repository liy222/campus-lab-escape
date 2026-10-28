"""Explicit-file evidence archive and separately sourced human review records.

Collection is a copy/import, never a test execution or a human acceptance.
The caller supplies truthful human text/reference and user-provided screenshots.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import uuid

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HUB_ROOT = PROJECT_ROOT / 'evidence/project'
CATEGORIES = ('automated', 'logs', 'evaluation', 'reviews', 'screenshots')
DECISIONS = ('accepted', 'changes-requested', 'undecided')
IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
TEXT_SUFFIXES = {'.json', '.jsonl', '.md', '.txt', '.log', '.csv', '.tsv', '.html', '.svg'}
SAFE_SUFFIXES = TEXT_SUFFIXES | IMAGE_SUFFIXES | {'.pdf'}
PRIVATE_KEYS = {'password', 'api_key', 'apikey', 'authorization', 'cookie', 'session_token',
                'definition_json', 'private_definition', 'private_dump', 'answers',
                'witness', 'parameters', 'draft', 'choices'}


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def slug(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}', value):
        raise ValueError('stage must be a lowercase safe slug')
    return value


def relative_name(value):
    value = str(value).replace('\\', '/')
    if not value or PureWindowsPath(value).is_absolute() or ':' in value or value.startswith('/'):
        raise ValueError('name must be a safe relative file path')
    parts = value.split('/')
    for part in parts:
        if (part in {'', '.', '..'} or part[-1:] in {' ', '.'}
                or re.search(r'[<>:"|?*\x00-\x1f]', part)
                or re.fullmatch(r'(?i)(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part)):
            raise ValueError('unsafe relative file path')
    return Path(*parts)


def inside(base, relative):
    target = base / relative_name(relative)
    try: target.resolve().relative_to(base.resolve())
    except ValueError: raise ValueError('destination escapes evidence directory') from None
    return target


def _root():
    if any(path.is_symlink() for path in (HUB_ROOT, *HUB_ROOT.parents)):
        raise ValueError('evidence root cannot traverse symlinks')
    return HUB_ROOT


def _read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _write_json(path, value, *, new=False):
    text = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if new:
        with path.open('x', encoding='utf-8', newline='\n') as stream: stream.write(text)
    else:
        temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
        with temporary.open('x', encoding='utf-8', newline='\n') as stream: stream.write(text)
        temporary.replace(path)


def _stage(stage):
    stage = slug(stage)
    directory = inside(_root(), 'stages/' + stage)
    metadata = _read_json(inside(directory, 'stage.json'))
    if metadata.get('stage') != stage: raise ValueError('stage metadata mismatch')
    return directory, metadata


def _round_directory(stage, number):
    if type(number) is not int or not 1 <= number <= 999: raise ValueError('round must be 1..999')
    return inside(_root(), f'human-reviews/{slug(stage)}/round-{number:02d}')


def _pending_review(stage, number):
    return (f'# 真人核验：{stage} / round-{number:02d}\n\n'
            '本人：未核验。\n\n同伴：未核验。\n\n'
            '- [ ] 本人实际体验并提供反馈或明确结论\n'
            '- [ ] 记录原消息或人工来源\n'
            '- [ ] 如有截图，确认由用户明确提供\n\n'
            '技术检查通过、导入截图或创建此表均不代表真人接受。\n')


def init_stage(stage, title, *, activate=False):
    stage = slug(stage)
    if not isinstance(title, str) or not title.strip(): raise ValueError('title is required')
    root = _root()
    directory = inside(root, 'stages/' + stage)
    human = _round_directory(stage, 1)
    if directory.exists() or human.exists(): raise FileExistsError('stage already exists')
    index_path = inside(root, 'index.json')
    index = _read_json(index_path) if index_path.exists() else {'active_stage': None, 'stages': []}
    if any(item['stage'] == stage for item in index['stages']): raise FileExistsError('stage already indexed')
    directory.mkdir(parents=True, exist_ok=False)
    for category in CATEGORIES: (directory / category).mkdir()
    (human / 'screenshots').mkdir(parents=True, exist_ok=False)
    (human / 'review.md').write_text(_pending_review(stage, 1), encoding='utf-8', newline='\n')
    metadata = {'schema_version': 1, 'stage': stage, 'title': title.strip(), 'created_at': utc_now(),
        'technical_status': 'not_recorded', 'human_review_status': 'not_reviewed',
        'owner_review_status': 'not_reviewed', 'peer_review_status': 'not_reviewed',
        'current_human_review_round': 1, 'human_review_rounds': {}, 'collections': []}
    _write_json(directory / 'stage.json', metadata, new=True)
    index['stages'].append({'stage': stage, 'title': title.strip(),
        'stage_metadata': f'stages/{stage}/stage.json',
        'human_review': f'human-reviews/{stage}/round-01/review.md'})
    if activate: index['active_stage'] = stage
    _write_json(index_path, index, new=not index_path.exists())
    return metadata


def _sensitive_json(value):
    if isinstance(value, dict):
        return any(str(key).lower().replace('-', '_') in PRIVATE_KEYS or _sensitive_json(item)
                   for key, item in value.items())
    if isinstance(value, list): return any(_sensitive_json(item) for item in value)
    return False


def safe_file(source):
    source = Path(source).resolve(strict=True)
    if not source.is_file(): raise ValueError('source must be one explicit regular file')
    lowered = str(source).lower().replace('\\', '/')
    parts = source.parts
    if (any(part.lower().startswith('.env') for part in parts)
            or re.search(r'(?:raw[-_]sensitive|private|definition|witness|provider[-_](?:raw|result|response)|(?:raw|private)[-_]provider)', lowered)
            or any(part.lower() in {'node_modules', '.venv', 'venv', 'env', 'envs', '.conda', '.aws'} for part in parts)
            or source.suffix.lower() not in SAFE_SUFFIXES):
        raise ValueError('sensitive or unsupported source file')
    payload = source.read_bytes()
    if payload.startswith(b'SQLite format 3\x00'): raise ValueError('database files cannot be collected')
    if source.suffix.lower() in TEXT_SUFFIXES:
        text = payload.decode('utf-8-sig')
        if re.search(r'(?i)\bsk-[a-z0-9_-]{12,}|\bbearer\s+[a-z0-9_.-]{12,}', text):
            raise ValueError('credential-like content cannot be collected')
        if source.suffix.lower() in {'.json', '.jsonl'}:
            values = [json.loads(line) for line in text.splitlines() if line.strip()] if source.suffix.lower() == '.jsonl' else [json.loads(text)]
            if any(_sensitive_json(value) for value in values): raise ValueError('private JSON content cannot be collected')
    return source, payload


def _copy(source, payload, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream: stream.write(payload)
    return {'source_path': str(source), 'archive_path': destination.relative_to(_root()).as_posix(),
            'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload), 'collected_at': utc_now()}


def collect(stage, category, source, *, name=None):
    if category not in CATEGORIES: raise ValueError('unknown category')
    directory, metadata = _stage(stage)
    source, payload = safe_file(source)
    destination = inside(inside(directory, category), name if name is not None else source.name)
    entry = _copy(source, payload, destination)
    entry.update(category=category, new_execution=False)
    metadata['collections'].append(entry)
    _write_json(directory / 'stage.json', metadata)
    return entry


def _user_screenshot(source):
    source, payload = safe_file(source)
    if source.suffix.lower() not in IMAGE_SUFFIXES: raise ValueError('screenshot must be an image supplied by the user')
    known_image = (payload.startswith(b'\x89PNG\r\n\x1a\n') or payload.startswith(b'\xff\xd8\xff')
                   or payload.startswith((b'GIF87a', b'GIF89a'))
                   or payload.startswith(b'RIFF') and payload[8:12] == b'WEBP')
    if not known_image: raise ValueError('unrecognized screenshot image')
    try: source.relative_to((_root() / 'stages').resolve())
    except ValueError: pass
    else: raise ValueError('automated stage screenshots cannot be imported as human screenshots')
    if any(part.lower() in {'automated', 'qa', 'playwright', 'browser'} for part in source.parts):
        raise ValueError('automated screenshots cannot be imported as human screenshots')
    return source, payload


def _review_markdown(stage, number, events, states):
    lines = [f'# 真人核验：{stage} / round-{number:02d}', '',
             '本人结论：' + states['owner'], '', '同伴结论：' + states['peer'], '',
             '以下时间是导入时间；未提供的原核验时间为空。技术结果不替代真人结论。', '']
    for event in events:
        lines.extend([f"## {event['imported_at']} / {event['reviewer']} / {event['decision']}", '',
                      '核验方式：' + event['mode'], '', '人工来源：' + event['reference'], '',
                      '原核验时间：未提供', '', event['text'], ''])
        for screenshot in event['screenshots']:
            name = Path(screenshot['archive_path']).name
            lines.extend([f'用户提供截图：[{name}](<screenshots/{name}>)', ''])
    return '\n'.join(lines)


def record_review(stage, *, reviewer, mode, decision, text, reference, round_number=1, screenshots=()):
    if reviewer not in {'owner', 'peer'} or mode not in {'executed', 'read-existing'} or decision not in DECISIONS:
        raise ValueError('invalid reviewer, mode or decision')
    if not isinstance(text, str) or not text.strip() or not isinstance(reference, str) or not reference.strip():
        raise ValueError('actual feedback and its human source are required')
    directory, metadata = _stage(stage)
    human = _round_directory(stage, round_number)
    prepared = [_user_screenshot(source) for source in screenshots]
    human.mkdir(parents=True, exist_ok=True)
    screenshot_directory = inside(human, 'screenshots')
    screenshot_directory.mkdir(exist_ok=True)
    log = inside(human, 'events.jsonl')
    events = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines() if line.strip()] if log.exists() else []
    event = {'event_id': uuid.uuid4().hex, 'stage': stage, 'round': round_number,
             'reviewer': reviewer, 'mode': mode, 'decision': decision, 'text': text,
             'reference': reference, 'imported_at': utc_now(), 'reviewed_at': None,
             'screenshots': []}
    for index, (source, payload) in enumerate(prepared, 1):
        destination = inside(screenshot_directory, f"{event['event_id']}-{index:02d}-" + source.name)
        entry = _copy(source, payload, destination)
        entry['origin'] = 'user-provided'
        event['screenshots'].append(entry)
    with log.open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + '\n')
    events.append(event)
    states = {'owner': 'not_reviewed', 'peer': 'not_reviewed'}
    for item in events: states[item['reviewer']] = item['decision']
    inside(human, 'review.md').write_text(_review_markdown(stage, round_number, events, states), encoding='utf-8', newline='\n')
    metadata['human_review_rounds'][str(round_number)] = states
    current = max(int(number) for number in metadata['human_review_rounds'])
    metadata['current_human_review_round'] = current
    latest = metadata['human_review_rounds'][str(current)]
    metadata['owner_review_status'], metadata['peer_review_status'] = latest['owner'], latest['peer']
    metadata['human_review_status'] = latest['owner']
    _write_json(directory / 'stage.json', metadata)
    index_path = inside(_root(), 'index.json')
    index = _read_json(index_path)
    for item in index['stages']:
        if item['stage'] == stage:
            item['human_review'] = f'human-reviews/{stage}/round-{current:02d}/review.md'
    _write_json(index_path, index)
    return event


def main(argv=None):
    parser = argparse.ArgumentParser(description='固定证据目录：显式文件归档与有来源的真人反馈。采集不代表新执行或人工接受。')
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init')
    init.add_argument('--stage', required=True); init.add_argument('--title', required=True)
    init.add_argument('--activate', action='store_true')
    copy = commands.add_parser('collect')
    copy.add_argument('--stage', required=True); copy.add_argument('--category', choices=CATEGORIES, required=True)
    copy.add_argument('--source', type=Path, required=True); copy.add_argument('--name')
    review = commands.add_parser('record-review', description='仅导入真实人工反馈；--screenshot必须是明确由用户提供的图。')
    review.add_argument('--stage', required=True); review.add_argument('--round', type=int, default=1)
    review.add_argument('--reviewer', choices=('owner', 'peer'), required=True)
    review.add_argument('--mode', choices=('executed', 'read-existing'), required=True)
    review.add_argument('--decision', choices=DECISIONS, required=True)
    review.add_argument('--text', required=True); review.add_argument('--reference', required=True)
    review.add_argument('--screenshot', type=Path, action='append', default=[])
    args = parser.parse_args(argv)
    try:
        if args.command == 'init': result = init_stage(args.stage, args.title, activate=args.activate)
        elif args.command == 'collect': result = collect(args.stage, args.category, args.source, name=args.name)
        else: result = record_review(args.stage, reviewer=args.reviewer, mode=args.mode, decision=args.decision,
                                    text=args.text, reference=args.reference, round_number=args.round, screenshots=args.screenshot)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f'evidence hub: {type(error).__name__}: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
