"""Publication readiness rejects partial files and changed candidate archives."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_reference_release as release


class ReferenceReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in release.ARCHIVE_NAMES:
            with zipfile.ZipFile(self.root / name, 'w', zipfile.ZIP_STORED) as archive:
                archive.writestr('fixture.txt', b'original fixture')
        (self.root / release.README_NAME).write_text('Synthetic candidate\n')
        self.bind_archives()

    def checksums(self):
        (self.root / release.CHECKSUM_NAME).write_text(''.join(
            release.sha(self.root / name) + '  ' + name + '\n'
            for name in sorted(release.ASSET_NAMES) if name != release.CHECKSUM_NAME))

    def bind_archives(self):
        release.write_json(self.root / release.REPORT_NAME, {
            'source_commit': '0' * 40,
            'artifacts': [release.record(self.root / name) for name in release.ARCHIVE_NAMES]})
        self.checksums()

    def test_valid_exact_six_asset_set(self):
        result = release.verify_release(self.root)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['assets']), 6)
        self.assertEqual(len(result['archives']), 3)

    def test_extra_partial_fails_even_when_added_to_checksums(self):
        partial = self.root / (release.ARCHIVE_NAMES[1] + '.partial')
        partial.write_bytes(b'PK incomplete archive')
        with (self.root / release.CHECKSUM_NAME).open('a') as stream:
            stream.write(release.sha(partial) + '  ' + partial.name + '\n')
        with self.assertRaisesRegex(RuntimeError, 'file set differs'):
            release.verify_release(self.root)
        self.assertTrue(partial.exists(), 'Failure must preserve diagnostic artifacts')

    def test_missing_checksum_fails(self):
        path = self.root / release.CHECKSUM_NAME
        path.write_text('\n'.join(path.read_text().splitlines()[1:]) + '\n')
        with self.assertRaisesRegex(RuntimeError, 'exactly the five'):
            release.verify_release(self.root)

    def test_changed_valid_archive_fails_build_report_binding(self):
        with zipfile.ZipFile(self.root / release.ARCHIVE_NAMES[0], 'w') as archive:
            archive.writestr('changed.txt', b'changed fixture')
        self.checksums()
        with self.assertRaisesRegex(RuntimeError, 'Build report archive size/hash differs'):
            release.verify_release(self.root)

    def test_crc_corruption_fails_even_with_matching_whole_file_hash(self):
        path = self.root / release.ARCHIVE_NAMES[0]
        data = bytearray(path.read_bytes())
        name_length, extra_length = struct.unpack_from('<HH', data, 26)
        data[30 + name_length + extra_length] ^= 1
        path.write_bytes(data)
        self.bind_archives()
        with self.assertRaisesRegex(RuntimeError, 'Archive CRC failed'):
            release.verify_release(self.root)


if __name__ == '__main__':
    unittest.main()
