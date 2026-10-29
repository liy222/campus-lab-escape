"""Main integration: source binding and production serialization, no dispatch."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
import httpx
from backend.app.ai import provider as provider_module
from backend.app.ai.budget import cost_units
from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider, GenerationLimits, ProviderError
from backend.app.ai.v5 import GenerationService
from backend.app.domain.generation_content_v2 import select_blueprint
from backend.app.domain.generation_observability import source_snapshot


class StopBeforeReserve(RuntimeError):
    pass


class NoDatabaseLedger:
    def __init__(self):
        self.attempts = 0

    def reserve(self, scope, amount):
        self.attempts += 1
        raise StopBeforeReserve()


async def main():
    snapshot = source_snapshot()
    helper = 'backend/app/domain/puzzle_purpose.py'
    actual_hash = hashlib.sha256((ROOT / helper).read_bytes()).hexdigest()
    assert snapshot['file_fingerprints'][helper] == actual_hash
    rows = []
    transport_calls = []

    def forbidden_transport(request):
        transport_calls.append(True)
        raise AssertionError('Pure accounting reached transport')

    for seed in range(4):
        bp = select_blueprint(3, 'hard', seed=seed)
        messages = GenerationService.messages(
            theme='雨夜里的天文社旧活动室,寻找封存的观测记录',
            room_count=3, difficulty='hard', blueprint=bp)
        ledger = NoDatabaseLedger()
        provider = DeepSeekProvider(
            DeepSeekConfig('SYNTHETIC-ONLY-NOT-A-REAL-KEY'), ledger,
            transport=httpx.MockTransport(forbidden_transport))
        dumps = json.dumps
        captured = []

        def capture(value, *args, **kwargs):
            encoded = dumps(value, *args, **kwargs)
            if isinstance(value, dict) and value.get('model') == 'deepseek-flash' and 'messages' in value:
                captured.append(encoded.encode('utf-8'))
            return encoded

        error = None
        try:
            provider_module.json.dumps = capture
            await provider.complete(messages, [], GenerationLimits(),
                                    scope='v5_generation', tool_choice='none')
            raise AssertionError('Expected stop before any reservation')
        except StopBeforeReserve:
            pass
        except ProviderError as exc:
            error = exc.code
        finally:
            provider_module.json.dumps = dumps
        assert len(captured) == 1
        size = len(captured[0])
        bound = cost_units(size * 4 + 8192, 6000)
        eligible = bound <= 200_000_000
        assert (eligible and ledger.attempts == 1 and error is None) or (
            not eligible and ledger.attempts == 0 and error == 'AI_LIMIT_REACHED')
        rows.append({'seed': seed, 'blueprint': bp.blueprint_id,
                     'serialized_payload_bytes': size,
                     'payload_sha256': hashlib.sha256(captured[0]).hexdigest(),
                     'configured_upper_cost_cny': bound / 1_000_000_000,
                     'within_unchanged_per_call_cap': eligible,
                     'stop_before_reserve_attempts': ledger.attempts,
                     'controlled_error': error})
    assert all(row['within_unchanged_per_call_cap'] for row in rows)
    assert not transport_calls
    result = {'operator': 'Main integration', 'exit_code': 0,
              'helper_source_fingerprint': actual_hash,
              'source_snapshot_git_revision': snapshot['git_revision'],
              'source_revision_note': 'working-source hashes, not an assertion of clean HEAD',
              'request_preflight': rows, 'actual_reservations': 0,
              'transport_calls': 0, 'real_provider_calls': 0,
              'database_constructors': 0, 'player_database_access': False}
    with Path(__file__).with_name('integration-preflight.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'helper_fingerprint_present': True,
                      'upper_costs_cny': [row['configured_upper_cost_cny'] for row in rows],
                      'transport_calls': 0}, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
