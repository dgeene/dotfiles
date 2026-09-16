"""Offline catalog tests: small model fixtures, no Hub access or weight reads."""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

loader = importlib.machinery.SourceFileLoader('model_catalog', str(Path(__file__).resolve().parents[1] / 'scripts/ai/catalog-hf-models'))
spec = importlib.util.spec_from_loader(loader.name, loader)
catalog = importlib.util.module_from_spec(spec)
loader.exec_module(catalog)
COMMIT = 'a' * 40


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.local, self.nas = self.root / 'local', self.root / 'nas'
        self.local.mkdir()
        self.nas.mkdir()
        self.argv = ['model-catalog', '--local-root', str(self.local), '--nas-root', str(self.nas)]

    def model(self, root=None, layout='source/huggingface', artifact=None):
        path = (root or self.local) / layout / 'owner/model' / COMMIT
        if artifact:
            path /= artifact
        path.mkdir(parents=True)
        files = {'model.safetensors' if not artifact else 'model-Q4_K_M.gguf': b'fake weights',
                 'config.json': b'{"architectures":["ExampleModel"],"torch_dtype":"bfloat16"}',
                 'README.md': b'---\nlicense: apache-2.0\n---\n# Example\n\n![badge](badges.png)\n\nThis is a multilingual instruction model designed for coding and conversation.\n',
                 '.github/info.txt': b'support file'}
        for name, data in files.items():
            file = path / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
        prov = path / 'archive-provenance'
        prov.mkdir()
        manifest = {'schema_version': 1, 'repository': 'owner/model', 'repository_commit': COMMIT,
                    'conversion_name': artifact if artifact and artifact != 'download' else None,
                    'files': {name: 'b' * 64 for name in files},
                    'source_assessment': {'declared_dtype': 'bfloat16', 'complete_repository': True, 'warnings': []}}
        (prov / 'snapshot.json').write_text(json.dumps(manifest))
        return path

    def cli(self, *options):
        output = io.StringIO()
        with patch.object(sys, 'argv', self.argv + list(options)), contextlib.redirect_stdout(output):
            self.assertEqual(catalog.main(), 0)
        return output.getvalue()

    def test_merge_same_snapshot_and_summary(self):
        source = self.model()
        shutil.copytree(source, self.nas / source.relative_to(self.local))
        self.cli()
        text = (self.local / 'MODEL-CATALOG.md').read_text()
        self.assertIn('1 model revisions/artifacts; 2 directory copies', text)
        self.assertIn('multilingual instruction model', text)
        self.assertIn('bfloat16', text)
        self.assertIn('ExampleModel', text)
        self.assertIn('Local, NAS', text)
        self.assertNotIn('Missing recorded files', text)
        self.assertNotIn('badges.png', text)
        self.assertIn('not verified', text)

    def test_revision_and_selection_are_not_merged(self):
        source = self.model()
        other = self.nas / source.relative_to(self.local)
        shutil.copytree(source, other)
        manifest = json.loads((other / catalog.SNAPSHOT).read_text())
        manifest['files']['other.gguf'] = 'c' * 64
        (other / catalog.SNAPSHOT).write_text(json.dumps(manifest))
        text = self.cli('--stdout')
        self.assertIn('2 model revisions/artifacts', text)
        self.assertIn('missing recorded files', text)

    def test_no_weight_reads(self):
        self.model()
        original = Path.open
        def guarded(path, *args, **kwargs):
            if path.suffix in catalog.WEIGHTS:
                self.fail(f'Weight file read: {path}')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', guarded):
            self.cli('--stdout')

    def test_refresh_and_mirrored_outputs(self):
        self.model()
        local = self.local / 'INDEX.md'
        nas = self.nas / 'INDEX.md'
        self.cli('--output', str(local), '--output', str(nas))
        self.assertIn('1 model revisions/artifacts', nas.read_text())
        self.model(layout='inference/gguf', artifact='q4')
        self.cli('--output', str(local), '--output', str(nas))
        self.assertIn('2 model revisions/artifacts', local.read_text())
        self.assertIn('Q4', nas.read_text())
        self.assertNotIn('.model-catalog-', '\n'.join(p.name for p in self.local.iterdir()))

    def test_missing_nas_preserves_existing_catalog(self):
        self.model()
        self.cli()
        output = self.local / 'MODEL-CATALOG.md'
        before = output.read_bytes()
        self.nas.rmdir()
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            self.cli()
        self.assertEqual(output.read_bytes(), before)
        self.cli('--local-only')

    def test_malformed_metadata_preserves_catalog(self):
        source = self.model()
        self.cli()
        output = self.local / 'MODEL-CATALOG.md'
        before = output.read_bytes()
        (source / catalog.SNAPSHOT).write_text('broken JSON')
        with self.assertRaises(ValueError):
            self.cli()
        self.assertEqual(output.read_bytes(), before)

    def test_human_files_and_snapshot_outputs_protected(self):
        source = self.model()
        output = self.local / 'notes.md'
        output.write_text('my notes')
        with self.assertRaisesRegex(ValueError, 'not generated'):
            self.cli('--output', str(output))
        self.assertEqual(output.read_text(), 'my notes')
        with self.assertRaisesRegex(ValueError, 'outside model'):
            self.cli('--output', str(source / 'INDEX.md'))
        self.assertFalse((source / 'INDEX.md').exists())

    def test_symlinks_and_staging_are_not_scanned(self):
        source = self.model()
        shutil.copytree(source, source.parent / '.unfinished.download-partial')
        (source.parent / ('b' * 40)).symlink_to(source, target_is_directory=True)
        text = self.cli('--stdout')
        self.assertIn('1 model revisions/artifacts', text)
        output = self.local / 'INDEX.md'
        output.symlink_to(self.root / 'outside.md')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.cli('--output', str(output))

    def test_legacy_folder_and_new_commit_coexist_without_double_counting(self):
        source = self.model()
        (source.parent / 'old.gguf').write_bytes(b'old')
        text = self.cli('--stdout')
        self.assertIn('2 model revisions/artifacts', text)
        self.assertIn('Unsealed', text)
        entries, _ = catalog.scan_root(self.local, 'Local')
        legacy = next(e for e in entries if not e['sealed'])
        self.assertEqual(legacy['locations'][0]['bytes'], 3)

    def test_packages_listed_without_opening(self):
        self.model()
        package = self.local / 'archives/model.tar.zst'
        package.parent.mkdir()
        package.write_bytes(b'not an actual archive')
        text = self.cli('--stdout')
        self.assertIn('1 packaged files', text)
        self.assertIn('model.tar.zst', text)
        self.assertIn('contents, model identity, and checksums were not inspected', text)

    def test_markdown_content_is_escaped(self):
        source = self.model()
        (source / 'README.md').write_text('This model has pipes | and <script>alert(1)</script> with **markdown** that should remain safe text.')
        text = self.cli('--stdout')
        self.assertIn('&#124;', text)
        self.assertNotIn('<script>', text)
        self.assertNotIn('**markdown**', text)

    def test_root_symlink_and_nas_only_output(self):
        self.model(root=self.nas)
        alias = self.root / 'storage-link'
        alias.symlink_to(self.nas, target_is_directory=True)
        self.cli('--nas-only', '--nas-root', str(alias))
        self.assertTrue((self.nas / 'MODEL-CATALOG.md').exists())
        self.assertFalse((self.local / 'MODEL-CATALOG.md').exists())

    def test_source_files_unchanged(self):
        source = self.model()
        before = {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}
        self.cli()
        after = {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_sample_frontmatter_nested_dtype_and_ternary_label(self):
        source = self.model(layout='inference/gguf', artifact='download')
        (source / 'model-PQ2_0.gguf').write_bytes(b'ternary')
        (source / 'config.json').write_text('{"text_config":{"dtype":"bfloat16"}}')
        manifest = json.loads((source / catalog.SNAPSHOT).read_text())
        manifest['source_assessment'] = {}
        (source / catalog.SNAPSHOT).write_text(json.dumps(manifest))
        (source / 'README.md').write_text('---\nbase_model:\n- owner/base\nlicense: apache-2.0\npipeline_tag: text-generation\nlanguage:\n- en\n---\n# Promotional preamble\n\nA long promotional paragraph about the provider, which should be skipped.\n\n# model\n\nA model description about reasoning and multilingual language understanding.\n')
        text = self.cli('--stdout')
        self.assertIn('PQ2&#95;0', text)
        self.assertIn('bfloat16', text)
        self.assertIn('owner/base', text)
        self.assertIn('apache-2.0', text)
        self.assertIn('text-generation', text)
        self.assertIn('multilingual language understanding', text)
        self.assertNotIn('long promotional paragraph', text)

    def test_conversion_source_metadata_fallback(self):
        source = self.model(layout='inference/gguf', artifact='q4')
        (source / 'config.json').unlink()
        manifest = json.loads((source / catalog.SNAPSHOT).read_text())
        manifest.pop('source_assessment')
        (source / catalog.SNAPSHOT).write_text(json.dumps(manifest))
        (source / 'archive-provenance/source-snapshot.json').write_text(json.dumps({
            'source_assessment': {'declared_dtype': 'float16', 'architectures': ['SourceModel']}}))
        text = self.cli('--stdout')
        self.assertIn('float16', text)
        self.assertIn('SourceModel', text)

    def test_description_preferred_over_generic_announcement(self):
        text = '# Example\n\nWe are pleased to announce the newest generation of our open-model family.\n\nExample is a native vision-language model for coding and reasoning.\n'
        self.assertEqual(catalog.card_summary(text, 'Example'), 'Example is a native vision-language model for coding and reasoning.')

    def api(self, current=False):
        head, side, initial = 'b' * 40, 'c' * 40, '0' * 40
        api = Mock()
        api.endpoint = 'https://huggingface.co'
        api.model_info.return_value = SimpleNamespace(sha=COMMIT if current else head)
        # A merged commit can occur after the ancestor in date-sorted history.
        api.list_repo_commits.side_effect = lambda repo, revision: [SimpleNamespace(commit_id=c) for c in
            ([head, COMMIT, side, initial] if revision == head else [COMMIT, initial])]
        old = {'model.safetensors': 'old-weights', 'README.md': 'old-card', 'tokenizer.json': 'old-tokenizer'}
        new = {'model.safetensors': 'new-weights', 'README.md': 'new-card', 'LICENSE': 'new-license'}
        api.list_repo_tree.side_effect = lambda repo, revision, recursive: iter([
            SimpleNamespace(path=n, blob_id=h) for n, h in (old if revision == COMMIT else new).items()])
        return api

    def test_offline_never_initializes_hub_client(self):
        self.model()
        with patch.object(catalog, 'make_hub_api', side_effect=AssertionError('network access')):
            text = self.cli('--stdout')
        self.assertNotIn('Upstream comparison', text)

    def test_upstream_current_skips_history_and_tree(self):
        self.model()
        api = self.api(current=True)
        with patch.object(catalog, 'make_hub_api', return_value=api):
            text = self.cli('--check-upstream', '--stdout')
        self.assertIn('| Status | Current |', text)
        self.assertIn('| Commits behind | 0 |', text)
        self.assertIn('main fallback', text)
        api.list_repo_commits.assert_not_called()
        api.list_repo_tree.assert_not_called()

    def test_upstream_changes_history_sets_and_cache_across_copies(self):
        source = self.model()
        shutil.copytree(source, self.nas / source.relative_to(self.local))
        api = self.api()
        with patch.object(catalog, 'make_hub_api', return_value=api):
            text = self.cli('--check-upstream', '--stdout')
        self.assertIn('2 commits behind', text)
        self.assertIn('Weights/indexes: 1', text)
        self.assertIn('Documentation/license: 2', text)
        self.assertIn('Runtime/config/tokenizer: 1', text)
        self.assertIn('| LICENSE | added | Documentation/license | No |', text)
        self.assertIn('| tokenizer.json | removed | Runtime/config/tokenizer | No |', text)
        self.assertIn('| model.safetensors | modified | Weights/indexes | Yes |', text)
        self.assertEqual(api.model_info.call_count, 1)
        self.assertEqual(api.list_repo_tree.call_count, 2)
        self.assertEqual(api.list_repo_commits.call_count, 2)
        self.assertTrue(all(c.kwargs['revision'] in {COMMIT, 'b' * 40} for c in api.list_repo_tree.call_args_list))

    def test_upstream_absent_ancestor_is_not_reported_as_behind(self):
        self.model()
        api = self.api()
        api.list_repo_commits.side_effect = None
        api.list_repo_commits.return_value = [SimpleNamespace(commit_id='b' * 40)]
        with patch.object(catalog, 'make_hub_api', return_value=api):
            text = self.cli('--check-upstream', '--stdout')
        self.assertIn('Diverged/unknown ancestry', text)
        self.assertIn('| Commits behind | Unknown |', text)
        self.assertIn('Weights/indexes: 1', text)

    def test_upstream_failed_history_can_still_compare_files(self):
        self.model()
        api = self.api()
        api.list_repo_commits.side_effect = TimeoutError('never print this message')
        with patch.object(catalog, 'make_hub_api', return_value=api):
            text = self.cli('--check-upstream', '--stdout')
        self.assertIn('Revision differs', text)
        self.assertIn('Commit count:', text)
        self.assertIn('Weights/indexes: 1', text)
        self.assertNotIn('never print this message', text)

    def test_upstream_failed_file_comparison_remains_unknown(self):
        self.model()
        api = self.api()
        api.list_repo_tree.side_effect = OSError('network failure')
        with patch.object(catalog, 'make_hub_api', return_value=api):
            text = self.cli('--check-upstream', '--stdout')
        self.assertIn('2 commits behind', text)
        self.assertIn('File changes: unknown', text)
        self.assertNotIn('No repository file differences', text)

    def test_upstream_error_reports_are_sanitized_and_cached(self):
        source = self.model()
        shutil.copytree(source, self.nas / source.relative_to(self.local))
        for code, message in [(401, 'Access denied'), (403, 'Access denied'), (404, 'unavailable'), (429, 'rate limit')]:
            api = self.api()
            error = RuntimeError('credential-must-not-appear')
            error.response = SimpleNamespace(status_code=code)
            api.model_info.side_effect = error
            with patch.object(catalog, 'make_hub_api', return_value=api):
                text = self.cli('--check-upstream', '--stdout')
            self.assertIn('Unavailable', text)
            self.assertIn(message, text)
            self.assertNotIn('credential-must-not-appear', text)
            self.assertEqual(api.model_info.call_count, 1)

    def test_upstream_uses_saved_ref_or_override_and_skips_stale_records(self):
        source = self.model()
        record = {'repository': 'owner/model', 'repository_commit': COMMIT,
                  'requested_revision': 'release/v2', 'source_url': 'https://huggingface.co/owner/model'}
        provenance = source / 'archive-provenance/download-test.json'
        provenance.write_text(json.dumps(record))
        for options, expected in [((), 'release/v2'), (('--upstream-revision', 'main'), 'main')]:
            api = self.api(current=True)
            with patch.object(catalog, 'make_hub_api', return_value=api):
                text = self.cli('--check-upstream', '--stdout', *options)
            api.model_info.assert_called_once_with('owner/model', revision=expected, timeout=30)
        record['repository_commit'] = 'f' * 40
        provenance.write_text(json.dumps(record))
        api = self.api(current=True)
        with patch.object(catalog, 'make_hub_api', return_value=api):
            self.cli('--check-upstream', '--stdout')
        self.assertEqual(api.model_info.call_args.kwargs['revision'], 'main')

    def test_upstream_pinned_sha_uses_main_fallback(self):
        source = self.model()
        (source / 'archive-provenance/download-test.json').write_text(json.dumps({
            'repository': 'owner/model', 'repository_commit': COMMIT, 'requested_revision': COMMIT}))
        api = self.api(current=True)
        with patch.object(catalog, 'make_hub_api', return_value=api):
            text = self.cli('--check-upstream', '--stdout')
        self.assertIn('main fallback', text)
        self.assertEqual(api.model_info.call_args.kwargs['revision'], 'main')

    def test_upstream_source_endpoint_mismatch_does_not_send_requests(self):
        source = self.model()
        (source / 'archive-provenance/download-test.json').write_text(json.dumps({
            'repository': 'owner/model', 'repository_commit': COMMIT, 'requested_revision': 'main',
            'source_url': 'https://different.example/owner/model'}))
        api = self.api()
        with patch.object(catalog, 'make_hub_api', return_value=api):
            text = self.cli('--check-upstream', '--stdout')
        self.assertIn('comparison was skipped', text)
        api.model_info.assert_not_called()

    def test_upstream_conversion_compares_source_selection(self):
        source = self.model(layout='inference/gguf', artifact='q4')
        (source / 'archive-provenance/source-snapshot.json').write_text(json.dumps({
            'files': {'model.safetensors': 'b' * 64}}))
        api = self.api()
        with patch.object(catalog, 'make_hub_api', return_value=api):
            text = self.cli('--check-upstream', '--stdout')
        self.assertIn('Source checkpoint for local conversion', text)
        self.assertIn('| model.safetensors | modified | Weights/indexes | Yes |', text)
        self.assertIn('main fallback', text)

    def test_upstream_unsealed_download_not_compared(self):
        source = self.model()
        (source / catalog.SNAPSHOT).unlink()
        api = self.api()
        with patch.object(catalog, 'make_hub_api', return_value=api):
            text = self.cli('--check-upstream', '--stdout')
        self.assertIn('No sealed revision', text)
        api.model_info.assert_not_called()

    def test_upstream_missing_dependency_preserves_catalog(self):
        self.model()
        self.cli()
        output = self.local / 'MODEL-CATALOG.md'
        before = output.read_bytes()
        with patch.object(catalog, 'make_hub_api', side_effect=ValueError('Missing SDK')), self.assertRaises(ValueError):
            self.cli('--check-upstream')
        self.assertEqual(output.read_bytes(), before)

    def test_upstream_revision_requires_flag(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.cli('--upstream-revision', 'release')

    def test_upstream_commit_advance_with_identical_files(self):
        self.model()
        api = self.api()
        api.list_repo_tree.side_effect = lambda *args, **kwargs: iter([SimpleNamespace(path='README.md', blob_id='same')])
        with patch.object(catalog, 'make_hub_api', return_value=api):
            text = self.cli('--check-upstream', '--stdout')
        self.assertIn('2 commits behind', text)
        self.assertIn('No repository file differences', text)

    def test_upstream_inconsistent_histories_have_unknown_count(self):
        self.model()
        api = self.api()
        api.list_repo_commits.side_effect = lambda repo, revision: [SimpleNamespace(commit_id=c) for c in
            (['b' * 40, COMMIT] if revision == 'b' * 40 else [COMMIT, 'f' * 40])]
        with patch.object(catalog, 'make_hub_api', return_value=api):
            text = self.cli('--check-upstream', '--stdout')
        self.assertIn('| Commits behind | Unknown |', text)
        self.assertNotIn('0 commits behind', text)

    def test_offline_refresh_drops_previous_online_report(self):
        self.model()
        with patch.object(catalog, 'make_hub_api', return_value=self.api(current=True)):
            self.cli('--check-upstream')
        output = self.local / 'MODEL-CATALOG.md'
        self.assertIn('Upstream comparison', output.read_text())
        with patch.object(catalog, 'make_hub_api', side_effect=AssertionError('network access')):
            self.cli()
        self.assertNotIn('Upstream comparison', output.read_text())


if __name__ == '__main__':
    unittest.main()
