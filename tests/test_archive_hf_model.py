"""Offline provenance checks: python3 -m unittest discover -s tests."""
import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path
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
        self.paths = archive.ArchivePaths(*([self.root] * 5))
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


if __name__ == "__main__":
    unittest.main()
