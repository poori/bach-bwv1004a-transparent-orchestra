"""Regression checks for the failures found during editorial review."""
from copy import deepcopy
import unittest
from xml.etree import ElementTree as E
import validate_outputs as v

class MusicalValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = E.parse(v.ROOT / 'score' / f'{v.STEM}.musicxml').getroot()

    def test_current_source_and_phrase_coverage(self):
        report = v.source_and_phrase_metrics(self.root)
        self.assertEqual(report['source_notes'], 3083)
        self.assertEqual(report['uncovered_source_notes'], [])
        self.assertEqual(report['misplaced_thematic_notes'], [])

    def test_active_accompaniment_is_not_melody(self):
        root = deepcopy(self.root)
        for n in root.findall('part[@id="P12"]/measure[@number="249"]/note[pitch]'):
            n.find('pitch/step').text = 'F'
        self.assertTrue(v.source_and_phrase_metrics(root)['misplaced_thematic_notes'])

    def test_missing_source_note(self):
        root = deepcopy(self.root)
        for m in root.findall('part/measure[@number="1"]'):
            for n in m.findall('note[pitch]'):
                if v.pitch_to_midi(n) % 12 == 9:
                    n.remove(n.find('pitch'))
                    E.SubElement(n,'rest')
        self.assertTrue(v.source_and_phrase_metrics(root)['uncovered_source_notes'])

    def test_short_tonic_over_dominant(self):
        root = deepcopy(self.root)
        m = root.find('part[@id="P9"]/measure[@number="176"]')
        n = m.find('note[pitch]')
        pitch = n.find('pitch')
        pitch.find('step').text = 'C'  # written C sounds D
        if pitch.find('alter') is not None:
            pitch.remove(pitch.find('alter'))
        n.find('duration').text = '192'
        for child in list(m):
            if child.tag in {'note','forward','backup'}:
                m.remove(child)
        forward = E.SubElement(m,'forward')
        E.SubElement(forward,'duration').text = '768'
        m.append(n)
        self.assertTrue(v.brass_harmony_violations(root))

    def test_resolution_inside_cadence_bar_is_allowed(self):
        self.assertEqual(v.brass_harmony_violations(self.root), [])

    def test_inner_voice_extension_collision(self):
        root = deepcopy(self.root)
        n = root.find('part[@id="P14"]/measure[@number="215"]/note[pitch]')
        n.find('duration').text = '1152'
        self.assertTrue(any(x['bar'] == 215 for x in v.cross_relation_violations(root)))

    def test_pickup_is_two_beats(self):
        root = deepcopy(self.root)
        n = root.find('part[@id="P5"]/measure[@number="1"]/note')
        n.find('duration').text = '1152'
        n.find('type').text = 'half'
        E.SubElement(n,'dot')
        with self.assertRaisesRegex(AssertionError,'Incomplete measure'):
            v.validate_musicxml_rhythm(root)

    def test_tripling_checks_double_bass_pitch_and_timing(self):
        root = E.Element('score-partwise')
        for pid,pitch in [('P5','D'),('P6',None),('P15','D'),('P16','A')]:
            part = E.SubElement(root,'part',id=pid)
            for bar in range(1,258):
                m = E.SubElement(part,'measure',number=str(bar))
                if bar == 1 and pitch:
                    n = E.SubElement(m,'note')
                    p = E.SubElement(n,'pitch')
                    E.SubElement(p,'step').text = pitch
                    E.SubElement(p,'octave').text = '3'
                    E.SubElement(n,'duration').text = '384'
        self.assertEqual(v.bass_tripling_metrics(root), [])
        bass = root.find('part[@id="P16"]/measure[@number="1"]')
        bass.find('note/pitch/step').text = 'D'
        self.assertEqual(v.bass_tripling_metrics(root)[0]['ticks'],384)
        forward = E.Element('forward')
        E.SubElement(forward,'duration').text = '384'
        bass.insert(0,forward)
        self.assertEqual(v.bass_tripling_metrics(root), [])

if __name__ == '__main__':
    unittest.main()
