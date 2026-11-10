##### test_converting.py ######

# unit tests for MusicXML export. Each exported measure is measured the way notation
# programs read it (note type + dots + tuplet ratio) and must exactly fill the bar,
# with every tuplet bracket complete and using a single ratio.
# run from inner/src: python -m unittest tests.test_converting

###### IMPORT ######

import os
import sys
import random
import tempfile
import unittest
import xml.etree.ElementTree as ET
from fractions import Fraction
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import converting

####### INITIALIZE ######

TYPE_QL = {
    'breve': Fraction(8), 'whole': Fraction(4), 'half': Fraction(2), 'quarter': Fraction(1),
    'eighth': Fraction(1, 2), '16th': Fraction(1, 4), '32nd': Fraction(1, 8),
    '64th': Fraction(1, 16), '128th': Fraction(1, 32), '256th': Fraction(1, 64),
}

###### METHODS ######

def makeNote(time, duration, pitch=30):
    return SimpleNamespace(time=time, duration=duration, pitch=pitch)

def nominalLength(noteElement):
    noteType = noteElement.find('type')
    if noteType is None:
        return None
    length = TYPE_QL[noteType.text]
    dotValue = length
    for _ in noteElement.findall('dot'):
        dotValue /= 2
        length += dotValue
    return length

def findProblems(filePath, measureQL):
    '''
    Returns a list of human-readable problems found in an exported file.
    '''
    problems = []
    root = ET.parse(filePath).getroot()
    for part in root.findall('part'):
        divisions = None
        for measure in part.findall('measure'):
            label = f"measure {measure.get('number')}"
            attributes = measure.find('attributes')
            if attributes is not None and attributes.find('divisions') is not None:
                divisions = int(attributes.find('divisions').text)

            total = Fraction(0)
            tupletOpen = None  # [ratio, filled length, needed length]
            for noteElement in measure.findall('note'):
                if noteElement.find('chord') is not None:
                    continue
                storedLength = Fraction(int(noteElement.find('duration').text), divisions)
                rest = noteElement.find('rest')
                if rest is not None and rest.get('measure') == 'yes':
                    total += storedLength
                    continue

                length = nominalLength(noteElement)
                if length is None:
                    problems.append(f'{label}: note without a type')
                    continue
                timeMod = noteElement.find('time-modification')
                tupletTypes = [t.get('type') for t in noteElement.findall('notations/tuplet')]

                if timeMod is not None:
                    actual = int(timeMod.find('actual-notes').text)
                    normal = int(timeMod.find('normal-notes').text)
                    normalType = timeMod.find('normal-type')
                    unit = TYPE_QL[normalType.text] if normalType is not None else TYPE_QL[noteElement.find('type').text]
                    ratio = (actual, normal, unit)
                    if 'start' in tupletTypes:
                        if tupletOpen is not None:
                            problems.append(f'{label}: tuplet started before the previous one finished')
                        tupletOpen = [ratio, Fraction(0), actual * unit]
                    elif tupletOpen is None:
                        problems.append(f'{label}: tuplet note outside a bracket')
                        tupletOpen = [ratio, Fraction(0), actual * unit]
                    if tupletOpen[0] != ratio:
                        problems.append(f'{label}: mixed tuplet ratios in one bracket')
                    tupletOpen[1] += length
                    if 'stop' in tupletTypes:
                        if tupletOpen[1] != tupletOpen[2]:
                            problems.append(f'{label}: incomplete tuplet ({tupletOpen[1]} of {tupletOpen[2]})')
                        tupletOpen = None
                    length = length * normal / actual
                elif tupletOpen is not None:
                    problems.append(f'{label}: tuplet bracket never closed')
                    tupletOpen = None

                if length != storedLength:
                    problems.append(f'{label}: written note value {length} disagrees with stored duration {storedLength}')
                total += length

            if tupletOpen is not None:
                problems.append(f'{label}: tuplet bracket never closed')
            if total != measureQL:
                problems.append(f'{label}: holds {total} quarter notes, expected {measureQL}')
    return problems

###### TESTS ######

class TestMusicXMLMeasures(unittest.TestCase):

    def setUp(self):
        self.tempDir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tempDir.cleanup()

    def export(self, noteMap, beatLength, numerator=4, denominator=4):
        filePath = os.path.join(self.tempDir.name, 'score.musicxml')
        if os.path.exists(filePath):
            os.remove(filePath)
        converting.createMusicXMLFromNotes(noteMap, filePath, 120, numerator, denominator,
                                           beatLength, 'C', 'Ionian (maj.)')
        return filePath, Fraction(4 * numerator, denominator)

    def assertMeasuresRegular(self, noteMap, beatLength, numerator=4, denominator=4):
        filePath, measureQL = self.export(noteMap, beatLength, numerator, denominator)
        problems = findProblems(filePath, measureQL)
        self.assertEqual(problems, [], f'beatLength={beatLength} {numerator}/{denominator} notes={noteMap}')

    def testSameOnsetDifferentLengths(self):
        self.assertMeasuresRegular({'red': [makeNote(0, 4, 30), makeNote(0, 2, 34)]}, 4)

    def testSameOnsetDifferentTies(self):
        # one note carried over the bar line, another starting fresh on the downbeat
        self.assertMeasuresRegular({'red': [makeNote(12, 8, 30), makeNote(16, 4, 34)]}, 4)

    def testTripletOddLength(self):
        self.assertMeasuresRegular({'red': [makeNote(0, 5)]}, 3)

    def testTripletOffbeatQuarter(self):
        self.assertMeasuresRegular({'red': [makeNote(1, 3)]}, 3)

    def testQuintupletOddLength(self):
        self.assertMeasuresRegular({'red': [makeNote(0, 7)]}, 5)

    def testSeptupletOffbeat(self):
        self.assertMeasuresRegular({'red': [makeNote(2, 3)]}, 7)

    def testTripletAcrossBarLine(self):
        self.assertMeasuresRegular({'red': [makeNote(10, 4)]}, 3)

    def testCompoundMeterTriplet(self):
        self.assertMeasuresRegular({'red': [makeNote(1, 2)]}, 3, 6, 8)

    def testEmptyScore(self):
        self.assertMeasuresRegular({'red': []}, 3)

    def testRandomGrids(self):
        rng = random.Random(1)
        signatures = [(4, 4), (3, 4), (6, 8), (5, 4), (2, 2)]
        for beatLength in range(1, 9):
            for numerator, denominator in signatures:
                for _ in range(3):
                    measureTiles = beatLength * numerator
                    notes = []
                    for _ in range(rng.randint(1, 12)):
                        notes.append(makeNote(
                            rng.randint(0, measureTiles * 3),
                            rng.randint(1, measureTiles + beatLength),
                            rng.randint(20, 45),
                        ))
                    with self.subTest(beatLength=beatLength, signature=f'{numerator}/{denominator}'):
                        self.assertMeasuresRegular({'red': notes, 'blue': notes[::2]},
                                                   beatLength, numerator, denominator)

if __name__ == '__main__':
    unittest.main()
