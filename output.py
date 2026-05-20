"""
Generate ABC notation and MIDI from voiced progressions.
"""

from chords import midi_to_name

# Instruments that use bass clef. Everything else defaults to treble.
_BASS_CLEF_INSTRUMENTS = {
    'cello', 'bass', 'contrebasse', 'tuba', 'bassoon', 'baritone',
}


def _clef_for_label(label: str) -> str:
    return 'bass' if label.lower().strip() in _BASS_CLEF_INSTRUMENTS else 'treble'


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


def _arpeggio_notes(primary: int, all_pitches: list[int], n: int = 4) -> list[int]:
    """Return n chord tones closest to primary, sorted ascending (no octave wrapping)."""
    pitches = sorted(set(all_pitches))
    if not pitches:
        return [primary] * n
    if len(pitches) <= n:
        return pitches + [pitches[-1]] * (n - len(pitches))
    by_dist = sorted(pitches, key=lambda p: (abs(p - primary), p))
    return sorted(by_dist[:n])


def to_abc(progression: list[dict],
           labels: list[str],
           title: str = "Voice Leading",
           time_sig: str = "4/4",
           tempo: int = 120,
           arpeggio_voices: set[int] | None = None) -> str:
    """
    Generate ABC notation.
    arpeggio_voices: 0-based set of voice indices to render as 4-note ascending arpeggios.
                     Other voices get a single whole note. None = all sustained.
    """
    if not progression:
        return ''

    arp = arpeggio_voices or set()
    n = len(progression[0]['pitches'])
    bars_per_line = 4 if arp else 8
    lines = [
        f'X:1', f'T:{title}', f'M:{time_sig}',
        f'L:1/4', f'Q:1/4={tempo}', f'K:C',
        f'%%barsperline {bars_per_line}',
        f'%%stretchlast 0',
    ]
    for i in range(n):
        label = labels[i] if i < len(labels) else f'Voice {i+1}'
        clef = _clef_for_label(label)
        lines.append(f'V:{i+1} name="{label}" clef={clef}')

    for i in range(n):
        voice_bars = []
        for entry in progression:
            prefix = f'"{entry["chord"]}"' if i == 0 else ''
            if i in arp:
                primary = entry['pitches'][i]
                alts    = entry.get('alternatives', [[] for _ in range(n)])[i]
                notes   = _arpeggio_notes(primary, [primary] + alts)
                bar     = ' '.join(_midi_to_abc(p) for p in notes)
                voice_bars.append(f'{prefix}{bar}')
            else:
                note = _midi_to_abc(entry['pitches'][i])
                voice_bars.append(f'{prefix}{note}4')
        lines.append(f'[V:{i+1}] ' + ' | '.join(voice_bars) + ' |]')

    return '\n'.join(lines)


def to_midi(progression: list[dict], labels: list[str],
            filename: str, tempo_bpm: int = 120,
            arpeggio_voices: set[int] | None = None):
    """Write a MIDI file with one track per voice."""
    try:
        import mido
    except ImportError:
        raise ImportError("pip install mido")

    if not progression:
        return

    arp = arpeggio_voices or set()
    n = len(progression[0]['pitches'])
    mid = mido.MidiFile(ticks_per_beat=480)
    tempo = mido.bpm2tempo(tempo_bpm)
    ticks_per_bar = 4 * 480
    ticks_per_note = ticks_per_bar // 4

    for i in range(n):
        label = labels[i] if i < len(labels) else f'Voice {i+1}'
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))
        track.append(mido.MetaMessage('track_name', name=label, time=0))
        track.append(mido.Message('program_change', channel=i % 16, program=40, time=0))
        for entry in progression:
            if i in arp:
                primary = entry['pitches'][i]
                alts    = entry.get('alternatives', [[] for _ in range(n)])[i]
                notes   = _arpeggio_notes(primary, [primary] + alts)
                first = True
                for p in notes:
                    track.append(mido.Message('note_on',  channel=i % 16, note=p,
                                              velocity=80, time=0))
                    track.append(mido.Message('note_off', channel=i % 16, note=p,
                                              velocity=0,  time=ticks_per_note))
            else:
                p = entry['pitches'][i]
                track.append(mido.Message('note_on',  channel=i % 16, note=p, velocity=80, time=0))
                track.append(mido.Message('note_off', channel=i % 16, note=p, velocity=0,  time=ticks_per_bar))

    mid.save(filename)


def print_table(progression: list[dict], labels: list[str]):
    """Pretty-print voicing table with available arpeggio tones."""
    if not progression:
        return
    n = len(progression[0]['pitches'])
    has_alts = 'alternatives' in progression[0]
    col_w = 20 if has_alts else 8
    hdrs = [f'{(labels[i] if i < len(labels) else f"V{i+1}"):>{col_w}}' for i in range(n)]
    header = f"{'Chord':<12}" + ''.join(hdrs)
    print(header)
    print('-' * len(header))
    for entry in progression:
        row = f"{entry['chord']:<12}"
        for j, p in enumerate(entry['pitches']):
            primary_str = midi_to_name(p) + str(p // 12 - 1)
            if has_alts:
                alts = entry['alternatives'][j]
                by_dist = sorted(alts, key=lambda a: (abs(a - p), a))[:3]
                by_dist_asc = sorted(by_dist)
                rest = [midi_to_name(a) + str(a // 12 - 1) for a in by_dist_asc]
                cell = f'{primary_str}({" ".join(rest)})' if rest else primary_str
            else:
                cell = primary_str
            row += f' {cell:>{col_w}}'
        print(row)
