"""Integration tests using real FFmpeg and generated PNGs (no image packages)."""
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib

COMMAND = Path(__file__).resolve().parents[1] / 'bin/png-to-jpeg'


def png(path, rgba=(255, 0, 0, 255)):
    def chunk(kind, data):
        return (struct.pack('!I', len(data)) + kind + data
                + struct.pack('!I', zlib.crc32(kind + data)))
    width, height = 33, 25
    data = b'\x89PNG\r\n\x1a\n'
    data += chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 6, 0, 0, 0))
    data += chunk(b'IDAT', zlib.compress((b'\0' + bytes(rgba) * width) * height))
    data += chunk(b'IEND', b'')
    path.write_bytes(data)
    return data


@unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg required')
class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_cli(self, *args, status=0):
        result = subprocess.run([str(COMMAND), *args], cwd=self.root,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        return result

    def test_recursive_transparency_and_originals(self):
        nested = self.root / 'nested folder'
        nested.mkdir()
        for name, alpha, expected in [('white.PNG', 0, (255, 255, 255)),
                                      ('-half %.png', 128, (255, 127, 127)),
                                      ('.opaque.png', 255, (255, 0, 0))]:
            source = nested / name
            original = png(source, (255, 0, 0, alpha))
            self.run_cli()
            self.assertFalse(source.exists())
            self.assertEqual((nested / 'PNG' / name).read_bytes(), original)
            raw = subprocess.check_output([
                'ffmpeg', '-v', 'error', '-i', str(source.with_suffix('.jpg')),
                '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
            self.assertEqual(len(raw), 33 * 25 * 3)
            self.assertTrue(all(abs(raw[i] - expected[i]) <= 4 for i in range(3)), raw[:3])
        self.assertIn('0 converted', self.run_cli().stdout)

    def test_preview_no_recursion_and_conflicts(self):
        nested = self.root / 'nested'
        nested.mkdir()
        png(nested / 'child.png')
        original = png(self.root / 'photo.png')
        self.run_cli('--dry-run')
        self.assertFalse((self.root / 'PNG').exists())
        self.assertFalse((nested / 'child.jpg').exists())
        (self.root / 'photo.JPEG').write_bytes(b'existing')
        self.run_cli('--no-recursive')
        self.assertEqual((self.root / 'photo.png').read_bytes(), original)
        self.assertEqual((self.root / 'photo.JPEG').read_bytes(), b'existing')
        self.assertTrue((nested / 'child.png').exists())

    def test_corrupt_input_archive_collision_and_symlinks(self):
        (self.root / 'bad.png').write_bytes(b'not a png')
        png(self.root / 'good.png')
        png(self.root / 'taken.png')
        archive = self.root / 'PNG'
        archive.mkdir()
        (archive / 'taken.png').write_bytes(b'existing archive')
        (self.root / 'link.png').symlink_to('good.png')
        self.run_cli(status=1)
        self.assertTrue((self.root / 'good.jpg').is_file())
        self.assertFalse((self.root / 'bad.jpg').exists())
        self.assertTrue((self.root / 'bad.png').exists())
        self.assertTrue((self.root / 'taken.png').exists())
        self.assertEqual((archive / 'taken.png').read_bytes(), b'existing archive')
        self.assertTrue((self.root / 'link.png').is_symlink())
        self.assertFalse(list(self.root.glob('.png-to-jpeg-*')))

    def test_invalid_quality(self):
        self.run_cli('--quality', '0', status=2)


if __name__ == '__main__':
    unittest.main()
