import tempfile
import unittest
from pathlib import Path
from organizer import apply, category, plan


class OrganizerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'inbox'
        self.destination = Path(self.temp.name) / 'organized'
        self.source.mkdir()

    def test_preview_does_not_create_destination(self):
        (self.source / 'demo.PDF').write_text('demo')
        entries = plan(self.source, self.destination)
        self.assertEqual(entries[0]['category'], 'Documents')
        self.assertFalse(self.destination.exists())

    def test_copy_verifies_and_retains_original(self):
        original = self.source / 'notes.txt'
        original.write_text('hello')
        results = apply(plan(self.source, self.destination))
        self.assertEqual(results[0]['status'], 'copied-verified')
        self.assertEqual(original.read_text(), 'hello')
        self.assertEqual((self.destination / 'Documents' / 'notes.txt').read_text(), 'hello')

    def test_collision_never_overwrites(self):
        (self.source / 'notes.txt').write_text('new')
        folder = self.destination / 'Documents'
        folder.mkdir(parents=True)
        (folder / 'notes.txt').write_text('old')
        results = apply(plan(self.source, self.destination))
        self.assertEqual(results[0]['status'], 'skip-existing')
        self.assertEqual((folder / 'notes.txt').read_text(), 'old')

    def test_overlap_rejected(self):
        for target in (self.source, self.source / 'child', self.source.parent):
            with self.assertRaises(ValueError):
                plan(self.source, target)

    def test_unknown_extension_and_directories(self):
        (self.source / 'nested').mkdir()
        (self.source / '.hidden').write_text('skip')
        (self.source / 'record.bin').write_bytes(b'123')
        entries = plan(self.source, self.destination)
        self.assertEqual(len(entries), 1)
        self.assertEqual(category(Path('record.bin')), 'Other')

    def test_repeated_run_is_idempotent(self):
        (self.source / 'app.py').write_text('print(1)')
        apply(plan(self.source, self.destination))
        self.assertEqual(apply(plan(self.source, self.destination))[0]['status'], 'skip-existing')


if __name__ == '__main__':
    unittest.main()
