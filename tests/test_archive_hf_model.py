"""Offline provenance checks: python3 -m unittest discover -s tests."""
import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
import io
import contextlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


loader = importlib.machinery.SourceFileLoader(
    "archive_hf_model", str(Path(__file__).resolve().parents[1] / "scripts/ai/archive-hf-model")
)
spec = importlib.util.spec_from_loader(loader.name, loader)
archive = importlib.util.module_from_spec(spec)
sys.modules[loader.name] = archive
loader.exec_module(archive)


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.args = argparse.Namespace(
            hf_repo="owner/model", revision="release", include=["*.gguf", "README.md"],
            exclude=["skip*"], force_download=False, limit=False, max_workers=None,
        )
        self.paths = archive.ArchivePaths(*([self.root] * 6))
        self.info = {"sha": "a" * 40, "siblings": [
            {"rfilename": name} for name in
            ["model.i1-Q4_K_S.gguf", "README.md", "skip.gguf", "model.safetensors"]
        ], "card_data": {"base_model": "owner/source", "base_model_relation": "quantized"}}

    def download(self, command):
        self.assertEqual(command[command.index("--revision") + 1], self.info["sha"])
        for name in ["model.i1-Q4_K_S.gguf", "README.md"]:
            (self.root / name).write_bytes(b"example model bytes")
        (self.root / "unrelated.gguf").write_text("old file")

    def test_pinned_download_hashes_scope_and_history(self):
        with patch.object(archive, "require_command"), patch.object(archive, "model_info", return_value=self.info), patch.object(archive, "run_command", side_effect=self.download):
            archive.download_model(self.args, self.paths)
            archive.download_model(self.args, self.paths)
        records = list((self.root / archive.PROVENANCE_DIR).glob("*.json"))
        self.assertEqual(len(records), 2)
        record = json.loads(records[0].read_text())
        self.assertEqual(record["repository_commit"], "a" * 40)
        self.assertEqual(record["declared_base_model"], "owner/source")
        self.assertEqual(record["model_kinds"], ["quantized_gguf"])
        self.assertEqual(len(record["files"]), 2)
        for file in record["files"]:
            self.assertEqual(file["sha256"], hashlib.sha256(b"example model bytes").hexdigest())
            self.assertIn("/resolve/" + "a" * 40 + "/", file["source_url"])
        self.assertLessEqual(record["download_started_at"], record["download_completed_at"])

    def test_failure_does_not_publish_record(self):
        with patch.object(archive, "require_command"), patch.object(archive, "model_info", return_value=self.info), patch.object(archive, "run_command", side_effect=subprocess.CalledProcessError(1, "hf")):
            with self.assertRaises(subprocess.CalledProcessError):
                archive.download_model(self.args, self.paths)
        self.assertFalse((self.root / archive.PROVENANCE_DIR).exists())

    def test_classification_does_not_assume_all_gguf_quantized(self):
        self.assertEqual(archive.file_format("model.F16.gguf")["model_kind"], "gguf")
        self.assertIsNone(archive.file_format("model.safetensors")["quantization"])
        self.assertEqual(archive.file_format("model.i1-Q4_K_S.gguf")["quantization"], "Q4_K_S")

    def test_invalid_revision_response_fails(self):
        result = subprocess.CompletedProcess([], 0, '{"sha":"main","siblings":[]}')
        with patch.object(archive.subprocess, "run", return_value=result):
            with self.assertRaises(SystemExit):
                archive.model_info(self.args)

    def test_missing_file_does_not_publish_record(self):
        with self.assertRaises(SystemExit):
            archive.write_provenance(self.args, self.paths, self.info, ["absent.gguf"],
                                     "https://huggingface.co", "start", "end")
        self.assertFalse((self.root / archive.PROVENANCE_DIR).exists())


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.argv = ["archive-hf-model", "owner/model", "--local-root", str(self.root / "local"),
                     "--nas-root", str(self.root / "nas")]

    def args(self, *options):
        with patch.object(sys, "argv", self.argv + list(options)):
            return archive.parse_args()

    def info(self, *names):
        return {"sha": "a" * 40, "siblings": [{"rfilename": n} for n in names]}

    def test_paths_match_under_both_roots(self):
        args = self.args()
        for layout, prefix in [("source", "source/huggingface"), ("gguf", "inference/gguf")]:
            paths = archive.build_paths(args, "model", layout)
            relative = Path(prefix) / "owner/model"
            self.assertEqual(paths.local_model, args.local_root / relative)
            self.assertEqual(paths.nas_model, args.nas_root / relative)
            checksums = Path("metadata/checksums") / prefix / "owner/model.sha256"
            self.assertEqual(paths.local_checksum, args.local_root / checksums)
            self.assertEqual(paths.checksum, args.nas_root / checksums)

    def test_routing_uses_selected_files_and_preserves_mixed_source(self):
        info = self.info("model.safetensors", "model-Q4_K_M.gguf", "README.md")
        for options, expected in [([], "source"), (["--include", "*.gguf", "--include", "*.md"], "gguf"),
                                  (["--exclude", "*.gguf"], "source"), (["--include", "*.md"], "source")]:
            self.assertEqual(archive.choose_layout(self.args(*options), {"download"}, "model", info), expected)

    def test_offline_detection_and_ambiguity(self):
        args = self.args("--sync")
        gguf = archive.build_paths(args, "model", "gguf")
        gguf.local_model.mkdir(parents=True)
        self.assertEqual(archive.choose_layout(args, {"sync"}, "model"), "gguf")
        source = archive.build_paths(args, "model", "source")
        source.local_model.mkdir(parents=True)
        with self.assertRaisesRegex(SystemExit, "both layouts"):
            archive.choose_layout(args, {"sync"}, "model")
        args.layout = "source"
        self.assertEqual(archive.choose_layout(args, {"sync"}, "model"), "source")

    def test_checksum_only_finds_nas(self):
        args = self.args("--checksum")
        archive.build_paths(args, "model", "gguf").nas_model.mkdir(parents=True)
        self.assertEqual(archive.choose_layout(args, {"checksum"}, "model"), "gguf")

    def test_explicit_archive_checksum_does_not_need_layout(self):
        tar = self.root / "saved.tar.zst"
        tar.write_bytes(b"archive")
        args = self.args("--archive-checksum", "--archive-path", str(tar))
        layout = archive.choose_layout(args, {"archive_checksum"}, "model")
        self.assertEqual(archive.build_paths(args, "model", layout).local_archive, tar)

    def test_explicit_local_directory_is_preserved(self):
        existing = self.root / "old-model"
        existing.mkdir()
        (existing / "model.gguf").write_text("weights")
        args = self.args("--sync", "--local-model-dir", str(existing))
        layout = archive.choose_layout(args, {"sync"}, "model")
        self.assertEqual(layout, "gguf")
        self.assertEqual(archive.build_paths(args, "model", layout).local_model, existing)

    def test_gguf_layout_rejects_source_selection_or_existing_source(self):
        args = self.args("--layout", "gguf")
        with self.assertRaisesRegex(SystemExit, "source-format weights"):
            archive.choose_layout(args, {"download"}, "model", self.info("model.safetensors"))
        paths = archive.build_paths(args, "model", "gguf")
        paths.local_model.mkdir(parents=True)
        (paths.local_model / "model.safetensors").write_text("preserve me")
        with self.assertRaisesRegex(SystemExit, "source-format weights"):
            archive.choose_layout(args, {"download"}, "model", self.info("model.gguf"))
        self.assertEqual((paths.local_model / "model.safetensors").read_text(), "preserve me")

    def test_download_sync_checksums_and_offline_rerun(self):
        for filename, layout in [("model.safetensors", "source"), ("model.gguf", "gguf")]:
            info = self.info(filename, "README.md")
            paths = archive.build_paths(self.args(), "model", layout)

            def command(cmd):
                if cmd[0] == "hf":
                    self.assertEqual(cmd[cmd.index("--revision") + 1], info["sha"])
                    destination = Path(cmd[cmd.index("--local-dir") + 1])
                    self.assertEqual(destination, paths.local_model)
                    destination.mkdir(parents=True, exist_ok=True)
                    (destination / filename).write_bytes(b"weights")
                    (destination / "README.md").write_text("model card")
                elif cmd[0] == "rsync":
                    shutil.copytree(cmd[-2], cmd[-1], dirs_exist_ok=True)
                else:
                    self.fail(f"unexpected command: {cmd}")

            with patch.object(sys, "argv", self.argv), patch.object(archive, "model_info", return_value=info) as get_info, patch.object(archive, "require_command"), patch.object(archive, "run_command", side_effect=command), patch.object(archive, "summarize"), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(archive.main(), 0)
                get_info.assert_called_once()
            for root, manifest in [(paths.local_model, paths.local_checksum), (paths.nas_model, paths.checksum)]:
                for line in manifest.read_text().splitlines():
                    digest, relative = line.split("  ", 1)
                    self.assertEqual(digest, hashlib.sha256((root / relative).read_bytes()).hexdigest())
                self.assertIn(filename, manifest.read_text())
                self.assertIn("archive-provenance", manifest.read_text())
            with patch.object(sys, "argv", self.argv + ["--sync", "--checksum", "--layout", layout]), patch.object(archive, "model_info") as get_info, patch.object(archive, "require_command"), patch.object(archive, "run_command", side_effect=command), patch.object(archive, "summarize"), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(archive.main(), 0)
                get_info.assert_not_called()
            self.assertTrue((paths.local_model / filename).exists())


if __name__ == "__main__":
    unittest.main()
