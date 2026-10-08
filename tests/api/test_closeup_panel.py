"""Targeted independent projection/guard regression; isolated public API fixtures."""
import copy
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.api.test_r1 import HTTPFixture
from tests.api import test_upgrade_v33 as manual
from tests.api import test_upgrade_v34 as graybox


class VersionFixture(HTTPFixture):
    gameplay_version = 'v3.4'

    def setUp(self):
        super().setUp()
        self.client.__exit__(None, None, None)
        from backend.app.main import create_app
        self.db = Path(self.temp.name) / 'closeup.sqlite'
        self.client = TestClient(create_app(self.db, gameplay_version=self.gameplay_version), raise_server_exceptions=False)
        self.client.__enter__()
        self.session = self.create()
        self.network = patch('httpx.AsyncClient.send', side_effect=AssertionError('Model network forbidden in closeup QA'))
        self.network.start()

    def tearDown(self):
        self.network.stop()
        super().tearDown()


class CloseupPanelProjection(VersionFixture):
    reopen = graybox.UpgradeV34Acceptance.reopen
    route32 = manual.UpgradeV33Acceptance.route32
    version = manual.UpgradeV33Acceptance.version
    control = manual.UpgradeV33Acceptance.control
    circuit_ready_to_edit = manual.UpgradeV33Acceptance.circuit_ready_to_edit
    rotate_to = manual.UpgradeV33Acceptance.rotate_to
    finish_circuit = manual.UpgradeV33Acceptance.finish_circuit

    def panel_empty(self):
        self.circuit_ready_to_edit()
        self.finish_circuit()
        self.route32(23, 39)
        self.assertEqual(self.state()['puzzle_states']['panel'], 'EMPTY')
        self.assertEqual(self.state()['device_states']['exit'], 'LOCKED')
        self.assertIsNone(self.state()['minigames']['sequence'])

    def board(self, exit_state, submit):
        state = self.state()
        self.assertEqual(state['device_states']['exit'], exit_state)
        sequence = state['minigames']['sequence']
        self.assertEqual(sequence['target_id'], 'r3_panel')
        self.assertEqual(sequence['length'], 4)
        self.assertEqual(len(sequence['devices']), 4)
        self.assertEqual(len({d['device_id'] for d in sequence['devices']}), 4)
        self.assertEqual({d['symbol'] for d in sequence['devices']}, {'▲', '●', '■', '★'})
        panel = next(o for o in state['objects'] if o['object_id'] == 'r3_panel')
        self.assertEqual(any(a['tool'] == 'submit_sequence' for a in panel['actions']), submit)
        return state

    def test_early_public_devices_keep_final_check_guard_then_finish(self):
        self.panel_empty()
        self.action('use_item', {'item_id': 'research_strip', 'target_id': 'r3_panel'})
        early = self.board('LOCKED', False)
        self.assertFalse(early['progress']['check_done'])
        order = manual.derive_public_sequence(early)
        self.reject(self.request('submit_sequence', {'target_id': 'r3_panel', 'device_ids': order}), 'PRECONDITION_FAILED')
        self.action('use_item', {'item_id': 'access_card', 'target_id': 'exit_door'})
        self.board('CARD_ACCEPTED', False)
        self.reject(self.request('submit_sequence', {'target_id': 'r3_panel', 'device_ids': order}), 'PRECONDITION_FAILED')
        self.action('interact', {'target_id': 'exit_door'})
        self.board('FINAL_CHECK', True)
        self.action('submit_sequence', {'target_id': 'r3_panel', 'device_ids': order})
        self.assertTrue(self.state()['progress']['check_done'])
        self.assertEqual(self.state()['minigames']['sequence']['status'], 'completed')
        self.reject(self.request('submit_sequence', {'target_id': 'r3_panel', 'device_ids': order}), 'PRECONDITION_FAILED')
        self.route32(43, 46)
        self.assertEqual(self.state()['status'], 'won')

    def test_early_board_control_and_archive_restore_reopen_projection(self):
        self.panel_empty()
        self.action('use_item', {'item_id': 'research_strip', 'target_id': 'r3_panel'})
        early = copy.deepcopy(self.board('LOCKED', False))
        self.control('save')
        status, saved = self.exchange('POST', f"/api/sessions/{self.session['session_id']}/saves",
                                     headers=self.headers(), json={**self.version(), 'name': 'early strip'},
                                     definition='save_slot_response')
        self.assertEqual(status, 201)
        slot = saved['data']['slot']
        self.action('use_item', {'item_id': 'access_card', 'target_id': 'exit_door'})
        self.action('interact', {'target_id': 'exit_door'})
        self.control('restore')
        self.board('LOCKED', False)
        self.action('use_item', {'item_id': 'access_card', 'target_id': 'exit_door'})
        status, restored = self.exchange('POST', f"/api/sessions/{self.session['session_id']}/saves/{slot['save_id']}/restore",
                                        headers=self.headers(), json=self.version(), definition='save_slot_response')
        self.assertEqual(status, 200)
        self.assertEqual(restored['data']['slot'], slot)
        after = self.board('LOCKED', False)
        for key in ('room', 'device_states', 'puzzle_states', 'inventory', 'clues', 'progress', 'statistics', 'minigames'):
            self.assertEqual(after[key], early[key], key)
        self.assertNotEqual(after['generation'], early['generation'])
        self.reopen()
        self.assertEqual(self.state(), after)


class CloseupPanelV33Compatibility(VersionFixture):
    gameplay_version = 'v3.3'
    route32 = manual.UpgradeV33Acceptance.route32
    circuit_ready_to_edit = manual.UpgradeV33Acceptance.circuit_ready_to_edit
    rotate_to = manual.UpgradeV33Acceptance.rotate_to
    finish_circuit = manual.UpgradeV33Acceptance.finish_circuit

    def test_v33_keeps_sequence_hidden_until_final_check(self):
        self.circuit_ready_to_edit()
        self.finish_circuit()
        self.route32(23, 40)
        self.assertEqual(self.state()['puzzle_states']['panel'], 'STRIP_INSERTED')
        self.assertIsNone(self.state()['minigames']['sequence'])
        self.route32(40, 41)
        self.assertIsNone(self.state()['minigames']['sequence'])
        self.route32(41, 42)
        self.assertEqual(len(self.state()['minigames']['sequence']['devices']), 4)
