"""
Generate ABC notation and MIDI from voiced progressions.
"""

from chords import midi_to_name


def _midi_to_abc(pitch: int) -> str:
    """Convert MIDI pitch to ABC note name with octave markers."""
    name = midi_to_name(pitch)
    octave = pitch // 12 - 1
    base, acc = (name[0], '^') if len(name) == 2 else (name, '')

    if octave == 5:   return acc + base.lower()
    if octave == 4:   return acc + base
    if octave == 3:   return acc + base + ','
    if octave == 2:   return acc + base + ',,'
    if octave == 6:   return acc + base.lower() + "'"
    diff = octave - 4
    if diff > 0:      return acc + base.lower() + "'" * diff
    return acc + base + ',' * (-diff)


def to_abc(progression: list[dict],
           labels: list[str],
           title: str = "Voice Leading",
           time_sig: str = "4/4",
           tempo: int = 120) -> str:
    """
    Generate ABC notation.
    labels: instrument/voice name for each voice (same order as pitches).
    """
    if not progression:
        return ''

    n = len(progression[0]['pitches'])
    # Clef: voices whose median pitch is below C4 (60) go on bass clef
    def clef_for(voice_idx: int) -> str:
        pitches = [e['pitches'][voice_idx] for e in progression]
        return 'bass' if sum(pitches) / len(pitches) < 60 else 'treble'

    lines = [
        f'X:1', f'T:{title}', f'M:{time_sig}',
        f'L:1/4', f'Q:1/4={tempo}', f'K:C',
    ]
    for i in range(n):
        label = labels[i] if i < len(labels) else f'Voice {i+1}'
        lines.append(f'V:{i+1} name="{label}" clef={clef_for(i)}')

    for i in range(n):
        bars = []
        for entry in progression:
            note = _midi_to_abc(entry['pitches'][i])
            prefix = f'"{entry["chord"]}"' if i == 0 else ''
            bars.append(f'{prefix}{note}4')
        lines.append(f'[V:{i+1}] ' + ' | '.join(bars) + ' |]')

    return '\n'.join(lines)


def to_midi(progression: list[dict], labels: list[str],
            filename: str, tempo_bpm: int = 120):
    """Write a MIDI file with one track per voice."""
    try:
        import mido
    except ImportError:
        raise ImportError("pip install mido")

    if not progression:
        return

    n = len(progression[0]['pitches'])
    mid = mido.MidiFile(ticks_per_beat=480)
    tempo = mido.bpm2tempo(tempo_bpm)
    ticks_per_bar = 4 * 480

    for i in range(n):
        label = labels[i] if i < len(labels) else f'Voice {i+1}'
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))
        track.append(mido.MetaMessage('track_name', name=label, time=0))
        track.append(mido.Message('program_change', channel=i % 16, program=40, time=0))
        for entry in progression:
            p = entry['pitches'][i]
            track.append(mido.Message('note_on',  channel=i % 16, note=p, velocity=80, time=0))
            track.append(mido.Message('note_off', channel=i % 16, note=p, velocity=0,  time=ticks_per_bar))

    mid.save(filename)


def print_table(progression: list[dict], labels: list[str]):
    """Pretty-print voicing table."""
    if not progression:
        return
    n = len(progression[0]['pitches'])
    hdrs = [f'{labels[i] if i < len(labels) else f"V{i+1}":>8}' for i in range(n)]
    header = f"{'Chord':<12}" + ''.join(hdrs)
    print(header)
    print('-' * len(header))
    for entry in progression:
        row = f"{entry['chord']:<12}"
        for p in entry['pitches']:
            row += f" {midi_to_name(p) + str(p // 12 - 1):>7}"
        print(row)
