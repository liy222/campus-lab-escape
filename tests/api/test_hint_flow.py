"""Independent hint-flow acceptance using legal domain paths and isolated HTTP DBs.

No provider network or old test/evidence mutation. Main frozen-candidate runner
is required for formal evidence; importing this module alone is preparation.
"""
import asyncio
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from backend.app.domain import graybox_rules as rules
from backend.app.ai.hints import available_topics, bounded_render, TEMPLATES, NO_HINT
from backend.app.ai.runtime import Runtime
from backend.app.ai.mock import DeterministicMockProvider
from backend.app.ai.types import TurnResult, Version, ProposalCandidate
from tests.api.test_r1 import HTTPFixture
from tests.api import test_upgrade_v33 as manual
from tests.api import test_upgrade_v34 as old

ROOT = Path(__file__).resolve().parents[2]
RECORDS = []
ROUTE = [(x['tool'], x['arguments']) for x in json.loads((ROOT / 'evidence/documentation/gameplay-walkthrough-20261018/verification.json').read_text(encoding='utf-8'))['route_steps']]
ORIGINAL = json.loads((ROOT / 'evidence/review/default-hints-20261018/probe.json').read_text(encoding='utf-8'))['template_rendering']
FORBIDDEN = ('4217', '2117', '4792', 'LAB-42', 'ventilation, cooling, lighting, safety', '通风 → 冷却 → 照明 → 安全')


def snapshots(route=ROUTE):
    state = rules.initial_state()
    yield 'initial', rules.visible_state('qa-hint-flow', state)
    for n, (tool, arguments) in enumerate(route, 1):
        state, _ = rules.apply_action(state, tool, arguments)
        yield f'{n}:{tool}:{arguments}', rules.visible_state('qa-hint-flow', state)


def gameplay(state):
    return {k: copy.deepcopy(v) for k, v in state.items() if k not in {'statistics', 'revision', 'generation', 'save', 'settlement'}}


class HintFlowDomain(unittest.TestCase):
    def check_options(self, label, state):
        options = available_topics(state)
        known = {c['clue_id'] for c in state['clues']}
        self.assertEqual(len({tuple(sorted(o['clue_refs'])) for o in options}), len(options), 'Store refs ambiguity: ' + label)
        if state['status'] == 'playing':
            self.assertTrue(options, 'Missing route-node hint: ' + label)
        else:
            self.assertEqual(options, [])
        rendered = []
        for option in options:
            self.assertLessEqual(set(option['clue_refs']), known, label)
            for level in (1, 2, 3):
                projection = copy.deepcopy(state)
                projection['statistics']['current_hint_level'] = level
                answer, refs = bounded_render(projection, option['clue_refs'], option['topic'])
                self.assertTrue(answer.strip())
                self.assertEqual(refs, option['clue_refs'])
                self.assertEqual(bounded_render(projection, refs)[0], answer, 'Store/runtime topic mismatch')
                for solution in FORBIDDEN:
                    self.assertNotIn(solution, answer, label)
                self.assertNotIn('r1_photo', answer)
                self.assertNotIn('r2_service_label', answer)
                rendered.append({'topic': option['topic'], 'level': level, 'answer': answer, 'refs': refs})
        RECORDS.append({'check': 'domain-node', 'label': label, 'room': state['room']['room_id'], 'devices': state['device_states'], 'puzzles': state['puzzle_states'], 'known': sorted(known), 'observed': state['observed_object_ids'], 'visible': [o['object_id'] for o in state['objects']], 'inventory': [i['item_id'] for i in state['inventory']], 'topics': options, 'rendered': rendered})
        return options

    def test_real_walkthrough_every_node_three_levels_and_original_18(self):
        covered = set()
        for label, state in snapshots():
            with self.subTest(node=label):
                options = self.check_options(label, state)
                covered.update(o['topic'] for o in options)
        self.assertLessEqual(set(ORIGINAL), covered)
        for topic, levels in ORIGINAL.items():
            for level, expected in levels.items():
                self.assertEqual(TEMPLATES[topic][int(level)-1], expected['answer'])
        RECORDS.append({'check': 'original-18-byte-text-preserved', 'templates': ORIGINAL})

    def test_early_cross_room_and_guessed_completed_goals(self):
        early = [('inspect', {'object_id': 'r1_door'}), ('interact', {'target_id': 'r1_door'}), ('move', {'destination_id': 'R2'}), ('inspect', {'object_id': 'r2_door'}), ('interact', {'target_id': 'r2_door'}), ('move', {'destination_id': 'R3'}), ('inspect', {'object_id': 'r3_panel'}), ('inspect', {'object_id': 'exit_door'})]
        for label, state in snapshots(early):
            with self.subTest(early=label):
                self.check_options('early:' + label, state)
        # Skip deduction-only clues, but retain every legally required object read.
        skipped = {'r1_clock', 'r1_record', 'r1_plaque', 'r1_microscope', 'sample_slide', 'r1_symbols', 'r2_maintenance', 'r3_legend'}
        guessed = [(t, a) for t, a in ROUTE if not (t == 'inspect' and a.get('object_id') in skipped) and not (t == 'take' and a.get('item_id') == 'sample_slide') and not (t == 'use_item' and a.get('item_id') == 'sample_slide')]
        last = None
        for label, state in snapshots(guessed):
            with self.subTest(guessed=label):
                options = self.check_options('guessed:' + label, state)
                ids = {o['topic'] for o in options}
                if state['device_states']['cabinet'] != 'LOCKED':
                    self.assertFalse(ids & {'sample_time', 'sample_mark'})
                if state['device_states']['computer'] in {'UNLOCKED', 'DATA_READ'}:
                    self.assertFalse(ids & {'login_identity', 'login_time'})
                if state['progress']['check_done']:
                    self.assertNotIn('sequence', ids)
                last = state
        self.assertEqual(last['status'], 'won')
        self.assertNotIn('r1_record_clue', {c['clue_id'] for c in last['clues']})
        self.assertNotIn('r3_legend_clue', {c['clue_id'] for c in last['clues']})


class HintFlowHTTP(HTTPFixture):
    route32 = manual.UpgradeV33Acceptance.route32
    version = manual.UpgradeV33Acceptance.version
    control = manual.UpgradeV33Acceptance.control
    circuit_ready_to_edit = manual.UpgradeV33Acceptance.circuit_ready_to_edit
    rotate_to = manual.UpgradeV33Acceptance.rotate_to
    finish_circuit = manual.UpgradeV33Acceptance.finish_circuit
    reopen = old.UpgradeV34Acceptance.reopen
    ask = old.UpgradeV34Acceptance.ask
    install = old.UpgradeV34Acceptance.install

    def setUp(self):
        super().setUp()
        self.client.__exit__(None, None, None)
        from fastapi.testclient import TestClient
        from backend.app.main import create_app
        self.db = Path(self.temp.name) / 'hint-flow.sqlite'
        self.client = TestClient(create_app(self.db, gameplay_version='v3.4'), raise_server_exceptions=False)
        self.client.__enter__()
        self.session = self.create()
        self.network = patch('httpx.AsyncClient.send', side_effect=AssertionError('Provider network forbidden in hint-flow QA'))
        self.network.start()

    def tearDown(self):
        self.network.stop()
        super().tearDown()

    def assert_hint(self, level=1):
        before = self.state()
        self.client.app.state.ai_runtime = Runtime(DeterministicMockProvider())
        options = available_topics(before)
        expected = copy.deepcopy(before)
        expected['statistics']['current_hint_level'] = level
        allowed = {bounded_render(expected, o['clue_refs'], o['topic'])[0] for o in options}
        data, request = self.ask(level)
        self.assertIn(data['answer'], allowed)
        self.assertEqual(data['status'], 'no_suggestion')
        self.assertIsNone(data['proposal'])
        self.assertEqual(data['usage']['model_calls'], 0)
        self.assertEqual(data['usage']['read_tool_calls'], 0)
        self.assertEqual(gameplay(self.state()), gameplay(before))
        self.assertEqual(self.state()['statistics']['hint_count'], before['statistics']['hint_count']+1)
        self.assertEqual(self.state()['statistics']['current_hint_level'], level)
        RECORDS.append({'check': 'HTTP-mock', 'test': self._testMethodName, 'level': level, 'answer': data['answer'], 'count_before': before['statistics']['hint_count'], 'count_after': self.state()['statistics']['hint_count'], 'eligible': options})
        return data, request

    def test_initial_observation_valid_repeat_replay_stale_and_failed_provider(self):
        initial = self.state()
        data, request = self.assert_hint(1)
        self.assertEqual(self.state()['observed_object_ids'], initial['observed_object_ids'])
        after = self.state()
        replay, _ = self.ask(request=request)
        self.assertEqual(replay['answer'], data['answer'])
        self.assertEqual(self.state(), after)
        self.assert_hint(1)
        self.assertEqual(self.state()['statistics']['hint_count'], 2)
        stale = {**self.version(), 'message': '合法请求', 'hint_level': 1}
        self.action('inspect', {'object_id': 'r1_clock'})
        before = self.state()
        rejected, _ = self.ask(request=stale, expected=409)
        self.assertEqual(rejected['error']['code'], 'STALE_STATE')
        self.assertEqual(self.state(), before)
        from backend.app.ai.provider import ProviderError
        provider = self.install(old.CapturedHintProvider(error=ProviderError('MODEL_UNAVAILABLE')))
        failed, _ = self.ask(1)
        self.assertEqual(failed['status'], 'stopped')
        self.assertEqual(len(provider.contexts), 1)
        self.assertEqual(self.state(), before)

    def test_mock_round_robin_at_two_original_topics_and_levels(self):
        self.route32(end=9)
        options = available_topics(self.state())
        self.assertGreaterEqual(len(options), 2)
        self.assertLessEqual({'sample_time', 'sample_mark'}, {o['topic'] for o in options})
        for level in (1, 2, 3):
            answers = [self.assert_hint(level)[0]['answer'] for _ in options]
            self.assertEqual(len(set(answers)), len(options))
        # Every supplied provider choice must survive Store final rendering exactly.
        for option in options:
            class Select(old.CapturedHintProvider):
                async def complete(provider, messages, tools, limits, **kwargs):
                    provider.contexts.append(copy.deepcopy(messages))
                    from tests.api.test_m3 import reply
                    return reply(json.dumps(option, ensure_ascii=False))
            provider = self.install(Select())
            before = self.state()
            data, _ = self.ask(2, message='QA_PRIVATE_QUESTION_4217')
            expected = copy.deepcopy(before)
            expected['statistics']['current_hint_level'] = 2
            self.assertEqual(data['answer'], bounded_render(expected, option['clue_refs'], option['topic'])[0])
            context = json.dumps(provider.contexts, ensure_ascii=False)
            for private in ('QA_PRIVATE_QUESTION', '4217', '21:17', 'LAB-42', 'r3_legend_clue'):
                self.assertNotIn(private, context)

    def test_store_does_not_trust_prose_refs_proposals_or_read_tools(self):
        baseline, _ = self.assert_hint(1)
        sentinel = 'QA_UNTRUSTED_FULL_SOLUTION_4217'
        for case in ('prose', 'unknown-refs', 'proposal', 'stale', 'read', 'stopped'):
            with self.subTest(case=case):
                before = self.state()
                option = available_topics(before)[0]
                class Fake:
                    async def run(fake, start, callbacks):
                        version = Version.from_state(start.visible_state)
                        data = {k: copy.deepcopy(baseline[k]) for k in ('answer', 'clue_refs', 'status', 'stop_reason', 'usage')}
                        data.update(answer=sentinel, clue_refs=option['clue_refs'])
                        proposal = None
                        if case == 'unknown-refs': data['clue_refs'] = ['r3_legend_clue']
                        if case == 'proposal': proposal = ProposalCandidate('move', {'destination_id': 'R2'}, (), sentinel)
                        if case == 'stale': version = Version(version.revision+1, version.generation)
                        if case == 'stopped': data.update(status='stopped', stop_reason='MODEL_INVALID_OUTPUT')
                        if case == 'read':
                            result = await callbacks.read_tool(version, 'inspect', {'object_id': 'r1_plaque'})
                            self.assertFalse(result.ok)
                            self.assertEqual(result.error_code, 'INVALID_TOOL')
                        return TurnResult(data, proposal, (), version)
                self.client.app.state.ai_runtime = Fake()
                data, _ = self.ask(1)
                self.assertNotIn(sentinel, json.dumps(data, ensure_ascii=False))
                self.assertIsNone(data['proposal'])
                self.assertEqual(gameplay(self.state()), gameplay(before))
                if case in {'unknown-refs', 'proposal', 'stale', 'stopped'}:
                    self.assertEqual(data['status'], 'stopped')
                    self.assertEqual(self.state()['statistics']['hint_count'], before['statistics']['hint_count'])
                else:
                    self.assertEqual(data['status'], 'no_suggestion')
                    self.assertEqual(data['answer'], bounded_render(before, option['clue_refs'])[0])
                    self.assertEqual(self.state()['statistics']['hint_count'], before['statistics']['hint_count']+1)
                RECORDS.append({'check': 'Store-authority', 'case': case, 'status': data['status'], 'count_delta': self.state()['statistics']['hint_count']-before['statistics']['hint_count']})

    def test_selected_archive_restore_reopen_preserves_count_level_and_rotation(self):
        self.route32(end=9)
        self.assert_hint(3)
        saved = self.state()
        status, body = self.exchange('POST', f"/api/sessions/{self.session['session_id']}/saves", headers=self.headers(), json={**self.version(), 'name': 'hint rotation'}, definition='save_slot_response')
        self.assertEqual(status, 201)
        save_id = body['data']['slot']['save_id']
        expected, stale = self.assert_hint(3)
        self.assert_hint(1)
        status, _ = self.exchange('POST', f"/api/sessions/{self.session['session_id']}/saves/{save_id}/restore", headers=self.headers(), json=self.version(), definition='save_slot_response')
        self.assertEqual(status, 200)
        restored = self.state()
        self.assertEqual(restored['statistics'], saved['statistics'])
        self.assertEqual(gameplay(restored), gameplay(saved))
        self.reopen()
        self.assertEqual(self.state(), restored)
        data, _ = self.assert_hint(3)
        self.assertEqual(data['answer'], expected['answer'])
        before = self.state()
        rejected, _ = self.ask(request=stale, expected=409)
        self.assertEqual(rejected['error']['code'], 'STALE_GENERATION')
        self.assertEqual(self.state(), before)

    def test_http_route_to_r3_and_no_topic_fallback_count_zero_after_exit(self):
        for tool, arguments in ROUTE:
            self.action(tool, arguments)
            state = self.state()
            if state['status'] == 'playing' and (state['room']['room_id'] == 'R3' or state['device_states']['powerbox'] == 'CIRCUIT_READY' or state['device_states']['computer'] in {'BOOTING', 'UNLOCKED', 'DATA_READ'}):
                self.assert_hint(2)
        self.assertEqual(self.state()['status'], 'won')
        before = self.state()
        data, _ = self.ask(1)
        self.assertEqual(data['answer'], NO_HINT)
        self.assertEqual(data['usage']['model_calls'], 0)
        self.assertEqual(self.state(), before)


if __name__ == '__main__':
    unittest.main()
