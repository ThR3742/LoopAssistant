"""
4-voice SATB voice leading engine.
Minimises total voice movement between consecutive chords.
"""

from itertools import product
from chords import chord_pitches_in_range, parse_chord

# SATB ranges in MIDI
VOICE_RANGES = {
    'S': (60, 81),   # C4–A5
    'A': (55, 74),   # G3–D5
    'T': (48, 69),   # C3–A4
    'B': (40, 60),   # E2–C4
}
VOICES = ['S', 'A', 'T', 'B']


def _candidates(root: str, intervals: list[int]) -> dict[str, list[int]]:
    return {
        v: chord_pitches_in_range(root, intervals, *VOICE_RANGES[v])
        for v in VOICES
    }


def _cost(prev: list[int], curr: list[int]) -> int:
    """Sum of semitone movements + penalties for crossing and adjacent unisons."""
    movement = sum(abs(c - p) for c, p in zip(curr, prev))
    crossing = sum(20 for i in range(len(curr) - 1) if curr[i] < curr[i + 1])
    unison = sum(8 for i in range(len(curr) - 1) if curr[i] == curr[i + 1])
    return movement + crossing + unison


def _is_valid(chord: list[int], intervals: list[int]) -> bool:
    """All interval classes in the chord must appear at least once."""
    n = len(intervals)
    present = set((p % 12) for p in chord)
    # Root must be present
    return len(present) >= min(n, 3)


def voice_chord(root: str, intervals: list[int],
                prev_voicing: list[int] | None = None) -> list[int]:
    """
    Choose the best 4-voice voicing for the chord.
    If prev_voicing is given, minimise movement from it.
    """
    cands = _candidates(root, intervals)

    best = None
    best_cost = float('inf')

    for combo in product(*[cands[v] for v in VOICES]):
        combo = list(combo)
        if not _is_valid(combo, intervals):
            continue
        if prev_voicing is not None:
            c = _cost(prev_voicing, combo)
        else:
            # First chord: prefer compact spacing centred around C4, no crossing
            centre = sum(abs(p - 60) for p in combo)
            crossing = sum(20 for i in range(len(combo) - 1) if combo[i] < combo[i + 1])
            unison = sum(8 for i in range(len(combo) - 1) if combo[i] == combo[i + 1])
            c = centre + crossing + unison
        if c < best_cost:
            best_cost = c
            best = combo

    return best


def voice_progression(chords: list[str]) -> list[dict]:
    """
    Given a list of chord symbols, return a list of dicts:
        {'chord': str, 'voices': {'S': int, 'A': int, 'T': int, 'B': int}}
    """
    result = []
    prev = None

    for symbol in chords:
        root, intervals = parse_chord(symbol)
        voicing = voice_chord(root, intervals, prev)
        if voicing is None:
            raise ValueError(f"Could not voice chord: {symbol}")
        entry = {
            'chord': symbol,
            'root': root,
            'intervals': intervals,
            'voices': dict(zip(VOICES, voicing)),
        }
        result.append(entry)
        prev = voicing

    return result
