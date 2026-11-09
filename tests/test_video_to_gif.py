"""Real FFmpeg integration tests for the video-to-gif CLI."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

COMMAND = Path(__file__).resolve().parents[1] / 'bin/video-to-gif'


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg tools required')
class VideoToGifTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.video = self.root / 'demo recording.MOV'
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-f', 'lavfi', '-i',
                        'testsrc2=size=192x108:rate=20:duration=2', '-c:v', 'mpeg4',
                        str(self.video)], check=True)

    def cli(self, *args, status=0):
        result = subprocess.run([str(COMMAND), *map(str, args)], cwd=self.root,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        return result

    def probe(self, path):
        return json.loads(subprocess.check_output([
            'ffprobe', '-v', 'error', '-count_frames', '-show_streams',
            '-of', 'json', str(path)]))['streams'][0]

    def test_default_animation_source_preservation_and_collision(self):
        before = hashlib.sha256(self.video.read_bytes()).digest()
        self.cli(self.video)
        output = self.video.with_suffix('.gif')
        info = self.probe(output)
        self.assertEqual((info['width'], info['height']), (192, 108))
        self.assertEqual(int(info['nb_read_frames']), 20)
        self.assertAlmostEqual(float(info['duration']), 2.0, places=1)
        self.assertIn(b'NETSCAPE2.0\x03\x01\x00\x00', output.read_bytes())
        self.assertEqual(hashlib.sha256(self.video.read_bytes()).digest(), before)
        existing = output.read_bytes()
        self.cli(self.video, status=2)
        self.assertEqual(output.read_bytes(), existing)
        self.assertFalse(list(self.root.glob('.video-to-gif-*')))

    def test_trim_resize_and_mp4(self):
        video = self.root / '-recording.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(self.video), '-c', 'copy',
                        str(video)], check=True)
        self.cli('--start', '0.5', '--duration', '0.8', '--width', '96', '--fps', '5',
                 '-o', 'trimmed.gif', '--', video.name)
        info = self.probe(self.root / 'trimmed.gif')
        self.assertEqual((info['width'], info['height']), (96, 54))
        self.assertEqual(int(info['nb_read_frames']), 4)
        self.assertAlmostEqual(float(info['duration']), 0.8, places=1)

    def test_phone_rotation(self):
        rotated = self.root / 'phone.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-display_rotation:v:0', '90',
                        '-i', str(self.video), '-c', 'copy', str(rotated)], check=True)
        self.assertTrue(any(abs(data.get('rotation', 0)) == 90
                            for data in self.probe(rotated).get('side_data_list', [])))
        self.cli(rotated, '--width', '54')
        info = self.probe(rotated.with_suffix('.gif'))
        self.assertEqual((info['width'], info['height']), (54, 96))

    def test_dry_run_invalid_arguments_and_broken_symlink(self):
        self.cli(self.video, '--dry-run')
        self.assertEqual(list(self.root.iterdir()), [self.video])
        for option, value in [('--start', '-1'), ('--start', 'nan'), ('--duration', '0'),
                              ('--duration', 'inf'), ('--width', '0'), ('--fps', '51')]:
            self.cli(self.video, option, value, status=2)
        self.video.with_suffix('.gif').symlink_to('missing')
        self.cli(self.video, status=2)
        self.assertTrue(self.video.with_suffix('.gif').is_symlink())

    def test_failed_conversion_and_empty_trim_leave_no_output(self):
        self.cli(self.video, '--start', '20', status=1)
        self.assertFalse(self.video.with_suffix('.gif').exists())
        corrupt = self.root / 'broken.mov'
        corrupt.write_bytes(b'not video')
        self.cli(corrupt, status=1)
        self.assertEqual(corrupt.read_bytes(), b'not video')
        self.assertFalse(corrupt.with_suffix('.gif').exists())
        self.assertFalse(list(self.root.glob('.video-to-gif-*')))


if __name__ == '__main__':
    unittest.main()
