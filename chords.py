"""
Chord theory: parse chord symbols into MIDI pitch sets.
Pitches are represented as integers (C4 = 60).
"""

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
ENHARMONIC = {'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#', 'Cb': 'B'}

# Interval sets (semitones from root)
CHORD_INTERVALS = {
    '':      [0, 4, 7],          # major
    'maj':   [0, 4, 7],
    'm':     [0, 3, 7],          # minor
    'min':   [0, 3, 7],
    '-':     [0, 3, 7],
    'dim':   [0, 3, 6],
    'aug':   [0, 4, 8],
    '+':     [0, 4, 8],
    'sus2':  [0, 2, 7],
    'sus4':  [0, 5, 7],
    '7':     [0, 4, 7, 10],      # dominant 7
    'maj7':  [0, 4, 7, 11],
    'M7':    [0, 4, 7, 11],
    'Δ':     [0, 4, 7, 11],
    'Δ7':    [0, 4, 7, 11],
    'm7':    [0, 3, 7, 10],
    'min7':  [0, 3, 7, 10],
    '-7':    [0, 3, 7, 10],
    'mM7':   [0, 3, 7, 11],
    'dim7':  [0, 3, 6, 9],
    'ø7':    [0, 3, 6, 10],      # half-diminished
    'm7b5':  [0, 3, 6, 10],
    '9':     [0, 4, 7, 10, 14],
    'maj9':  [0, 4, 7, 11, 14],
    'm9':    [0, 3, 7, 10, 14],
    '6':     [0, 4, 7, 9],
    'm6':    [0, 3, 7, 9],
    '6/9':   [0, 4, 7, 9, 14],
    '11':    [0, 4, 7, 10, 14, 17],
    '13':    [0, 4, 7, 10, 14, 17, 21],
}


def note_to_midi(name: str, octave: int) -> int:
    name = ENHARMONIC.get(name, name)
    return NOTE_NAMES.index(name) + (octave + 1) * 12


def midi_to_name(pitch: int) -> str:
    return NOTE_NAMES[pitch % 12]


def parse_chord(symbol: str) -> tuple[str, list[int]]:
    """
    Parse a chord symbol like 'Cm7', 'Fmaj7', 'G7'.
    Returns (root_name, intervals_list).
    """
    symbol = symbol.strip()
    # Extract root (1 or 2 chars)
    if len(symbol) >= 2 and symbol[1] in '#b':
        root_raw = symbol[:2]
        rest = symbol[2:]
    else:
        root_raw = symbol[0]
        rest = symbol[1:]

    root = ENHARMONIC.get(root_raw, root_raw)

    # Handle slash chords — just use upper part for voice leading
    if '/' in rest:
        rest = rest.split('/')[0]

    intervals = CHORD_INTERVALS.get(rest, CHORD_INTERVALS.get(''))
    if intervals is None:
        intervals = [0, 4, 7]  # fallback: major

    return root, intervals


def chord_pitches_in_range(root: str, intervals: list[int],
                            low: int, high: int) -> list[int]:
    """Return all chord tones between low and high MIDI pitches."""
    root_pc = NOTE_NAMES.index(root)
    pitches = []
    for octave in range(-1, 9):
        for iv in intervals:
            p = root_pc + iv + (octave + 1) * 12
            if low <= p <= high:
                pitches.append(p)
    return sorted(pitches)
