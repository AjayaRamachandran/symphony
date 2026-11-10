# utils/converting.py
# module for handling converting to various file formats.
###### IMPORT ######

import pretty_midi
from os import path
from music21 import stream, note, tempo, meter, clef, key as keys, tie, metadata, duration as m21duration, chord
from fractions import Fraction

###### INTERNAL MODULES ######

from console_controls.console import *

###### METHODS / CLASSES ######

def createMidiFromNotes(noteMap: dict, filename: str, instrumentName="Acoustic Grand Piano"):
    '''
    fields:
        noteMap (dict) - noteMap data\n
        filename (string) - path of output folder\n
        instrumentName (string) - instrument type to use\n
    outputs: string (the output file path)

    Generates a MIDI file from a 1.1 noteMap and saves it to a file.
    '''

    base, ext = path.splitext(filename)
    # Resolve name conflicts
    candidate = base + ext
    counter = 1
    while path.exists(candidate):
        candidate = f"{base} ({counter}){ext}"
        counter += 1
    
    midi = pretty_midi.PrettyMIDI()
    instrument = pretty_midi.Instrument(program=pretty_midi.instrument_name_to_program(instrumentName))

    for color, channel in noteMap.items():
        for note in channel:
            pitch = note.pitch + 35
            start = note.time / 4
            end = start + note.duration / 4
            velocity = 64

            midiNote = pretty_midi.Note(velocity=velocity, pitch=pitch, start=start, end=end)
            instrument.notes.append(midiNote)

    midi.instruments.append(instrument)
    midi.write(candidate)
    return candidate

def splitIntoNoteValues(count: int, unitQL: Fraction):
    '''
    fields:
        count (int) - number of units to cover\n
        unitQL (Fraction) - quarter length of one unit\n
    outputs: list of music21 Durations

    Splits count units into the fewest notatable note values (at most double-dotted),
    longest first, so music21 never has to guess a complex duration.
    '''
    durations = []
    remaining = count
    while remaining > 0:
        for take in range(remaining, 0, -1):
            d = m21duration.Duration(quarterLength=take * unitQL)
            if d.type not in ('complex', 'inexpressible') and d.dots <= 2 and not d.tuplets:
                break
        # mark as deliberate so music21 doesn't merge pieces back across beat lines on export
        d.expressionIsInferred = False
        durations.append(d)
        remaining -= take
    return durations

def splitIntoBeatDurations(startTile: int, lengthTiles: int, beatLength: int, beatQL: Fraction):
    '''
    fields:
        startTile (int) - start of the span, in tiles from the start of the measure\n
        lengthTiles (int) - length of the span in tiles\n
        beatLength (int) - number of tiles per beat\n
        beatQL (Fraction) - quarter length of one beat\n
    outputs: list of music21 Durations (to be tied together)

    Converts a span of grid tiles into notated durations. When a beat is split into a
    non power of two (triplets, quintuplets, ...), the span is cut at beat lines so each
    partial beat gets its own beatLength:n tuplet that fills exactly that beat, while
    whole beats are written as ordinary notes.
    '''
    if beatLength & (beatLength - 1) == 0:
        return splitIntoNoteValues(lengthTiles, beatQL / beatLength)

    normalNotes = 1 << (beatLength.bit_length() - 1)
    tupletUnitQL = beatQL / normalNotes
    tupletUnitType = m21duration.Duration(quarterLength=tupletUnitQL).type

    durations = []
    position = startTile
    endTile = startTile + lengthTiles
    while position < endTile:
        if position % beatLength == 0 and endTile - position >= beatLength:
            wholeBeats = (endTile - position) // beatLength
            durations.extend(splitIntoNoteValues(wholeBeats, beatQL))
            position += wholeBeats * beatLength
        else:
            chunkEnd = min((position // beatLength + 1) * beatLength, endTile)
            for d in splitIntoNoteValues(chunkEnd - position, tupletUnitQL):
                d.appendTuplet(m21duration.Tuplet(
                    numberNotesActual=beatLength,
                    numberNotesNormal=normalNotes,
                    durationActual=tupletUnitType,
                    durationNormal=tupletUnitType,
                ))
                durations.append(d)
            position = chunkEnd
    return durations

def createMusicXMLFromNotes(
    noteMap: dict,
    filename: str,
    tempoBPM: int,
    timeSigNumerator: int,
    timeSigDenominator: int,
    beatLength: int,
    key: str,
    mode: str,
    colorClefMap: dict | None = None,
):
    '''
    fields:
        noteMap (dict) - {color: iterable of notes}\n
        filename (str) - output filepath (.musicxml)\n
        tempoBPM (int) - tempo in BPM\n
        timeSigNumerator (int) - beats per measure\n
        timeSigDenominator (int) - note value that gets the beat\n
        beatLength (int) - number of tiles per beat\n
        key (str) - tonic (e.g. "C#", "Db")\n
        mode (str) - musical mode\n
        colorClefMap (dict) - color → clef name (ex. "Treble", "Bass (8vb)")\n
    outputs: string (the output file path)

    Generates a MuseScore-compatible MusicXML notation file.
    '''
    
    base, ext = path.splitext(filename)
    if ext.lower() not in (".xml", ".musicxml"):
        ext = ".musicxml"

    candidate = base + ext
    counter = 1
    while path.exists(candidate):
        candidate = f"{base} ({counter}){ext}"
        counter += 1

    score = stream.Score()
    score.metadata = metadata.Metadata()
    score.metadata.title = path.split(base)[1]
    score.metadata.alternativeTitle = f"in {key} {mode}"
    score.metadata.composer = "Created with Symphony"

    # All timing is done in whole grid tiles, so every measure adds up exactly.
    # One beat = (4 / timeSigDenominator) quarter notes, split into beatLength tiles.
    beatQL = Fraction(4, timeSigDenominator)
    measureTiles = beatLength * timeSigNumerator

    # Clef mapping
    clefMap = {
        "Treble": clef.TrebleClef,
        "Treble (8va)": clef.Treble8vaClef,
        "Treble (8vb)": clef.Treble8vbClef,
        "Soprano": clef.SopranoClef,
        "Mezzo-soprano": clef.MezzoSopranoClef,
        "Alto": clef.AltoClef,
        "Tenor": clef.TenorClef,
        "Bass": clef.BassClef,
        "Bass (8vb)": clef.Bass8vbClef,
    }

    # Mode mapping
    modeMap = {
        "Ionian (maj.)": "major",
        "Aeolian (min.)": "minor",
        "Dorian": "dorian",
        "Phrygian": "phrygian",
        "Lydian": "lydian",
        "Mixolydian": "mixolydian",
        "Locrian": "locrian",
    }

    # Determine the maximum number of measures needed across all parts
    maxMeasures = 0
    for color, notes in noteMap.items():
        if notes:
            maxEndTile = max((int(n.time) + int(n.duration)) for n in notes)
            maxMeasures = max(maxMeasures, maxEndTile // measureTiles + 1)

    # Ensure at least one measure
    if maxMeasures == 0:
        maxMeasures = 1

    for color, notes in noteMap.items():
        part = stream.Part()

        # Create a timeline for each measure
        measureTimelines = [[] for _ in range(maxMeasures)]

        # Distribute notes into measures, splitting notes that cross bar lines
        for n in (notes or []):
            pitch = n.pitch + 35
            startTile = int(n.time)
            endTile = startTile + int(n.duration)
            if endTile <= startTile:
                continue

            firstMeasure = startTile // measureTiles
            lastMeasure = (endTile - 1) // measureTiles

            for mIdx in range(firstMeasure, min(lastMeasure + 1, maxMeasures)):
                measureStart = mIdx * measureTiles
                segmentStart = max(startTile, measureStart)
                segmentEnd = min(endTile, measureStart + measureTiles)

                measureTimelines[mIdx].append({
                    'offset': segmentStart - measureStart,
                    'duration': segmentEnd - segmentStart,
                    'pitch': pitch,
                    'tiedFromPrevious': mIdx > firstMeasure,
                    'tiedToNext': mIdx < lastMeasure,
                })

        # Pitches whose tie into the next measure was cut off by a chord
        brokenTies = set()

        # Build measures
        for i in range(maxMeasures):
            m = stream.Measure(number=i + 1)

            # Add metadata to first measure
            if i == 0:
                clefName = colorClefMap.get(color) if colorClefMap else None
                if clefName and clefName in clefMap:
                    m.clef = clefMap[clefName]()
                else:
                    m.clef = clef.TrebleClef()

                m.timeSignature = meter.TimeSignature(f"{timeSigNumerator}/{timeSigDenominator}")
                m.keySignature = keys.Key(key, modeMap[mode])
                m.insert(0, tempo.MetronomeMark(number=tempoBPM))

            # A staff holds a single voice, so everything starting on the same tile
            # becomes one chord, cut to its shortest note and to the next onset.
            eventsByOffset = {}
            for event in measureTimelines[i]:
                eventsByOffset.setdefault(event['offset'], []).append(event)

            segments = []
            nextBrokenTies = set()
            offsets = sorted(eventsByOffset)
            for idx, offset in enumerate(offsets):
                events = eventsByOffset[offset]
                length = min(e['duration'] for e in events)
                if idx < len(offsets) - 1:
                    length = min(length, offsets[idx + 1] - offset)

                # pitch -> (tiedFromPrevious, tiedToNext)
                pitchTies = {}
                for e in events:
                    tiedFromPrevious = e['tiedFromPrevious'] and e['pitch'] not in brokenTies
                    tiedToNext = e['tiedToNext'] and e['duration'] == length
                    if e['tiedToNext'] and not tiedToNext:
                        # cut short, so it no longer reaches its continuation
                        nextBrokenTies.add(e['pitch'])
                    previous = pitchTies.get(e['pitch'], (False, False))
                    pitchTies[e['pitch']] = (previous[0] or tiedFromPrevious, previous[1] or tiedToNext)

                segments.append((offset, length, pitchTies))
            brokenTies = nextBrokenTies

            # Fill gaps with rests (pitchTies of None)
            filledSegments = []
            cursor = 0
            for offset, length, pitchTies in segments:
                if offset > cursor:
                    filledSegments.append((cursor, offset - cursor, None))
                filledSegments.append((offset, length, pitchTies))
                cursor = offset + length
            if cursor < measureTiles:
                filledSegments.append((cursor, measureTiles - cursor, None))

            for offset, length, pitchTies in filledSegments:
                durations = splitIntoBeatDurations(offset, length, beatLength, beatQL)
                for pieceIdx, pieceDuration in enumerate(durations):
                    if pitchTies is None:
                        m.append(note.Rest(duration=pieceDuration))
                        continue

                    pitches = sorted(pitchTies)
                    musicalEvent = note.Note(pitches[0]) if len(pitches) == 1 else chord.Chord(pitches)
                    musicalEvent.duration = pieceDuration
                    eventNotes = [musicalEvent] if len(pitches) == 1 else list(musicalEvent.notes)
                    for chordNote in eventNotes:
                        tiedFromPrevious, tiedToNext = pitchTies[chordNote.pitch.midi]
                        tieBack = pieceIdx > 0 or tiedFromPrevious
                        tieForward = pieceIdx < len(durations) - 1 or tiedToNext
                        if tieBack and tieForward:
                            chordNote.tie = tie.Tie('continue')
                        elif tieBack:
                            chordNote.tie = tie.Tie('stop')
                        elif tieForward:
                            chordNote.tie = tie.Tie('start')
                    m.append(musicalEvent)
            part.append(m)
        score.append(part)

    score.write("musicxml", candidate)
    console.log('musicxml created')
    return candidate