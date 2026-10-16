"""The LilyPond master, its MusicXML export, and the content comparison."""
from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest
from xml.etree import ElementTree as E

import compare_musicxml as c
import ly_to_musicxml as x

ROOT = Path(__file__).resolve().parents[1]
MUSICXML = ROOT / 'score' / f'{x.STEM}.musicxml'


@unittest.skipUnless(shutil.which('lilypond'), 'LilyPond is not installed')
class LilyPondExportTests(unittest.TestCase):
    def test_checked_in_musicxml_is_current(self):
        """score/*.musicxml must be exactly what ly/ generates (run `make musicxml`)."""
        with tempfile.TemporaryDirectory() as folder:
            out = x.export(Path(folder) / 'score.musicxml', workdir=Path(folder) / 'work')
            self.assertEqual(out.read_bytes(), MUSICXML.read_bytes())


class ComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = E.parse(MUSICXML)

    def diff_after(self, mutate):
        root = deepcopy(self.tree.getroot())
        mutate(root)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'changed.musicxml'
            E.ElementTree(root).write(path, encoding='UTF-8', xml_declaration=True)
            return c.compare(c.score_model(MUSICXML), c.score_model(path))

    def test_identical_scores_have_no_differences(self):
        self.assertEqual(self.diff_after(lambda root: None), {})

    def test_changed_pitch_is_reported(self):
        def mutate(root):
            step = root.find('part[@id="P12"]/measure[@number="2"]/note/pitch/step')
            step.text = 'F' if step.text != 'F' else 'G'
        self.assertIn('note', self.diff_after(mutate))

    def test_reordered_directions_are_equivalent(self):
        def mutate(root):
            measure = root.find('part[@id="P1"]/measure[@number="1"]')
            directions = measure.findall('direction')
            for d in directions:
                measure.remove(d)
            for d in reversed(directions):
                measure.insert(1, d)
        self.assertEqual(self.diff_after(mutate), {})

    def test_moved_dynamic_is_reported(self):
        def mutate(root):
            measure = root.find('part[@id="P12"]/measure[@number="1"]')
            dynamic = next(d for d in measure.findall('direction') if d.find('direction-type/dynamics') is not None)
            measure.remove(dynamic)
            measure.append(dynamic)  # now at the barline instead of the downbeat
        self.assertIn('direction', self.diff_after(mutate))


if __name__ == '__main__':
    unittest.main()
