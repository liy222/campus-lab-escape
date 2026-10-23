"""QA-only browser server. No fixture HTTP routes or network/model fallback.

Launch only with TEMP/.../game-v5.sqlite. The injected synthetic generator is
explicitly different from real provider acceptance; all other API/UI is real.
"""
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
db=Path(os.environ.get('SQLITE_PATH','')).resolve()
if db.name!='game-v5.sqlite' or not db.is_relative_to(Path(tempfile.gettempdir()).resolve()):
    raise RuntimeError('QA browser requires a fresh TEMP game-v5.sqlite')
os.environ['GAMEPLAY_VERSION']='v5'; os.environ['AI_PROVIDER']='mock'
from backend.app.main import create_v5_app
from backend.app.domain.generated import make_fixture

class SyntheticGenerator:
    async def generate(self, *,theme,room_count,difficulty,api_key,draft_schema):
        return make_fixture(room_count,difficulty)

app=create_v5_app(db,generation_service=SyntheticGenerator())
