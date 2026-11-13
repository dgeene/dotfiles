"""Real FFmpeg integration tests plus GPU command tests (no GPU required)."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

COMMAND = Path(__file__).resolve().parents[1] / 'bin/video-to-mp4'
MODULE = runpy.run_path(str(COMMAND))


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg tools required')
class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, name, codec='mpeg4', size='96x64', sar='1', audio=True):
        path = self.root / name
        command = ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                   f'testsrc=size={size}:rate=10:duration=0.6']
        if audio:
            command += ['-f', 'lavfi', '-i', 'sine=duration=0.6', '-c:a', 'wmav2' if codec == 'wmv2' else 'libmp3lame']
        command += ['-vf', f'setsar={sar}', '-c:v', codec, '-threads', '1', str(path)]
        subprocess.run(command, check=True)
        return path

    def cli(self, *args, status=0):
        result = subprocess.run([str(COMMAND), *map(str, args)], cwd=self.root,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        return result

    def probe(self, path):
        return json.loads(subprocess.check_output(['ffprobe', '-v', 'error',
                          '-show_streams', '-of', 'json', str(path)]))['streams']

    def test_legacy_formats_and_faststart(self):
        for name, codec in [('old.flv', 'flv'), ('windows.wmv', 'wmv2'),
                            ('movie.avi', 'mpeg4'), ('web.webm', 'libvpx')]:
            with self.subTest(name=name):
                source = self.fixture(name, codec, audio=codec != 'libvpx')
                before = hashlib.sha256(source.read_bytes()).digest()
                self.cli(source)
                output = source.with_name(source.stem + '.web.mp4')
                streams = self.probe(output)
                self.assertEqual(streams[0]['codec_name'], 'h264')
                self.assertEqual(streams[0]['pix_fmt'], 'yuv420p')
                self.assertEqual((streams[0]['width'], streams[0]['height']), (96, 64))
                self.assertEqual(streams[0]['r_frame_rate'], '10/1')
                if codec != 'libvpx':
                    self.assertEqual(streams[1]['codec_name'], 'aac')
                    self.assertEqual(streams[1]['channels'], 2)
                data = output.read_bytes()
                self.assertLess(data.index(b'moov'), data.index(b'mdat'))
                self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), before)

    def test_odd_dimensions_and_display_aspect(self):
        source = self.fixture('odd.mkv', 'ffv1', size='95x63', sar='4/3', audio=False)
        self.cli(source)
        video = self.probe(self.root / 'odd.web.mp4')[0]
        self.assertEqual((video['width'], video['height']), (96, 64))
        self.assertEqual(Fraction(video['display_aspect_ratio'].replace(':', '/')), Fraction(95 * 4, 63 * 3))

    def test_batch_preview_recursion_collisions_and_failures(self):
        source = self.fixture('top.avi')
        nested = self.root / 'nested'
        nested.mkdir()
        source.rename(nested / source.name)
        self.assertIn('0 planned', self.cli('--dry-run').stdout)
        self.assertIn('1 planned', self.cli('-r', '--dry-run').stdout)
        self.assertFalse(list(self.root.rglob('*.mp4')))
        self.cli('-r')
        output = nested / 'top.web.mp4'
        before = output.read_bytes()
        self.assertIn('1 skipped', self.cli('-r').stdout)
        self.assertEqual(output.read_bytes(), before)
        bad = self.root / 'bad.wmv'
        bad.write_bytes(b'broken video')
        self.cli(status=1)
        self.assertEqual(bad.read_bytes(), b'broken video')
        self.assertFalse((self.root / 'bad.web.mp4').exists())
        self.assertFalse(list(self.root.rglob('.video-to-mp4-*')))

    def test_audio_only_and_output_symlink(self):
        source = self.root / 'sound.wma'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=duration=0.3',
                        '-c:a', 'wmav2', str(source)], check=True)
        self.cli(source)
        streams = self.probe(self.root / 'sound.web.mp4')
        self.assertEqual(len(streams), 1)
        self.assertEqual(streams[0]['codec_name'], 'aac')
        target = self.root / 'occupied.mp4'
        target.symlink_to('missing')
        self.assertIn('1 skipped', self.cli(source, '-o', target).stdout)
        self.assertTrue(target.is_symlink())

    def test_rotation_and_custom_output(self):
        original = self.fixture('landscape.mp4', audio=False)
        rotated = self.root / 'portrait.mov'
        subprocess.run(['ffmpeg', '-v', 'error', '-display_rotation:v:0', '90',
                        '-i', str(original), '-c', 'copy', str(rotated)], check=True)
        self.assertTrue(any(abs(data.get('rotation', 0)) == 90
                            for data in self.probe(rotated)[0].get('side_data_list', [])))
        self.cli(rotated, '-o', 'custom.mp4', '--quality', '18', '--preset', 'fast')
        video = self.probe(self.root / 'custom.mp4')[0]
        self.assertEqual((video['width'], video['height']), (64, 96))
        self.assertFalse(any(data.get('rotation', 0)
                             for data in video.get('side_data_list', [])))


class EncoderTests(unittest.TestCase):
    def args(self, encoder):
        return argparse.Namespace(encoder=encoder, quality=20, preset=None, device=None,
                                  audio_bitrate=160, deinterlace=False)

    def test_nvidia_and_amd_commands(self):
        args = self.args('nvidia')
        args.device = '1'
        options = MODULE['encoder_options'](args)
        self.assertIn('h264_nvenc', options[1])
        self.assertEqual(options[1][-2:], ['-gpu', '1'])
        args.encoder = 'amd'
        args.device = '/dev/dri/renderD129'
        with patch.dict(MODULE['encoder_options'].__globals__, amd_device=lambda requested: requested):
            encoder = MODULE['encoder_options'](args)
        cmd = MODULE['command'](Path('/input.avi'), Path('/output.mp4'),
                                {'index': 2}, {'index': 3}, args, encoder)
        self.assertIn('h264_vaapi', cmd)
        self.assertIn('/dev/dri/renderD129', cmd)
        self.assertIn('0:2', cmd)
        self.assertIn('0:3', cmd)
        self.assertIn('hwupload', cmd[cmd.index('-vf') + 1])

    def test_gpu_preflight_failure_leaves_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.avi'
            source.write_bytes(b'original')
            namespace = MODULE['main'].__globals__
            def unavailable(encoder):
                raise subprocess.CalledProcessError(1, 'ffmpeg')
            with patch.dict(namespace, streams_for=lambda path: ({'index': 0}, None),
                            check_encoder=unavailable), patch('shutil.which', return_value='/ffmpeg'), \
                    patch('sys.argv', ['video-to-mp4', str(source), '--encoder', 'nvidia']):
                with self.assertRaisesRegex(RuntimeError, 'encoder unavailable'):
                    MODULE['main']()
            self.assertEqual(source.read_bytes(), b'original')
            self.assertEqual(list(Path(directory).iterdir()), [source])


if __name__ == '__main__':
    unittest.main()
