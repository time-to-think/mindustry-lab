import json
from dataclasses import replace
import tempfile
import unittest
from unittest.mock import patch

from mindustry_agent.config import AgentConfig
from mindustry_agent.http_client import HttpJsonError
from mindustry_agent.llm import LlmResult
from mindustry_agent.policy import validate_decision
from mindustry_agent.runner import run
from mindustry_agent.timing import CycleTimer


class CycleTimingTest(unittest.TestCase):
    def test_monotonic_duration_accumulation_and_snapshot_copy(self):
        with patch('mindustry_agent.timing.time.perf_counter', side_effect=[0, 1, 3, 4, 5, 6]):
            timer = CycleTimer()
            self.assertEqual(timer.call('work', lambda: 'value'), 'value')
            self.assertEqual(timer.call('work', lambda: 42), 42)
            snapshot = timer.snapshot()
        self.assertEqual(snapshot['stages_seconds'], {'work': 3})
        self.assertEqual(snapshot['elapsed_seconds'], 6)
        timer.stages['work'] = 99
        self.assertEqual(snapshot['stages_seconds']['work'], 3)

    def test_exception_duration_is_recorded_without_swallowing_error(self):
        with patch('mindustry_agent.timing.time.perf_counter', side_effect=[0, 1, 4]):
            timer = CycleTimer()
            with self.assertRaisesRegex(ValueError, 'test'):
                timer.call('work', lambda: (_ for _ in ()).throw(ValueError('test')))
        self.assertEqual(timer.stages['work'], 3)

    def run_mock_turn(self, directory, *, dry_run=False, fail=False, action_fail=False, discarded=False):
        state = {'episode_id': 'synthetic', 'playing': True, 'tick': 10, 'wave': 1, 'buildings': [], 'enemy_units': []}
        decision = validate_decision({'reasoning_summary': 'synthetic', 'actions': [], 'wait_seconds': 1})
        config = replace(AgentConfig.from_env(), run_dir=directory, llm_model='synthetic', game_token='')
        with patch('mindustry_agent.runner.MindustryClient') as game, patch('mindustry_agent.runner.OpenAICompatibleLlm') as llm:
            game.return_value.health.return_value = {}
            game.return_value.state.side_effect = [dict(state), dict(state), {**state, 'episode_id': 'next'} if discarded else dict(state)]
            game.return_value.act.return_value = {'results': [], 'tick': 11}
            if action_fail:
                game.return_value.act.side_effect = HttpJsonError('synthetic failure')
            llm.return_value.decide.return_value = LlmResult(decision, 2, {}, '')
            if fail:
                llm.return_value.decide.side_effect = HttpJsonError('synthetic failure')
            path = run(config, once=True, dry_run=dry_run, max_turns=1)
            if fail or dry_run or discarded:
                game.return_value.act.assert_not_called()
            else:
                self.assertEqual(game.return_value.act.call_count, 1)
                self.assertEqual(game.return_value.act.call_args.args[1], decision['actions'])
        return [json.loads(line) for line in path.read_text().splitlines()]

    def test_runner_success_adds_timings_and_preserves_legacy_metric(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            records = self.run_mock_turn(Path(directory))
        turn = next(r for r in records if r['kind'] == 'turn')
        self.assertEqual(turn['llm_latency_seconds'], 2)
        self.assertEqual(set(turn['python_timing']['stages_seconds']), {
            'state_retrieval', 'state_compaction', 'llm_decide', 'action_preparation',
            'state_revalidation', 'execution_compaction', 'action_submission'})
        self.assertTrue(all(value >= 0 for value in turn['python_timing']['stages_seconds'].values()))

    def test_runner_failure_has_duration_but_no_invented_legacy_latency(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            records = self.run_mock_turn(Path(directory), fail=True)
        error = next(r for r in records if r['kind'] == 'turn_error')
        self.assertIn('llm_decide', error['python_timing']['stages_seconds'])
        self.assertNotIn('llm_latency_seconds', error)

    def test_dry_run_does_not_claim_action_submission_time(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            records = self.run_mock_turn(Path(directory), dry_run=True)
        turn = next(r for r in records if r['kind'] == 'turn')
        self.assertNotIn('action_submission', turn['python_timing']['stages_seconds'])

    def test_action_failure_preserves_rejection_and_timing(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            records = self.run_mock_turn(Path(directory), action_fail=True)
        turn = next(r for r in records if r['kind'] == 'turn')
        self.assertFalse(turn['action_response']['ok'])
        self.assertIn('action_submission', turn['python_timing']['stages_seconds'])

    def test_discarded_inference_remains_terminal_without_dispatch(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            records = self.run_mock_turn(Path(directory), discarded=True)
        end = records[-1]
        self.assertEqual(end['reason'], 'game_over_during_inference')
        self.assertIn('python_timing', end)
        self.assertEqual(end['llm_latency_seconds'], 2)


if __name__ == '__main__':
    unittest.main()
