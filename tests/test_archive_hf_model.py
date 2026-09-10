"""Offline archive safety tests; real rsync/zstd, mocked Hub calls."""
import contextlib
import hashlib
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('archive_hf_model', str(Path(__file__).resolve().parents[1] / 'scripts/ai/archive-hf-model'))
spec = importlib.util.spec_from_loader(loader.name, loader)
archive = importlib.util.module_from_spec(spec)
sys.modules[loader.name] = archive
loader.exec_module(archive)
COMMIT = 'a' * 40


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.local, self.nas, self.backup = [self.root / n for n in ('local', 'nas', 'backup')]
        self.nas.mkdir()
        self.backup.mkdir()
        self.argv = ['archive-hf-model', 'owner/model', '--local-root', str(self.local), '--nas-root', str(self.nas)]
        self.files = {'model.safetensors': b'weights', 'config.json': b'{"architectures":["ExampleModel"],"torch_dtype":"bfloat16"}',
                      'tokenizer.json': b'{}', 'README.md': b'model card', 'LICENSE': b'license text'}
        self.commit = COMMIT
        self.calls = []
        self.real_command = archive.run_command

    def args(self, *options):
        with patch.object(sys, 'argv', self.argv + list(options)):
            return archive.parse_args()

    def paths(self, *options, layout='source', commit=COMMIT):
        return archive.build_paths(self.args('--revision', commit, *options), 'model', layout)

    def info(self, *unused):
        return {'sha': self.commit, 'siblings': [{'rfilename': n} for n in self.files]}

    def command(self, cmd):
        self.calls.append(cmd)
        if cmd[:2] == ['hf', 'download']:
            self.assertEqual(cmd[cmd.index('--revision') + 1], self.commit)
            destination = Path(cmd[cmd.index('--local-dir') + 1])
            selection = self.args()
            selection.include = [cmd[i + 1] for i, v in enumerate(cmd) if v == '--include']
            selection.exclude = [cmd[i + 1] for i, v in enumerate(cmd) if v == '--exclude']
            for name in archive.selected_repo_files(self.info(), selection):
                path = destination / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(self.files[name])
            cache = destination / '.cache/huggingface'
            cache.mkdir(parents=True, exist_ok=True)
            (cache / 'metadata').write_text('mutable')
        elif cmd[:3] == ['hf', 'cache', 'verify']:
            self.assertEqual(cmd[cmd.index('--revision') + 1], self.commit)
        else:
            self.real_command(cmd)

    def run_cli(self, *options, command=None):
        original = archive.require_command
        with patch.object(sys, 'argv', self.argv + list(options)), patch.object(archive, 'model_info', side_effect=self.info), patch.object(archive, 'run_command', side_effect=command or self.command), patch.object(archive, 'summarize'), patch.object(archive, 'require_command', side_effect=lambda c: None if c == 'hf' else original(c)), contextlib.redirect_stdout(io.StringIO()):
            return archive.main()

    def download(self, *options):
        self.assertEqual(self.run_cli('--download', *options), 0)
        return self.paths()

    def test_revision_paths_and_rerun_are_immutable(self):
        paths = self.download()
        self.assertEqual(paths.local_model.relative_to(self.local).as_posix(), f'source/huggingface/owner/model/{COMMIT}')
        before = archive.inventory(paths.local_model)
        self.calls.clear()
        self.download()
        self.assertEqual(archive.inventory(paths.local_model), before)
        self.assertEqual(self.calls, [])
        self.commit = 'b' * 40
        self.files['model.safetensors'] = b'new weights'
        self.run_cli('--download')
        self.assertEqual(archive.inventory(paths.local_model), before)
        self.assertEqual((self.paths(commit=self.commit).local_model / 'model.safetensors').read_bytes(), b'new weights')

    def test_selection_changes_and_force_cannot_overwrite(self):
        paths = self.download()
        before = archive.inventory(paths.local_model)
        for options in [('--include', '*.safetensors'), ('--force-download',)]:
            with self.assertRaisesRegex(SystemExit, 'immutable'):
                self.run_cli('--download', *options)
        self.assertEqual(archive.inventory(paths.local_model), before)

    def test_corruption_missing_and_extra_files_fail(self):
        paths = self.download()
        file = paths.local_model / 'model.safetensors'
        for data in (b'corrupt', None):
            file.write_bytes(data) if data is not None else file.unlink()
            with self.assertRaisesRegex(SystemExit, 'verification failed'):
                archive.verify_snapshot(paths.local_model)
            file.write_bytes(self.files['model.safetensors'])
        (paths.local_model / 'extra').write_text('unexpected')
        with self.assertRaisesRegex(SystemExit, 'verification failed'):
            archive.verify_snapshot(paths.local_model)

    def test_interrupted_download_resumes_without_publishing_partial(self):
        def interrupted(cmd):
            self.command(cmd)
            if cmd[:2] == ['hf', 'download']:
                raise subprocess.CalledProcessError(1, cmd)
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_cli('--download', command=interrupted)
        self.assertFalse(self.paths().local_model.exists())
        self.assertTrue(list(self.paths().local_model.parent.glob('*.download-partial')))
        paths = self.download()
        archive.verify_snapshot(paths.local_model)
        self.assertFalse((paths.local_model / '.cache').exists())

    def test_upstream_failure_prevents_publication(self):
        def failed(cmd):
            if cmd[:3] == ['hf', 'cache', 'verify']:
                raise subprocess.CalledProcessError(1, cmd)
            self.command(cmd)
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_cli('--download', command=failed)
        self.assertFalse(self.paths().local_model.exists())

    def test_provenance_and_upstream_verification(self):
        paths = self.download()
        record = archive.read_json(next((paths.local_model / archive.PROVENANCE_DIR).glob('download-*.json')))
        self.assertEqual(record['repository_commit'], COMMIT)
        file = record['files'][0]
        self.assertEqual(file['sha256'], hashlib.sha256(self.files[file['path']]).hexdigest())
        verify = next(c for c in self.calls if c[:3] == ['hf', 'cache', 'verify'])
        self.assertIn('--fail-on-missing-files', verify)
        self.assertTrue(archive.verify_snapshot(paths.local_model)['source_assessment']['complete_repository'])

    def test_filtered_source_is_reported_and_strict_checks_fail(self):
        with self.assertRaisesRegex(SystemExit, 'readiness'):
            self.run_cli('--download', '--include', '*.safetensors', '--require-source-complete')
        self.assertFalse(self.paths().local_model.exists())
        self.run_cli('--download', '--include', '*.safetensors')
        report = archive.verify_snapshot(self.paths().local_model)['source_assessment']
        self.assertFalse(report['complete_repository'])
        self.assertIn('config.json', report['omitted_files'])
        self.assertTrue(report['warnings'])
        verify = next(c for c in self.calls if c[:3] == ['hf', 'cache', 'verify'])
        self.assertNotIn('--fail-on-missing-files', verify)

    def test_complete_source_passes_strict_checks(self):
        self.download('--require-source-complete')

    def test_missing_shard_blocks_publication(self):
        self.files['model.safetensors.index.json'] = b'{"weight_map":{"layer":"missing.safetensors"}}'
        with self.assertRaisesRegex(SystemExit, 'missing referenced'):
            self.run_cli('--download')
        self.assertFalse(self.paths().local_model.exists())

    def test_adapter_and_quantization_reported(self):
        self.files['adapter_config.json'] = b'{"base_model_name_or_path":"owner/base","revision":"main"}'
        self.files['config.json'] = b'{"quantization_config":{"bits":4}}'
        report = archive.verify_snapshot(self.download().local_model)['source_assessment']
        self.assertEqual(report['declared_base_model'], 'owner/base')
        self.assertEqual(report['quantization_config'], {'bits': 4})
        self.assertTrue(any('standalone' in w for w in report['warnings']))
        self.assertTrue(any('no explicitly archived' in w for w in report['warnings']))

    def test_dependency_commit_preserved(self):
        source = self.download().local_model
        self.commit = 'b' * 40
        self.files['adapter_config.json'] = json.dumps({'base_model_name_or_path': 'owner/model', 'revision': COMMIT}).encode()
        self.run_cli('--download', '--base-model-dir', str(source))
        report = archive.verify_snapshot(self.paths(commit=self.commit).local_model)['source_assessment']
        self.assertEqual(report['base_snapshots'][0]['repository_commit'], COMMIT)
        self.assertFalse(any('no explicitly archived' in w for w in report['warnings']))

    @unittest.skipUnless(shutil.which('rsync'), 'rsync not installed')
    def test_default_flow_real_rsync_backup_and_verify(self):
        self.run_cli('--backup-root', str(self.backup))
        paths = self.paths()
        expected = archive.inventory(paths.local_model)
        self.assertEqual(archive.inventory(paths.nas_model), expected)
        self.assertEqual(archive.inventory(self.backup / paths.nas_model.relative_to(self.nas)), expected)
        self.assertEqual(paths.local_checksum.read_bytes(), paths.checksum.read_bytes())
        for target in ('local', 'nas', 'backup'):
            self.run_cli('--verify', '--revision', COMMIT, '--verify-target', target, '--backup-root', str(self.backup))
        self.run_cli('--sync', '--checksum', '--revision', COMMIT)

    @unittest.skipUnless(shutil.which('rsync'), 'rsync not installed')
    def test_corrupted_transfer_is_not_published_and_can_resume(self):
        paths = self.download()
        def corrupt(cmd):
            shutil.copytree(cmd[-2], cmd[-1], dirs_exist_ok=True)
            (Path(cmd[-1]) / 'model.safetensors').write_bytes(b'bad data')
        with self.assertRaisesRegex(SystemExit, 'verification failed'):
            self.run_cli('--sync', '--revision', COMMIT, command=corrupt)
        self.assertFalse(paths.nas_model.exists())
        self.assertFalse(paths.checksum.exists())
        self.run_cli('--sync', '--revision', COMMIT)
        self.assertEqual(archive.inventory(paths.local_model), archive.inventory(paths.nas_model))

    @unittest.skipUnless(shutil.which('rsync'), 'rsync not installed')
    def test_nas_corruption_is_not_rebaselined(self):
        self.run_cli()
        paths = self.paths()
        original = paths.checksum.read_bytes()
        (paths.nas_model / 'model.safetensors').write_bytes(b'bad')
        for stage in ('--sync', '--checksum', '--verify'):
            with self.assertRaisesRegex(SystemExit, 'verification failed'):
                self.run_cli(stage, '--revision', COMMIT)
        self.assertEqual(paths.checksum.read_bytes(), original)

    def test_verify_requires_saved_checksum(self):
        paths = self.download()
        paths.local_checksum.unlink()
        with self.assertRaisesRegex(SystemExit, 'missing'):
            self.run_cli('--verify', '--verify-target', 'local', '--revision', COMMIT)
        self.assertFalse(paths.local_checksum.exists())

    def test_archive_roundtrip_and_no_overwrite(self):
        self.download()
        for compression in [None, 'none'] + (['zstd'] if shutil.which('zstd') else []):
            with self.subTest(compression=compression):
                compression_options = ('--compression', compression) if compression else ()
                options = ('--revision', COMMIT, *compression_options)
                self.run_cli('--archive', *options)
                paths = self.paths(*compression_options)
                self.assertTrue(str(paths.local_archive).endswith('.tar.zst' if compression == 'zstd' else '.tar'))
                before = paths.local_archive.read_bytes()
                self.run_cli('--archive', *options)
                self.run_cli('--verify-archive', '--archive-path', str(paths.local_archive))
                self.assertEqual(paths.local_archive.read_bytes(), before)
                restore = self.root / f'restore-{compression}'
                restore.mkdir()
                raw = paths.local_archive
                if compression == 'zstd':
                    raw = self.root / 'restore.tar'
                    with raw.open('wb') as output:
                        subprocess.run(['zstd', '-q', '-dc', str(paths.local_archive)], stdout=output, check=True)
                with tarfile.open(raw) as tar:
                    # Only our own verified test archive is extracted.
                    tar.extractall(restore)
                self.assertEqual(archive.inventory(restore / COMMIT), archive.inventory(paths.local_model))
                paths.local_archive.write_bytes(b'corrupt')
                with self.assertRaisesRegex(SystemExit, 'checksum'):
                    self.run_cli('--verify-archive', '--archive-path', str(paths.local_archive))
                paths.local_archive.write_bytes(before)

    def test_archive_inside_snapshot_rejected(self):
        paths = self.download()
        with self.assertRaisesRegex(SystemExit, 'outside'):
            self.run_cli('--archive', '--revision', COMMIT, '--archive-path', str(paths.local_model / 'bad.tar'))

    def test_archive_traversal_and_links_rejected(self):
        for name, kind in [('../escape', tarfile.REGTYPE), ('root/link', tarfile.SYMTYPE)]:
            target = self.root / 'unsafe.tar'
            with tarfile.open(target, 'w') as tar:
                member = tarfile.TarInfo(name)
                member.type = kind
                member.linkname = '/etc/passwd' if kind == tarfile.SYMTYPE else ''
                tar.addfile(member, io.BytesIO(b''))
            with self.assertRaises(SystemExit):
                archive.inspect_archive(target)
        self.assertFalse((self.root / 'escape').exists())

    def test_symlinks_and_unmanaged_directories_rejected(self):
        paths = self.download()
        (paths.local_model / 'link').symlink_to(self.root)
        with self.assertRaisesRegex(SystemExit, 'regular'):
            archive.verify_snapshot(paths.local_model)
        unmanaged = self.root / 'legacy'
        unmanaged.mkdir()
        (unmanaged / 'weights').write_text('preserve')
        with self.assertRaises(SystemExit):
            self.run_cli('--download', '--local-model-dir', str(unmanaged))
        self.assertEqual((unmanaged / 'weights').read_text(), 'preserve')

    def test_lock_prevents_concurrent_publication(self):
        path = self.paths().local_model
        with archive.publication_lock(path):
            with self.assertRaisesRegex(SystemExit, 'locked'):
                self.run_cli('--download')
        self.assertFalse(path.exists())

    def test_gguf_routing_and_classification(self):
        self.files = {'model-Q4_K_M.gguf': b'gguf', 'README.md': b'card'}
        self.run_cli('--download')
        archive.verify_snapshot(self.paths(layout='gguf').local_model)
        self.run_cli('--verify', '--verify-target', 'local', '--revision', COMMIT)
        self.assertEqual(archive.infer_layout(['model.gguf', 'model.safetensors']), 'source')
        self.assertEqual(archive.file_format('model.F16.gguf')['model_kind'], 'gguf')
        self.assertIsNone(archive.file_format('model.safetensors')['quantization'])

    def test_conversion_recipe_preserves_inputs_and_is_immutable(self):
        source = self.download().local_model
        outputs = self.root / 'outputs'
        outputs.mkdir()
        (outputs / 'model-Q4_K_M.gguf').write_bytes(b'converted')
        (self.root / 'requirements.txt').write_text('example==1.0\n')
        (self.root / 'calibration.txt').write_text('calibration sample\n')
        recipe = {'name': 'q4', 'source_directory': str(source),
                  'converter': {'repository': 'https://github.com/ggml-org/llama.cpp', 'commit': 'c' * 40},
                  'commands': [['python', 'convert_hf_to_gguf.py', 'source'], ['llama-quantize', 'input.gguf', 'output.gguf', 'Q4_K_M']],
                  'environment': {'python': '3.12', 'platform': 'Linux x86_64'},
                  'dependency_files': ['requirements.txt'], 'calibration_files': ['calibration.txt']}
        recipe_path = self.root / 'recipe.json'
        recipe_path.write_text(json.dumps(recipe))
        options = ('--record-conversion', str(recipe_path), '--local-model-dir', str(outputs))
        self.run_cli(*options)
        paths = self.paths('--conversion-name', 'q4', layout='gguf')
        archive.verify_snapshot(paths.local_model)
        self.assertEqual(paths.local_model.relative_to(self.local).as_posix(), f'inference/gguf/owner/model/{COMMIT}/q4')
        saved = archive.read_json(paths.local_model / archive.PROVENANCE_DIR / 'conversion.json')
        self.assertEqual(saved['source']['repository_commit'], COMMIT)
        self.assertEqual(saved['commands'], recipe['commands'])
        self.assertEqual((paths.local_model / saved['calibration_files'][0]['path']).read_text(), 'calibration sample\n')
        self.calls.clear()
        self.run_cli(*options)
        self.assertEqual(self.calls, [])
        self.run_cli('--verify', '--verify-target', 'local', '--revision', COMMIT, '--conversion-name', 'q4')
        (outputs / 'model-Q4_K_M.gguf').write_bytes(b'different')
        with self.assertRaisesRegex(SystemExit, 'already exists'):
            self.run_cli(*options)
        archive.verify_snapshot(paths.local_model)

    def test_invalid_arguments_and_unresolved_revision(self):
        for options in [('--rsync-delete',), ('--record-conversion', 'recipe.json'), ('--conversion-name', '../bad'), ('--max-workers', '0')]:
            with self.subTest(options=options), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.args(*options)
        with self.assertRaisesRegex(SystemExit, 'full commit'):
            self.run_cli('--sync', '--revision', 'main')

    def test_checksum_filename_escaping(self):
        text = archive.checksum_text({'line\nbreak': 'a' * 64, 'back\\slash': 'b' * 64})
        self.assertIn('\\' + 'a' * 64 + '  ./line\\nbreak\n', text)
        self.assertIn('\\' + 'b' * 64 + '  ./back\\\\slash\n', text)

    def test_missing_storage_root_fails_before_download(self):
        self.nas.rmdir()
        with self.assertRaisesRegex(SystemExit, 'root must already exist'):
            self.run_cli()
        self.assertEqual(self.calls, [])
        self.assertFalse(self.local.exists())

    def test_checksum_path_cannot_be_inside_snapshot(self):
        with self.assertRaisesRegex(SystemExit, 'outside snapshot'):
            self.run_cli('--download', '--local-model-dir', str(self.local))
        self.assertFalse(self.local.exists())

    def test_existing_checksum_corruption_is_not_replaced(self):
        paths = self.download()
        paths.local_checksum.write_text('corrupt baseline')
        with self.assertRaisesRegex(SystemExit, 'saved checksum verification failed'):
            self.download()
        self.assertEqual(paths.local_checksum.read_text(), 'corrupt baseline')

    def test_backup_root_overlap_rejected(self):
        with self.assertRaisesRegex(SystemExit, 'separate'):
            self.run_cli('--download', '--backup-root', str(self.nas / 'nested'))
        self.assertEqual(self.calls, [])

    def test_explicit_local_snapshot_preserves_layout(self):
        self.files = {'model.gguf': b'gguf', 'README.md': b'card'}
        self.run_cli('--download', '--layout', 'source')
        paths = self.paths()
        self.run_cli('--verify', '--verify-target', 'local', '--local-model-dir', str(paths.local_model))

    def test_reserved_repository_paths_and_missing_files_rejected(self):
        self.files['archive-provenance/conflict'] = b'bad'
        with self.assertRaisesRegex(SystemExit, 'reserved'):
            self.run_cli('--download')
        self.assertFalse(self.paths().local_model.exists())

    def test_bad_revision_response_rejected(self):
        result = subprocess.CompletedProcess([], 0, '{"sha":"main","siblings":[]}')
        with patch.object(archive.subprocess, 'run', return_value=result), self.assertRaisesRegex(SystemExit, 'valid commit'):
            archive.model_info(self.args())

    def test_all_supporting_assets_preserved_without_execution(self):
        additions = {'chat_template.jinja': b'template', 'preprocessor_config.json': b'{}',
                     'vision/encoder.safetensors': b'vision', 'modeling_custom.py': b'raise RuntimeError("must never execute")'}
        self.files.update(additions)
        paths = self.download()
        for name, data in additions.items():
            self.assertEqual((paths.local_model / name).read_bytes(), data)

    def test_archive_internal_corruption_rejected_even_with_new_sidecar(self):
        self.download()
        self.run_cli('--archive', '--revision', COMMIT, '--compression', 'none')
        paths = self.paths('--compression', 'none')
        data = paths.local_archive.read_bytes()
        # Change the weight payload in a still structurally valid tar.
        paths.local_archive.write_bytes(data.replace(b'weights', b'corrupt', 1))
        paths.local_archive_checksum.write_text(archive.checksum_text({paths.local_archive.name: archive.sha256_file(paths.local_archive)}))
        with self.assertRaisesRegex(SystemExit, 'contents do not match'):
            self.run_cli('--verify-archive', '--archive-path', str(paths.local_archive))

    @unittest.skipUnless(shutil.which('rsync'), 'rsync not installed')
    def test_backup_from_nas_without_local_snapshot(self):
        self.run_cli()
        shutil.rmtree(self.local)
        self.run_cli('--checksum', '--revision', COMMIT, '--backup-root', str(self.backup))
        paths = self.paths()
        self.assertEqual(archive.inventory(paths.nas_model), archive.inventory(self.backup / paths.nas_model.relative_to(self.nas)))


if __name__ == '__main__':
    unittest.main()
