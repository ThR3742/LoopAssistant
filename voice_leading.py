"""
N-voice voice leading engine (1 to 4 voices).
Minimises total voice movement between consecutive chords.
"""

from itertools import product
from chords import chord_pitches_in_range, parse_chord

# All available voices and their MIDI ranges
ALL_VOICE_RANGES = {
    'S': (60, 81),   # C4–A5  soprano
    'A': (55, 74),   # G3–D5  alto
    'T': (48, 69),   # C3–A4  tenor
    'B': (40, 60),   # E2–C4  bass
}
ALL_VOICES = ['S', 'A', 'T', 'B']

# Default voice subsets for each count (top-down from soprano)
DEFAULT_VOICES = {
    1: ['S'],
    2: ['S', 'B'],
    3: ['S', 'A', 'B'],
    4: ['S', 'A', 'T', 'B'],
}

# Centre pitch for first-chord cost (middle of the soprano range)
_CENTRE = 66  # F#4


def select_voices(n: int) -> list[str]:
    """Return the default voice list for n voices (1–4)."""
    n = max(1, min(4, n))
    return DEFAULT_VOICES[n]


def _candidates(root: str, intervals: list[int],
                voices: list[str]) -> dict[str, list[int]]:
    return {
        v: chord_pitches_in_range(root, intervals, *ALL_VOICE_RANGES[v])
        for v in voices
    }


def _cost(prev: list[int], curr: list[int]) -> int:
    """Sum of semitone movements + penalties for crossing and adjacent unisons."""
    movement = sum(abs(c - p) for c, p in zip(curr, prev))
    crossing = sum(20 for i in range(len(curr) - 1) if curr[i] < curr[i + 1])
    unison = sum(8 for i in range(len(curr) - 1) if curr[i] == curr[i + 1])
    return movement + crossing + unison


def _is_valid(pitches: list[int], intervals: list[int], n_voices: int) -> bool:
    """Enough distinct chord tones must be covered given the voice count."""
    present = set(p % 12 for p in pitches)
    required = min(len(intervals), n_voices)
    return len(present) >= required


def voice_chord(root: str, intervals: list[int],
                voices: list[str],
                prev_voicing: list[int] | None = None) -> list[int]:
    """
    Choose the best voicing for the chord with the given voice list.
    If prev_voicing is given, minimise movement from it.
    """
    cands = _candidates(root, intervals, voices)
    n = len(voices)

    best = None
    best_cost = float('inf')

    for combo in product(*[cands[v] for v in voices]):
        combo = list(combo)
        if not _is_valid(combo, intervals, n):
            continue
        if prev_voicing is not None:
            c = _cost(prev_voicing, combo)
        else:
            centre = sum(abs(p - _CENTRE) for p in combo)
            crossing = sum(20 for i in range(n - 1) if combo[i] < combo[i + 1])
            unison = sum(8 for i in range(n - 1) if combo[i] == combo[i + 1])
            c = centre + crossing + unison
        if c < best_cost:
            best_cost = c
            best = combo

    return best


def voice_progression(chords: list[str],
                      voices: list[str] | None = None) -> list[dict]:
    """
    Given a list of chord symbols and a voice list, return a list of dicts:
        {'chord': str, 'voices': {voice: midi_pitch, ...}}

    voices defaults to all 4 SATB voices.
    """
    if voices is None:
        voices = ALL_VOICES

    result = []
    prev = None

    for symbol in chords:
        root, intervals = parse_chord(symbol)
        voicing = voice_chord(root, intervals, voices, prev)
        if voicing is None:
            raise ValueError(f"Could not voice chord: {symbol}")
        entry = {
            'chord': symbol,
            'root': root,
            'intervals': intervals,
            'voices': dict(zip(voices, voicing)),
        }
        result.append(entry)
        prev = voicing

    return result
