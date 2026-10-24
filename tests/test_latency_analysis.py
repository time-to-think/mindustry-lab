"""Synthetic fixtures only; these are not live model performance measurements."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from mindustry_agent.latency import analyze, statistics


class LatencyAnalysisTest(unittest.TestCase):
    def report(self, records):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.jsonl'
            path.write_text('\n'.join(json.dumps(row) for row in records) + '\n')
            return analyze([path])

    def test_valid_existing_schema_inherits_run_start_identity(self):
        result = self.report([{'kind': 'run_start', 'model': 'model-a', 'episode_id': 'e1', 'dry_run': False},
                              {'kind': 'turn', 'llm_latency_seconds': 2},
                              {'kind': 'turn', 'llm_latency_seconds': 4}])
        group = result['groups'][0]
        self.assertEqual((group['model'], group['episode'], group['mode']), ('model-a', 'e1', 'live'))
        self.assertEqual(group['latency_seconds'], {'count': 2, 'mean': 3, 'p50': 3, 'p95': 4, 'min': 2, 'max': 4})

    def test_missing_is_not_imputed_as_zero(self):
        result = self.report([{'kind': 'turn'}, {'kind': 'turn', 'llm_latency_seconds': 0}])
        self.assertEqual(result['groups'][0]['latency_seconds']['count'], 1)
        self.assertEqual(result['diagnostics']['missing_latency'], 1)

    def test_invalid_values_are_rejected(self):
        result = self.report([{'kind': 'turn', 'llm_latency_seconds': value}
                              for value in [True, -1, '2.0', float('nan'), float('inf'), {}, 10 ** 500]])
        self.assertEqual(result['diagnostics']['invalid_latency'], 7)
        self.assertIsNone(result['groups'][0]['latency_seconds']['mean'])

    def test_malformed_json_and_non_objects_are_counted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.jsonl'
            path.write_text('private malformed input\n[]\n\n{"kind":"turn","llm_latency_seconds":1}\n')
            result = analyze([path])
        self.assertEqual(result['diagnostics']['malformed'], 2)
        self.assertNotIn('private malformed input', json.dumps(result))
        self.assertEqual(result['diagnostics']['decisions'], 1)

    def test_mixed_models_and_episodes_do_not_pool(self):
        result = self.report([{'kind': 'turn', 'model': m, 'episode_id': e, 'llm_latency_seconds': 1}
                              for m in ('a', 'b') for e in ('one', 'two')])
        self.assertEqual(len(result['groups']), 4)

    def test_identical_repeated_run_starts_remain_separate(self):
        start = {'kind': 'run_start', 'experiment_id': 'experiment-a',
                 'episode_id': 'same-episode', 'model': 'same-model',
                 'team': 'sharded', 'dry_run': False}
        result = self.report([start, {'kind': 'turn', 'llm_latency_seconds': 1},
                              dict(start), {'kind': 'turn', 'llm_latency_seconds': 9}])
        self.assertEqual(len(result['groups']), 2)
        self.assertEqual({g['latency_seconds']['mean'] for g in result['groups']}, {1, 9})
        self.assertEqual({g['run'] for g in result['groups']},
                         {'input-1:session-1', 'input-1:session-2'})
        self.assertTrue(all(g['experiment'] == 'experiment-a' for g in result['groups']))

    def test_unmarked_legacy_prefix_is_separate_from_explicit_session(self):
        result = self.report([{'kind': 'turn', 'llm_latency_seconds': 1},
                              {'kind': 'run_start'}, {'kind': 'turn', 'llm_latency_seconds': 2}])
        self.assertEqual({g['run'] for g in result['groups']},
                         {'input-1:session-0', 'input-1:session-1'})

    def test_legacy_file_without_run_start_still_groups_turns(self):
        result = self.report([{'kind': 'turn', 'llm_latency_seconds': 1},
                              {'kind': 'turn', 'llm_latency_seconds': 3}])
        self.assertEqual(len(result['groups']), 1)
        self.assertEqual(result['groups'][0]['run'], 'input-1:session-0')
        self.assertEqual(result['groups'][0]['latency_seconds']['mean'], 2)

    def test_same_explicit_experiment_in_separate_inputs_keeps_runs_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ('a.jsonl', 'b.jsonl')]
            for path in paths:
                path.write_text(json.dumps({'kind': 'run_start', 'experiment_id': 'same'}) +
                                '\n' + json.dumps({'kind': 'turn', 'llm_latency_seconds': 1}) + '\n')
            result = analyze(paths)
        self.assertEqual({g['run'] for g in result['groups']},
                         {'input-1:session-1', 'input-2:session-1'})
        self.assertTrue(all(g['experiment'] == 'same' for g in result['groups']))

    def test_multiple_run_starts_reset_context(self):
        result = self.report([{'kind': 'run_start', 'model': 'a'}, {'kind': 'turn', 'llm_latency_seconds': 1},
                              {'kind': 'run_start', 'model': 'b'}, {'kind': 'turn', 'llm_latency_seconds': 2}])
        self.assertEqual({g['model'] for g in result['groups']}, {'a', 'b'})

    def test_empty_input(self):
        self.assertEqual(self.report([])['groups'], [])
        self.assertEqual(statistics([])['count'], 0)

    def test_failure_dry_run_repair_and_action_rejection_are_separate(self):
        result = self.report([
            {'kind': 'turn_error', 'message': 'private error'},
            {'kind': 'turn', 'llm_latency_seconds': 1},
            {'kind': 'turn', 'llm_latency_seconds': 2, 'action_response': {'ok': False}},
            {'kind': 'turn', 'llm_latency_seconds': 3, 'action_response': {'dry_run': True}},
            {'kind': 'turn', 'llm_latency_seconds': 4, 'llm_json_repair_attempted': True},
        ])
        self.assertEqual(len(result['groups']), 5)
        failed = next(g for g in result['groups'] if g['outcome'] == 'failed')
        self.assertEqual(failed['missing_latency'], 1)
        self.assertIsNone(failed['latency_seconds']['mean'])
        self.assertNotIn('private error', json.dumps(result))

    def test_percentile_is_nearest_rank_and_p50_is_median(self):
        self.assertEqual(statistics(list(range(1, 21)))['p95'], 19)
        self.assertEqual(statistics([2])['p95'], 2)
        self.assertEqual(statistics([1, 2, 3, 4])['p50'], 2.5)

    def test_discarded_decision_counted_once_and_terminal_record_ignored(self):
        result = self.report([{'kind': 'run_end', 'discarded_decision': {}, 'llm_latency_seconds': 3},
                              {'kind': 'run_end', 'reason': 'turn_limit'}])
        self.assertEqual(result['diagnostics']['decisions'], 1)
        self.assertEqual(result['groups'][0]['outcome'], 'discarded')

    def test_new_stages_are_optional_and_independently_counted(self):
        result = self.report([{'kind': 'turn', 'llm_latency_seconds': 1},
                              {'kind': 'turn', 'llm_latency_seconds': 2, 'python_timing': {
                                  'elapsed_seconds': 4, 'stages_seconds': {'state_retrieval': 0.5, 'llm_decide': 3, 'private': 99}}}])
        stages = result['groups'][0]['python_stage_seconds']
        self.assertEqual(stages['llm_decide']['count'], 1)
        self.assertNotIn('private', stages)
        self.assertEqual(stages['observe_to_log_record']['mean'], 4)

    def test_unknown_experiments_in_different_files_remain_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ('a.jsonl', 'b.jsonl')]
            for path in paths:
                path.write_text('{"kind":"turn","llm_latency_seconds":1}\n')
            self.assertEqual(len(analyze(paths)['groups']), 2)

    def test_explicit_experiments_and_teams_are_not_mixed(self):
        result = self.report([{'kind': 'turn', 'experiment_id': exp, 'team': team,
                               'llm_latency_seconds': 1}
                              for exp in ('a', 'b') for team in ('sharded', 'crux')])
        self.assertEqual(len(result['groups']), 4)

    def test_action_level_failure_is_separate_from_completed_turn(self):
        result = self.report([{'kind': 'turn', 'llm_latency_seconds': 1,
                               'action_response': {'results': [{'ok': True}, {'ok': False}]}},
                              {'kind': 'turn', 'llm_latency_seconds': 1}])
        self.assertEqual({g['outcome'] for g in result['groups']},
                         {'completed', 'action_partial_failure'})

    def test_finite_large_samples_remain_json_serializable(self):
        result = statistics([1e308, 1e308])
        self.assertEqual(result['p50'], 1e308)
        json.dumps(result, allow_nan=False)

    def test_cli_json_and_human_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.jsonl'
            path.write_text('{"kind":"turn","llm_latency_seconds":1}\n')
            cmd = [sys.executable, '-B', 'scripts/analyze_llm_latency.py', str(path)]
            result = subprocess.run(cmd + ['--json'], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout)['diagnostics']['decisions'], 1)
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.assertIn('not total decision-to-action', result.stdout)
            self.assertIn('\"run\": \"input-1:session-0\"', result.stdout)

    def test_cli_missing_file_is_clear_error(self):
        result = subprocess.run([sys.executable, '-B', 'scripts/analyze_llm_latency.py', '/nonexistent/latency-log'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
