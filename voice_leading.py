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


def _voice_arp_progression(per_chord_cands: list[list[int]], n: int = 4,
                           anchors_per_chord: list[int] | None = None,
                           avoid_per_chord: list[set[int]] | None = None) -> list[list[int]]:
    """
    Globally optimal arpeggio sequence for one voice over the full progression.
    Each chord gets an n-note run that can be ascending OR descending.

    anchors_per_chord: the voice-led (sustained) note for this voice at each chord.
      The DP strongly prefers windows that contain or are near the anchor, which
      keeps each voice centred around its own voice-led note — not an octave copy
      of another voice.
    avoid_per_chord: MIDI pitches already used by higher-priority voices (soft penalty).
    """
    windows_per_chord: list[list[list[int]]] = []
    for cands in per_chord_cands:
        pts = sorted(set(cands))
        if not pts:
            windows_per_chord.append([[]])
            continue
        base = pts if len(pts) >= n else pts + [pts[-1]] * (n - len(pts))
        if len(base) <= n:
            windows_per_chord.append([base, list(reversed(base))])
            continue
        ws = []
        for i in range(len(base) - n + 1):
            asc = base[i:i + n]
            ws.append(asc)
            ws.append(list(reversed(asc)))
        windows_per_chord.append(ws)

    if not windows_per_chord:
        return []

    all_pts = sorted(set(p for c in per_chord_cands for p in c))
    mid = (all_pts[0] + all_pts[-1]) / 2 if all_pts else 65.0

    def _anchor(w: list[int], ci: int) -> float:
        if not anchors_per_chord:
            return abs((min(w) + max(w)) / 2 - mid) * 0.2
        anc = anchors_per_chord[ci]
        return min(abs(p - anc) for p in w) * 1.5

    def _overlap(w: list[int], ci: int) -> float:
        if not avoid_per_chord:
            return 0.0
        return sum(1 for p in w if p in avoid_per_chord[ci]) * 6.0

    def _cost(w: list[int], ci: int) -> float:
        return _anchor(w, ci) + _overlap(w, ci)

    costs = {j: _cost(w, 0) for j, w in enumerate(windows_per_chord[0])}
    back: list[dict[int, int]] = [{}]

    for i in range(1, len(windows_per_chord)):
        new_costs: dict[int, float] = {}
        new_back:  dict[int, int]   = {}
        for k, w_next in enumerate(windows_per_chord[i]):
            best_c, best_j = float('inf'), 0
            for j, prev_cost in costs.items():
                prev_last = windows_per_chord[i - 1][j][-1]
                c = prev_cost + abs(w_next[0] - prev_last) + _cost(w_next, i)
                if c < best_c:
                    best_c, best_j = c, j
            new_costs[k] = best_c
            new_back[k]  = best_j
        costs = new_costs
        back.append(new_back)

    chosen = [min(costs, key=costs.__getitem__)]
    for i in range(len(windows_per_chord) - 1, 0, -1):
        chosen.append(back[i][chosen[-1]])
    chosen.reverse()

    return [windows_per_chord[i][chosen[i]] for i in range(len(windows_per_chord))]


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

    # DP for each arpeggiated voice, in order — later voices avoid notes
    # already chosen by earlier voices (soft penalty of 8 per shared note).
    arp_seqs_per_voice: dict[int, list[list[int]]] = {}
    used_per_chord: list[set[int]] = [set() for _ in raw]
    for i in sorted(arp):
        per_chord  = [cands[i]    for _, _,       cands   in raw]
        anchors    = [voicing[i]  for _, voicing, _       in raw]
        seq = _voice_arp_progression(per_chord,
                                     anchors_per_chord=anchors,
                                     avoid_per_chord=used_per_chord)
        arp_seqs_per_voice[i] = seq
        for ci, window in enumerate(seq):
            used_per_chord[ci].update(window)

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
