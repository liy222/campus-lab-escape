"""Synthetic experience fixture, never a production generator or player store."""
import os
from pathlib import Path
import tempfile

db = Path(os.environ['SQLITE_PATH']).resolve()
if db.name != 'game-v5.sqlite' or not db.is_relative_to(Path(tempfile.gettempdir()).resolve()) or not db.parent.name.startswith('campus-experience-') or (db.exists() and os.environ.get('EXPERIENCE_REUSE_TEMP') != '1'):
    raise RuntimeError('Fresh owned TEMP database required')
os.environ.update(GAMEPLAY_VERSION='v5', AI_PROVIDER='mock')
from backend.app.domain.generated import make_fixture
from backend.app.main import create_v5_app


class SyntheticGenerator:
    async def generate(self, *, theme, room_count, difficulty, **kwargs):
        assert (room_count, difficulty) == (1, 'hard')
        draft = make_fixture(room_count, difficulty)
        # Keep the original two code combinations and four-puzzle chain, but put
        # circuit first so this focused UI check need not replay unrelated codes.
        first, third = draft['puzzles'][0], draft['puzzles'][2]
        first['mechanism'] = 'circuit'
        first.pop('recipe'); first.pop('clue_ids')
        third.update(mechanism='code', recipe='index', clue_ids=['fact_source', 'fact_order'])
        draft['title'] = 'Synthetic · 雨夜天文社'
        draft['story'] = 'Synthetic：雨夜的天文社旧活动室里，封存的观测记录等待查阅。'
        room = draft['rooms'][0]
        room.update(name='天文社旧活动室', description='Synthetic：雨水敲着旧窗，观测记录摆在桌边。')
        for obj in room['objects']:
            if obj.get('puzzle_id') == first['puzzle_id']:
                obj.update(name='观测台配电线路', art_id='circuit')
            if obj.get('puzzle_id') == third['puzzle_id']:
                obj['art_id'] = 'terminal'
        return draft


app = create_v5_app(db, generation_service=SyntheticGenerator())


@app.middleware('http')
async def fixture_identity(request, call_next):
    response = await call_next(request)
    response.headers['X-QA-Synthetic-Experience'] = 'owned-temp-only'
    return response
