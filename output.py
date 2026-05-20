"""
Generate ABC notation and MIDI from voiced progressions.
"""

from chords import midi_to_name

# ABC pitch names: MIDI 60 = C5 in ABC (middle C = C,)
# ABC convention: C, = C3 (MIDI48), C = C4(60 in some), c = C5
# We use scientific: MIDI 60 = C4, ABC middle C = C (no octave marker = octave 4)

def _midi_to_abc(pitch: int) -> str:
    """Convert MIDI pitch to ABC note name with octave markers."""
    name = midi_to_name(pitch)
    octave = pitch // 12 - 1  # scientific octave

    # ABC reference: octave 4 = C D E F G A B (capital, no comma)
    # octave 5 = c d e f g a b (lower)
    # octave 3 = C, D, ... (capital + comma)
    # octave 6 = c' d' ...

    if len(name) == 2:  # sharp
        base = name[0]
        acc = '^'
    else:
        base = name
        acc = ''

    if octave == 5:
        return acc + base.lower()
    elif octave == 4:
        return acc + base
    elif octave == 3:
        return acc + base + ','
    elif octave == 2:
        return acc + base + ',,'
    elif octave == 6:
        return acc + base.lower() + "'"
    else:
        # Generic fallback
        diff = octave - 4
        if diff > 0:
            return acc + base.lower() + "'" * diff
        else:
            return acc + base + ',' * (-diff)


def to_abc(progression: list[dict],
           title: str = "Voice Leading",
           time_sig: str = "4/4",
           tempo: int = 120,
           instruments: dict | None = None) -> str:
    """
    Generate ABC notation for a 4-voice SATB progression.
    Each chord gets one whole note per voice (4 beats).
    """
    voices = ['S', 'A', 'T', 'B']
    voice_labels = {
        'S': instruments.get('S', 'Soprano') if instruments else 'Soprano',
        'A': instruments.get('A', 'Alto')    if instruments else 'Alto',
        'T': instruments.get('T', 'Tenor')   if instruments else 'Tenor',
        'B': instruments.get('B', 'Bass')    if instruments else 'Bass',
    }

    lines = [
        f'X:1',
        f'T:{title}',
        f'M:{time_sig}',
        f'L:1/4',
        f'Q:1/4={tempo}',
        f'K:C',
    ]

    # Voice declarations
    for i, v in enumerate(voices, 1):
        lines.append(f'V:{i} name="{voice_labels[v]}" clef={"treble" if v in ("S","A") else "bass"}')

    # Music data per voice
    for i, v in enumerate(voices, 1):
        bars = []
        for entry in progression:
            pitch = entry['voices'][v]
            abc_note = _midi_to_abc(pitch)
            if i == 1:
                # Chord symbol on soprano voice only
                bars.append(f'"{entry["chord"]}"' + f'{abc_note}4')
            else:
                bars.append(f'{abc_note}4')
        bar_notes = ' | '.join(bars) + ' |]'
        lines.append(f'[V:{i}] {bar_notes}')

    return '\n'.join(lines)


def to_midi(progression: list[dict], filename: str, tempo_bpm: int = 120):
    """Write a MIDI file. Requires the 'mido' package."""
    try:
        import mido
    except ImportError:
        raise ImportError("Install mido: pip install mido")

    mid = mido.MidiFile(ticks_per_beat=480)
    tempo = mido.bpm2tempo(tempo_bpm)
    ticks_per_bar = 4 * 480  # 4/4, quarter = 480 ticks

    voices = ['S', 'A', 'T', 'B']
    channels = [0, 1, 2, 3]

    # One track per voice
    for v, ch in zip(voices, channels):
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))
        track.append(mido.MetaMessage('track_name', name=v, time=0))
        track.append(mido.Message('program_change', channel=ch, program=40, time=0))  # violin

        time_cursor = 0
        for entry in progression:
            pitch = entry['voices'][v]
            track.append(mido.Message('note_on', channel=ch, note=pitch, velocity=80, time=time_cursor))
            track.append(mido.Message('note_off', channel=ch, note=pitch, velocity=0, time=ticks_per_bar))
            time_cursor = 0

    mid.save(filename)


def print_table(progression: list[dict]):
    """Pretty-print voicing table to terminal."""
    header = f"{'Chord':<12} {'S':>6} {'A':>6} {'T':>6} {'B':>6}"
    print(header)
    print('-' * len(header))
    for entry in progression:
        row = f"{entry['chord']:<12}"
        for v in ['S', 'A', 'T', 'B']:
            p = entry['voices'][v]
            name = midi_to_name(p)
            oct_ = p // 12 - 1
            row += f" {name+str(oct_):>6}"
        print(row)
