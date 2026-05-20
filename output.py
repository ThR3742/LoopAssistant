"""
Generate ABC notation and MIDI from voiced progressions.
"""

from chords import midi_to_name

# Default labels and clefs per voice ID
_VOICE_DEFAULTS = {
    'S': ('Soprano', 'treble'),
    'A': ('Alto',    'treble'),
    'T': ('Tenor',   'bass'),
    'B': ('Bass',    'bass'),
}


def _midi_to_abc(pitch: int) -> str:
    """Convert MIDI pitch to ABC note name with octave markers."""
    name = midi_to_name(pitch)
    octave = pitch // 12 - 1  # scientific octave (C4 = 60 → octave 4)

    if len(name) == 2:  # sharp note
        base, acc = name[0], '^'
    else:
        base, acc = name, ''

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
    Generate ABC notation. Voices and their count are inferred from
    the first entry in the progression.
    """
    if not progression:
        return ''

    active_voices = list(progression[0]['voices'].keys())

    lines = [
        f'X:1',
        f'T:{title}',
        f'M:{time_sig}',
        f'L:1/4',
        f'Q:1/4={tempo}',
        f'K:C',
    ]

    # Voice declarations
    for i, v in enumerate(active_voices, 1):
        default_label, default_clef = _VOICE_DEFAULTS.get(v, (v, 'treble'))
        label = (instruments or {}).get(v, default_label)
        clef = 'treble' if (instruments or {}).get(v, default_clef) != 'bass' else 'bass'
        # Re-derive clef from range if not overridden
        _, clef = _VOICE_DEFAULTS.get(v, (label, 'treble'))
        lines.append(f'V:{i} name="{label}" clef={clef}')

    # Music data per voice
    for i, v in enumerate(active_voices, 1):
        bars = []
        for entry in progression:
            pitch = entry['voices'][v]
            abc_note = _midi_to_abc(pitch)
            if i == 1:
                bars.append(f'"{entry["chord"]}"' + f'{abc_note}4')
            else:
                bars.append(f'{abc_note}4')
        lines.append(f'[V:{i}] ' + ' | '.join(bars) + ' |]')

    return '\n'.join(lines)


def to_midi(progression: list[dict], filename: str, tempo_bpm: int = 120):
    """Write a MIDI file with one track per active voice."""
    try:
        import mido
    except ImportError:
        raise ImportError("Install mido: pip install mido")

    if not progression:
        return

    active_voices = list(progression[0]['voices'].keys())
    mid = mido.MidiFile(ticks_per_beat=480)
    tempo = mido.bpm2tempo(tempo_bpm)
    ticks_per_bar = 4 * 480

    for ch, v in enumerate(active_voices):
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))
        track.append(mido.MetaMessage('track_name', name=v, time=0))
        track.append(mido.Message('program_change', channel=ch, program=40, time=0))

        for entry in progression:
            pitch = entry['voices'][v]
            track.append(mido.Message('note_on',  channel=ch, note=pitch, velocity=80, time=0))
            track.append(mido.Message('note_off', channel=ch, note=pitch, velocity=0,  time=ticks_per_bar))

    mid.save(filename)


def print_table(progression: list[dict]):
    """Pretty-print voicing table to terminal."""
    if not progression:
        return
    active_voices = list(progression[0]['voices'].keys())
    header = f"{'Chord':<12}" + ''.join(f" {v:>6}" for v in active_voices)
    print(header)
    print('-' * len(header))
    for entry in progression:
        row = f"{entry['chord']:<12}"
        for v in active_voices:
            p = entry['voices'][v]
            row += f" {midi_to_name(p) + str(p // 12 - 1):>6}"
        print(row)
