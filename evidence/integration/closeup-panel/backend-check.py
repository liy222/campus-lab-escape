"""Backend development checks only. Reuses existing isolated QA fixtures; no formal acceptance."""
from contextlib import closing
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tests.api.test_upgrade_v34 import UpgradeV34Acceptance
from tests.api.test_upgrade_v33 import UpgradeV33Acceptance, derive_public_sequence

records=[]
fixed_ids=['cooling','lighting','safety','ventilation']
def panel(state):return next(obj for obj in state['objects'] if obj['object_id']=='r3_panel')
def can_submit(state):return any(action['tool']=='submit_sequence' for action in panel(state)['actions'])

class EarlyV34(UpgradeV34Acceptance):
    def before_strip(self):
        self.route32(end=22);self.finish_circuit();self.route32(23,39)
        state=self.state();self.assertEqual(state['puzzle_states']['panel'],'EMPTY');self.assertIsNone(state['minigames']['sequence']);return state

    def assert_early(self,state,stage):
        self.assertEqual(state['device_states']['exit'],stage)
        self.assertEqual(state['puzzle_states']['panel'],'STRIP_INSERTED')
        sequence=state['minigames']['sequence'];self.assertIsNotNone(sequence)
        self.assertEqual(set(sequence),{'target_id','devices','length','status'})
        self.assertEqual(sequence['target_id'],'r3_panel');self.assertEqual(sequence['length'],4);self.assertEqual(sequence['status'],'editing')
        self.assertEqual([device['device_id'] for device in sequence['devices']],fixed_ids)
        self.assertTrue(all(set(device)=={'device_id','label','symbol'} for device in sequence['devices']))
        self.assertFalse(can_submit(state));self.assertFalse(state['progress']['check_done'])
        self.reject_unchanged('submit_sequence',{'target_id':'r3_panel','device_ids':fixed_ids},'PRECONDITION_FAILED')

    def test_v34_earlier_graphics_preserve_exit_stage_guards_and_win(self):
        self.before_strip()
        self.route32(39,40);self.assert_early(self.state(),'LOCKED')
        self.route32(40,41);self.assert_early(self.state(),'CARD_ACCEPTED')
        self.route32(41,42);ready=self.state();self.assertTrue(can_submit(ready));self.assertEqual(ready['device_states']['exit'],'FINAL_CHECK')
        self.action('submit_sequence',{'target_id':'r3_panel','device_ids':derive_public_sequence(ready)})
        completed=self.state();self.assertTrue(completed['progress']['check_done']);self.assertEqual(completed['minigames']['sequence']['status'],'completed');self.assertFalse(can_submit(completed))
        self.reject_unchanged('submit_sequence',{'target_id':'r3_panel','device_ids':fixed_ids},'PRECONDITION_FAILED')
        self.route32(43);self.assertEqual(self.state()['status'],'won');self.assertEqual(self.state()['room']['room_id'],'EXIT')
        records.append({'check':'v3.4 strips expose graphics at LOCKED and CARD_ACCEPTED; only FINAL_CHECK submits; full route won','result':'passed'})

    def test_v34_save_archive_restore_reopen_and_replay_reproject_without_snapshot_migration(self):
        self.before_strip();before_strip_saved=self.control('save')
        request=self.request('use_item',{'item_id':'research_strip','target_id':'r3_panel'})
        status,first=self.post(request);self.assertEqual(status,200);early=first['data']['visible_state'];self.assert_early(early,'LOCKED')
        saved=self.control('save')
        version=self.version()
        status,archive=self.exchange('POST',f"/api/sessions/{self.session['session_id']}/saves",headers=self.headers(),json={**version,'name':'backend owner pre-card'},definition='save_slot_response')
        self.assertEqual(status,201);save_id=archive['data']['slot']['save_id']
        with closing(sqlite3.connect(self.db)) as db:
            raw_slot=db.execute('SELECT snapshot_json FROM save_slots WHERE save_id=?',(save_id,)).fetchone()[0]
            raw_legacy=db.execute('SELECT snapshot_json FROM saves WHERE session_id=?',(self.session['session_id'],)).fetchone()[0]
        self.assertEqual((json.loads(raw_slot)['schema_version'],json.loads(raw_slot)['level_version']),('1.4.0','3.4.0'))
        self.route32(40,42);current=self.state()
        status,replay=self.post(deepcopy(request));self.assertEqual(status,200);self.assertTrue(replay['data']['replayed']);self.assertEqual(replay['data']['receipt'],first['data']['receipt']);self.assertEqual(replay['data']['visible_state'],current)
        restored=self.control('restore');self.assertEqual(restored['device_states']['exit'],'LOCKED');self.assertIsNotNone(restored['minigames']['sequence']);self.assertFalse(can_submit(restored))
        self.reopen();self.assertEqual(self.state(),restored)
        self.route32(40,42)
        status,archive_restored=self.exchange('POST',f"/api/sessions/{self.session['session_id']}/saves/{save_id}/restore",headers=self.headers(),json=self.version(),definition='save_slot_response')
        self.assertEqual(status,200);after=archive_restored['data']['visible_state'];self.assert_early(after,'LOCKED')
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute('SELECT snapshot_json FROM save_slots WHERE save_id=?',(save_id,)).fetchone()[0],raw_slot)
            self.assertEqual(db.execute('SELECT snapshot_json FROM saves WHERE session_id=?',(self.session['session_id'],)).fetchone()[0],raw_legacy)
        self.action('move',{'destination_id':'R2'});self.assertIsNone(self.state()['minigames']['sequence']);self.action('move',{'destination_id':'R3'});self.assertIsNotNone(self.state()['minigames']['sequence'])
        self.control('reset');self.assertIsNone(self.state()['minigames']['sequence'])
        records.append({'check':'v3.4 legacy slot and manual archive restores/reopen at pre-card stage; immutable raw snapshots; receipt replay current projection; other room/reset hidden','result':'passed'})

class LegacyV33(UpgradeV33Acceptance):
    def test_v33_original_projection_after_strip_stays_gated(self):
        self.route32(end=22);self.finish_circuit();self.route32(23,40)
        self.assertEqual(self.state()['device_states']['exit'],'LOCKED');self.assertIsNone(self.state()['minigames']['sequence']);self.assertFalse(can_submit(self.state()))
        self.route32(40,41);self.assertEqual(self.state()['device_states']['exit'],'CARD_ACCEPTED');self.assertIsNone(self.state()['minigames']['sequence']);self.assertFalse(can_submit(self.state()))
        self.route32(41,42);self.assertIsNotNone(self.state()['minigames']['sequence']);self.assertTrue(can_submit(self.state()))
        records.append({'check':'explicit v3.3 continues null sequence at LOCKED/CARD_ACCEPTED, exposed at FINAL_CHECK','result':'passed'})

suite=unittest.TestSuite([
    EarlyV34('test_v34_earlier_graphics_preserve_exit_stage_guards_and_win'),
    EarlyV34('test_v34_save_archive_restore_reopen_and_replay_reproject_without_snapshot_migration'),
    LegacyV33('test_v33_original_projection_after_strip_stays_gated'),
    UpgradeV33Acceptance('test_unknown_boards_stay_null_and_wrong_room_manual_actions_reject'),
    UpgradeV33Acceptance('test_sequence_derivation_wrong_order_length_duplicate_unknown_and_freeze'),
])
stream=io.StringIO();start=time.monotonic();run=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
print(stream.getvalue())
report={'scope':'Backend development only, not independent formal QA','methods_run':run.testsRun,'failures':len(run.failures),'errors':len(run.errors),'exit_code':0 if run.wasSuccessful() else 1,'elapsed_seconds':round(time.monotonic()-start,3),'records':records,'failed_method_ids':[case.id() for case,_ in run.failures+run.errors],'actual_paid_calls':0,'actual_provider_calls':0,'limits':['No browser rendering/draft tests.','In-process TestClient reopening; no actual process restart.','Production databases untouched; fixture-only temporary stores.']}
out=ROOT/'evidence/integration/closeup-panel/backend-development.json'
assert not out.exists(),'Preserve existing execution evidence; choose a new epoch filename.'
out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
raise SystemExit(report['exit_code'])
