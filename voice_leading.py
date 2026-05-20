"""
N-voice voice leading engine.
Voices are numbered 1..N from highest to lowest, each with a MIDI range.
No SATB assumptions — works for any N and any instrument combination.
"""

from itertools import product
from chords import chord_pitches_in_range, parse_chord

# Known instrument ranges (MIDI). Add more as needed.
INSTRUMENT_RANGES = {
    'violin':       (55, 93),   # G3–A6
    'viola':        (48, 81),   # C3–A5
    'cello':        (36, 72),   # C2–C5
    'bass':         (28, 60),   # E1–C4
    'contrebasse':  (28, 60),
    'guitar':       (40, 76),   # E2–E5
    'piano':        (21, 108),
    'flute':        (60, 96),   # C4–C7
    'trumpet':      (52, 84),   # E3–C6
    'saxophone':    (49, 80),
    'voice':        (48, 79),   # generic vocal range
}

# Default range when no instrument is specified, per voice index (0-based, high to low)
_DEFAULT_RANGES = [
    (60, 84),   # voice 1  (highest)
    (55, 76),   # voice 2
    (48, 69),   # voice 3
    (40, 62),   # voice 4
    (33, 55),   # voice 5
    (28, 50),   # voice 6
]


def resolve_range(instrument: str | None, voice_index: int) -> tuple[int, int]:
    """Return the MIDI range for a voice given its instrument name (or None)."""
    if instrument:
        key = instrument.lower().strip()
        if key in INSTRUMENT_RANGES:
            return INSTRUMENT_RANGES[key]
    idx = min(voice_index, len(_DEFAULT_RANGES) - 1)
    return _DEFAULT_RANGES[idx]


def _candidates(root: str, intervals: list[int],
                ranges: list[tuple[int, int]]) -> list[list[int]]:
    """For each voice range, return the list of valid chord pitches."""
    return [
        chord_pitches_in_range(root, intervals, lo, hi)
        for lo, hi in ranges
    ]


def _coverage_penalty(pitches: list[int], chord_pcs: set[int]) -> float:
    """Penalise each chord tone not covered by any voice. 0 = full coverage."""
    present = set(p % 12 for p in pitches)
    return len(chord_pcs - present) * 12


def _cost(prev: list[int], curr: list[int], chord_pcs: set[int]) -> float:
    """Semitone movement + voice crossing + coverage penalty."""
    movement = sum(abs(c - p) for c, p in zip(curr, prev))
    crossing = sum(20 for i in range(len(curr) - 1) if curr[i] < curr[i + 1])
    coverage = _coverage_penalty(curr, chord_pcs)
    return movement + crossing + coverage


def _is_valid(pitches: list[int], chord_pcs: set[int]) -> bool:
    """At least one chord tone must be covered (candidates already ensure this)."""
    present = set(p % 12 for p in pitches)
    return bool(present & chord_pcs)


def _first_chord_cost(combo: list[int], chord_pcs: set[int]) -> float:
    """Cost for the opening chord: compact, no crossing, maximum coverage."""
    n = len(combo)
    centre   = sum(abs(p - 65) for p in combo)
    crossing = sum(20 for i in range(n - 1) if combo[i] < combo[i + 1])
    coverage = _coverage_penalty(combo, chord_pcs)
    return centre + crossing + coverage


def voice_chord(root: str, intervals: list[int],
                ranges: list[tuple[int, int]],
                prev_voicing: list[int] | None = None) -> list[int] | None:
    """
    Find the best N-note voicing for the chord given voice ranges.
    Minimises movement from prev_voicing if provided.
    Unisons and octave doublings are allowed; full chord coverage is preferred.
    """
    from chords import NOTE_NAMES
    root_pc  = NOTE_NAMES.index(root)
    chord_pcs = set((root_pc + iv) % 12 for iv in intervals)

    cands = _candidates(root, intervals, ranges)
    if any(len(c) == 0 for c in cands):
        return None

    best, best_cost = None, float('inf')

    for combo in product(*cands):
        combo = list(combo)
        if not _is_valid(combo, chord_pcs):
            continue
        c = (_cost(prev_voicing, combo, chord_pcs)
             if prev_voicing is not None
             else _first_chord_cost(combo, chord_pcs))
        if c < best_cost:
            best_cost = c
            best = combo

    return best


def _arp_sequence_for_voice(primaries: list[int],
                            cands_per_chord: list[list[int]],
                            n: int = 4) -> list[list[int]]:
    """
    Build the arpeggio sequence for one voice over the full progression.

    Each chord: take the n chord tones closest to the voice-led primary note
    (guaranteeing the primary is always present and the voice stays in its own
    register).  Then choose ascending or descending order via a 2-state DP that
    minimises |last[chord N] - first[chord N+1]|.  This naturally produces
    contrary motion when two voices have neighbouring anchors.
    """
    # Step 1: expand each primary into n nearest chord tones (ascending)
    asc_runs: list[list[int]] = []
    for primary, cands in zip(primaries, cands_per_chord):
        pts = sorted(set(cands))
        if not pts:
            asc_runs.append([primary] * n)
            continue
        by_dist = sorted(pts, key=lambda p: (abs(p - primary), p))
        asc_runs.append(sorted(by_dist[:n]))

    # Step 2: 2-state DP — state = direction (0=asc, 1=desc)
    # costs[d] = best total transition cost arriving with direction d
    INF = float('inf')
    costs = [0.0, 0.0]
    back: list[list[int]] = [[-1, -1]]   # back[chord][dir] = parent direction

    for i in range(1, len(asc_runs)):
        new_costs = [INF, INF]
        new_back  = [-1,  -1]
        for d_next in range(2):
            first_next = asc_runs[i][0] if d_next == 0 else asc_runs[i][-1]
            for d_prev in range(2):
                last_prev = asc_runs[i - 1][-1] if d_prev == 0 else asc_runs[i - 1][0]
                c = costs[d_prev] + abs(first_next - last_prev)
                if c < new_costs[d_next]:
                    new_costs[d_next] = c
                    new_back[d_next]  = d_prev
        costs = new_costs
        back.append(new_back)

    # Traceback
    final_d = 0 if costs[0] <= costs[1] else 1
    dirs = [final_d]
    for i in range(len(asc_runs) - 1, 0, -1):
        dirs.append(back[i][dirs[-1]])
    dirs.reverse()

    return [asc_runs[i] if dirs[i] == 0 else list(reversed(asc_runs[i]))
            for i in range(len(asc_runs))]


def voice_progression(chords: list[str],
                      ranges: list[tuple[int, int]],
                      arpeggio_voices: set[int] | None = None) -> list[dict]:
    """
    Generate voice leading for a chord sequence.

    Args:
        chords: list of chord symbols e.g. ['Dm7', 'G7', 'Cmaj7']
        ranges: list of (low, high) MIDI ranges, one per voice
        arpeggio_voices: 0-based indices of voices rendered as arpeggios.
                         Uses global DP to minimise inter-chord transitions.

    Returns:
        list of dicts with keys:
          'chord'        – chord symbol
          'pitches'      – best single note per voice (sustained voice leading)
          'alternatives' – other chord tones in range per voice
          'arp_sequences'– 4-note ascending run per arp voice (None for others)
    """
    arp = set(arpeggio_voices) if arpeggio_voices else set()

    # First pass: collect voicings and per-chord candidates
    raw: list[tuple[str, list[int], list[list[int]]]] = []
    prev = None
    for symbol in chords:
        root, intervals = parse_chord(symbol)
        voicing = voice_chord(root, intervals, ranges, prev)
        if voicing is None:
            raise ValueError(
                f"Could not voice '{symbol}' with {len(ranges)} voices — "
                f"check instrument ranges or reduce voice count."
            )
        cands = _candidates(root, intervals, ranges)
        raw.append((symbol, voicing, cands))
        prev = voicing

    # Arpeggio: expand each voice-led note into n nearest chord tones,
    # choose ascending/descending per chord to minimise inter-chord jumps.
    arp_seqs_per_voice: dict[int, list[list[int]]] = {}
    for i in arp:
        primaries      = [voicing[i] for _, voicing, _     in raw]
        cands_per_chord = [cands[i]  for _, _,       cands in raw]
        arp_seqs_per_voice[i] = _arp_sequence_for_voice(primaries, cands_per_chord)

    # Assemble result
    result = []
    for ci, (symbol, voicing, cands) in enumerate(raw):
        arp_seqs: list[list[int] | None] = [
            arp_seqs_per_voice[i][ci] if i in arp else None
            for i in range(len(ranges))
        ]
        result.append({
            'chord':         symbol,
            'pitches':       voicing,
            'alternatives':  [[p for p in c if p != voicing[i]]
                              for i, c in enumerate(cands)],
            'arp_sequences': arp_seqs,
        })

    return result
