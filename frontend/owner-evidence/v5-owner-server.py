from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from backend.app.api.v5 import create_v5_application
from backend.app.domain.generated import make_fixture
class FixtureService:
    async def generate(self,**kwargs):
        return make_fixture(kwargs['room_count'],kwargs['difficulty'])
app=create_v5_application(Path(__file__).parent/'v5-runtime'/'owner-isolated.sqlite',generation_service=FixtureService(),dev=True)
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8001,log_level='warning')
