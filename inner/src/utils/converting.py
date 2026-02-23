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
    outputs: nothing

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
    outputs: nothing

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

    # Calculate quarter length values
    # One beat = (4 / timeSigDenominator) quarter notes
    # Example: if denominator is 4, one beat = 1 quarter note
    # Example: if denominator is 2, one beat = 2 quarter notes (half note)
    beatQL = Fraction(4, timeSigDenominator)
    
    # One tile = beatQL / beatLength quarter notes
    tileQL = beatQL / beatLength
    
    # One measure = timeSigNumerator beats
    measureQL = beatQL * timeSigNumerator

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
            maxEndTile = max((n.time + n.duration) for n in notes)
            maxEndQL = maxEndTile * tileQL
            numMeasures = int(maxEndQL / measureQL) + 1
            maxMeasures = max(maxMeasures, numMeasures)

    # Ensure at least one measure
    if maxMeasures == 0:
        maxMeasures = 1

    for color, notes in noteMap.items():
        part = stream.Part()

        # Sort notes by start time
        sortedNotes = sorted(notes, key=lambda n: n.time) if notes else []

        # Create a timeline for each measure
        measureTimelines = [[] for _ in range(maxMeasures)]

        # Distribute notes into measures
        for n in sortedNotes:
            pitch = n.pitch + 35
            startQL = Fraction(n.time) * tileQL
            durQL = Fraction(n.duration) * tileQL

            measureIdx = int(startQL / measureQL)
            if measureIdx >= maxMeasures:
                continue

            offsetInMeasure = startQL - (measureIdx * measureQL)
            endQL = startQL + durQL
            endMeasureIdx = int((endQL - Fraction(1, 100000)) / measureQL)

            if endMeasureIdx > measureIdx:
                # Note spans multiple measures - split it
                for mIdx in range(measureIdx, min(endMeasureIdx + 1, maxMeasures)):
                    measureStartQL = mIdx * measureQL
                    measureEndQL = (mIdx + 1) * measureQL

                    segmentStart = max(startQL, measureStartQL)
                    segmentEnd = min(endQL, measureEndQL)
                    segmentDur = segmentEnd - segmentStart

                    if segmentDur > 0:
                        offsetInThisMeasure = segmentStart - measureStartQL
                        
                        # Determine tie type
                        if mIdx > measureIdx and mIdx < endMeasureIdx:
                            tieType = 'continue'
                        elif mIdx > measureIdx:
                            tieType = 'stop'
                        elif mIdx < endMeasureIdx:
                            tieType = 'start'
                        else:
                            tieType = None

                        measureTimelines[mIdx].append({
                            'offset': offsetInThisMeasure,
                            'duration': segmentDur,
                            'pitch': pitch,
                            'tie': tieType
                        })
            else:
                # Note fits in single measure
                measureTimelines[measureIdx].append({
                    'offset': offsetInMeasure,
                    'duration': durQL,
                    'pitch': pitch,
                    'tie': None
                })

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

            # Sort events by offset
            timeline = sorted(measureTimelines[i], key=lambda x: x['offset'])

            if not timeline:
                # Empty measure - add a measure rest
                r = note.Rest()
                r.duration = m21duration.Duration(quarterLength=float(measureQL))
                m.append(r)
            else:
                # Group simultaneous notes into chords when they share
                # offset, duration, and tie type.
                groupedByTiming = {}
                for event in timeline:
                    groupKey = (event['offset'], event['duration'], event['tie'])
                    if groupKey not in groupedByTiming:
                        groupedByTiming[groupKey] = []
                    groupedByTiming[groupKey].append(event['pitch'])

                groupedEvents = sorted(
                    (
                        {
                            'offset': groupKey[0],
                            'duration': groupKey[1],
                            'tie': groupKey[2],
                            'pitches': pitches
                        }
                        for groupKey, pitches in groupedByTiming.items()
                    ),
                    key=lambda x: x['offset']
                )

                # Enforce single-voice timing per staff/measure:
                # if an event overlaps the next event onset, truncate it.
                normalizedEvents = []
                for idx, event in enumerate(groupedEvents):
                    eventOffset = event['offset']
                    eventDuration = event['duration']

                    if idx < len(groupedEvents) - 1:
                        nextOffset = groupedEvents[idx + 1]['offset']
                        if nextOffset > eventOffset and eventOffset + eventDuration > nextOffset:
                            eventDuration = nextOffset - eventOffset

                    if eventDuration > 0:
                        normalizedEvents.append({
                            'offset': eventOffset,
                            'duration': eventDuration,
                            'tie': event['tie'],
                            'pitches': event['pitches']
                        })

                # Fill measure with notes/chords and rests
                currentOffset = Fraction(0)

                for event in normalizedEvents:
                    eventOffset = event['offset']
                    eventDuration = event['duration']

                    # Add rest if there's a gap before this event
                    if eventOffset > currentOffset:
                        gapDur = eventOffset - currentOffset
                        r = note.Rest()
                        r.duration = m21duration.Duration(quarterLength=float(gapDur))
                        m.insert(float(currentOffset), r)

                    # Add note or chord
                    if len(event['pitches']) == 1:
                        musicalEvent = note.Note(event['pitches'][0])
                        if event['tie']:
                            musicalEvent.tie = tie.Tie(event['tie'])
                    else:
                        musicalEvent = chord.Chord(event['pitches'])
                        if event['tie']:
                            for chordNote in musicalEvent.notes:
                                chordNote.tie = tie.Tie(event['tie'])
                    musicalEvent.duration = m21duration.Duration(quarterLength=float(eventDuration))
                    m.insert(float(eventOffset), musicalEvent)

                    currentOffset = max(currentOffset, eventOffset + eventDuration)

                # Fill remaining space at end of measure with rest
                if currentOffset < measureQL:
                    remainingDur = measureQL - currentOffset
                    r = note.Rest()
                    r.duration = m21duration.Duration(quarterLength=float(remainingDur))
                    m.insert(float(currentOffset), r)
            part.append(m)
        score.append(part)

    score.write("musicxml", candidate)
    console.log('musicxml created')
    return candidate