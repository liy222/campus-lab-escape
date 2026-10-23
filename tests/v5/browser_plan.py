"""Private route planner consumed in memory by the QA browser harness only."""
import json
from backend.app.domain.generated import make_fixture,compile_level
draft=make_fixture(3,'hard')
compiled=compile_level(draft,3,'hard')
print(json.dumps({'draft':draft,'witness':compiled.witness},ensure_ascii=False))
