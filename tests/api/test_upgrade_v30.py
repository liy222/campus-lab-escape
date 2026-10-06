"""Independent v3.0 checks for exploratory presentation and safe item trials.

These tests use only the public HTTP contract and fixture-owned databases. They
do not read rule tables or call any model provider.
"""
from tests.api.test_r1 import HTTPFixture, semantic_text
from tests.api.test_m2 import ROUTE, gameplay


class UpgradeV30Acceptance(HTTPFixture):
    def send(self, tool, arguments):
        request = self.request(tool, arguments)
        return self.exchange(
            'POST', f"/api/sessions/{self.session['session_id']}/actions",
            headers=self.headers(), json=request, definition='action_response',
        )

    def do(self, tool, arguments):
        status, body = self.send(tool, arguments)
        self.assertEqual(status, 200, body)
        return body['data']

    def try_wrong_visible_targets(self, item_id, valid_target):
        """Every visible object can be tried; an incorrect target is harmless."""
        state = self.state()
        visible = [obj['object_id'] for obj in state['objects']]
        self.assertIn(valid_target, visible)
        for target_id in visible:
            if target_id == valid_target:
                continue
            with self.subTest(item=item_id, target=target_id):
                before = self.state()
                status, body = self.send('use_item', {'item_id': item_id, 'target_id': target_id})
                self.assertEqual(status, 409, body)
                self.assertEqual(body['error']['code'], 'PRECONDITION_FAILED')
                message = body['error']['message']
                self.assertTrue(message.strip())
                self.assertRegex(message, r'[\u3400-\u9fff]')
                self.assertNotIn('PRECONDITION_FAILED', message)
                self.assertEqual(body['visible_state'], before)
                after = self.state()
                self.assertEqual(after, before)
                self.assertEqual(after['revision'], before['revision'])
                self.assertEqual([i['item_id'] for i in after['inventory']],
                                 [i['item_id'] for i in before['inventory']])

    def test_v30_item_and_room_copy_does_not_map_items_to_targets(self):
        initial = self.state()
        self.assertNotRegex(initial['room']['description'], r'寻找.{0,12}(门卡|钥匙|保险丝)')
        self.assertNotRegex(initial['room']['description'], r'通往.{0,12}(门卡|钥匙|保险丝)')
        public = semantic_text(initial)
        for hidden in ['382', '724', '231', '三角记为3', '柜门标签从左到右', '青色7', '冷却对应2']:
            self.assertNotIn(hidden, public)

        for tool, arguments in ROUTE[:4]:
            self.do(tool, arguments)
        state = self.state()
        card = next(item for item in state['inventory'] if item['item_id'] == 'access_card')
        self.assertNotRegex(card['description'], r'(可用于|用于|可装入|设备间|刷卡门)')

    def test_v30_wrong_targets_are_safe_for_each_item_and_legacy_save_restores(self):
        # Door card: try every currently visible object before finding its use.
        for tool, arguments in ROUTE[:4]:
            self.do(tool, arguments)
        self.try_wrong_visible_targets('access_card', 'r1_door')
        self.do(*ROUTE[4])
        self.do(*ROUTE[5])

        # Fuse: mismatch feedback must preserve possession and the power state.
        self.do(*ROUTE[6])
        self.try_wrong_visible_targets('fuse', 'r2_powerbox')
        self.do(*ROUTE[7])
        self.assertTrue(self.state()['progress']['power_on'])

        # The current v2 save contract remains usable across a failed trial,
        # restore, and a subsequent successful route.
        status, saved = self.exchange(
            'POST', f"/api/sessions/{self.session['session_id']}/save",
            headers=self.headers(), json={
                'request_id': 'upgrade-v30-save-before-drawer',
                'revision': self.state()['revision'],
                'generation': self.state()['generation'],
            }, definition='control_response',
        )
        self.assertEqual(status, 200, saved)
        saved_state = saved['data']['visible_state']
        self.assertEqual(saved_state['level_version'], '2.0.0')

        # Reach the key without changing the route IDs or answer contract.
        self.do(*ROUTE[8])
        self.do(*ROUTE[9])
        self.do(*ROUTE[10])
        self.do(*ROUTE[11])
        self.try_wrong_visible_targets('emergency_key', 'r2_door')

        status, restored = self.exchange(
            'POST', f"/api/sessions/{self.session['session_id']}/restore",
            headers=self.headers(), json={
                'request_id': 'upgrade-v30-restore-before-drawer',
                'revision': self.state()['revision'],
                'generation': self.state()['generation'],
            }, definition='control_response',
        )
        self.assertEqual(status, 200, restored)
        restored_state = restored['data']['visible_state']
        self.assertEqual(gameplay(restored_state), gameplay(saved_state))
        self.assertEqual(restored_state['level_version'], '2.0.0')
        self.assertNotEqual(restored_state['generation'], saved_state['generation'])
        self.assertNotIn('emergency_key', [item['item_id'] for item in restored_state['inventory']])

        for tool, arguments in ROUTE[8:]:
            self.do(tool, arguments)
        final_state = self.state()
        self.assertEqual(final_state['status'], 'won')
        self.assertEqual(final_state['room']['room_id'], 'EXIT')
