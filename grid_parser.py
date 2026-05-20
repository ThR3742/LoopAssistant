"""
Parse chord grids from:
  1. Plain text:  "Cm7 F7 Bbmaj7 Eb7"
  2. iReal Pro .irealb URL (text extraction)
"""

import re
import urllib.parse


def parse_plain(text: str) -> list[str]:
    """Split space/comma/bar separated chord symbols."""
    tokens = re.split(r'[\s,|/]+', text.strip())
    return [t for t in tokens if t and t not in ('x', 'X', 'W', 'n', 'N')]


# ---------------------------------------------------------------------------
# iReal Pro URL parser
# ---------------------------------------------------------------------------

# iReal Pro stores music data in 50-char obfuscated blocks.
# The deobfuscation reverses each full 50-char block.
def _deobfuscate(s: str) -> str:
    result = []
    for i in range(0, len(s), 50):
        block = list(s[i:i + 50])
        if len(block) == 50:
            for j in range(25):
                block[j], block[49 - j] = block[49 - j], block[j]
        result.extend(block)
    return ''.join(result)


# iReal Pro uses both Root+Quality and Quality+Root notation internally.
# These regexes normalise both forms to Root+Quality.
_ROOTS = r'[A-G][#b]?'
_QUAL  = r'(?:\^7|\^|maj7|maj9|maj|M7|mM7|m7b5|-7b5|h7|-7|-9|-|dim7|dim|aug|sus4|sus2|sus|7|6/9|6|9|11|13)?'

# Root-before-quality:  C^7  Dm7  G7  F#o7  C6  etc.
_RE_RQ = re.compile(rf'({_ROOTS}){_QUAL}(?:/(?:{_ROOTS}))?')
# Quality-before-root (iReal internal):  7G  -7D  ^7C  h7E  etc.
_RE_QR = re.compile(
    rf'(?:\^7|\^|h7|-7b5|-7|-|dim7|dim|aug|sus4|sus2|sus|7|6/9|6|9)([A-G][#b]?)'
)

# iReal layout / non-chord tokens to strip before parsing
_LAYOUT = re.compile(
    r'\*[A-Z]'          # section markers *A *B
    r'|T\d\d'           # time sig T44 T34
    r'|N\d'             # endings N1 N2
    r'|<[^>]*>'         # comments
    r'|[|Z\[\]{}\s]'    # barlines, brackets, whitespace
    r'|LZ|XyQ|QyX|yQ|Xy|[QyrsfUpnxWL]'  # layout tokens
)


def _normalise_quality(root: str, raw_quality: str) -> str:
    """Convert iReal quality tokens to standard chord symbols."""
    q = raw_quality
    q = q.replace('^7', 'maj7').replace('^', 'maj7')
    q = q.replace('h7', 'm7b5')
    # already standard: -7, 7, 6, dim7, aug, sus4, sus2
    return root + q


def _extract_irealb_chords(url_or_text: str) -> list[str]:
    """Extract chord list from iReal Pro irealb:// URL."""
    payload = url_or_text.split('irealb://')[1] if 'irealb://' in url_or_text else url_or_text
    payload = urllib.parse.unquote(payload)

    # iReal format: Title=Composer=Arranger=Style=Key=n=MusicData=...
    parts = payload.split('=')
    # Music data is the longest part with chord-like content
    music_raw = max(
        (p for p in parts if len(p) > 10),
        key=len,
        default='',
    )
    if not music_raw:
        return parse_plain(url_or_text)

    music = _deobfuscate(music_raw)

    # Strip layout tokens to expose chord tokens
    clean = _LAYOUT.sub(' ', music)

    chords = []
    seen_positions = set()

    # Pass 1: find Root+Quality patterns (most reliable)
    for m in _RE_RQ.finditer(clean):
        start = m.start()
        # Reject if root was preceded immediately by a quality char (handled in pass 2)
        prev = clean[start - 1] if start > 0 else ' '
        if prev in '7-^h' or prev.isdigit():
            continue
        raw = m.group(0)
        root = m.group(1)
        quality = raw[len(root):]
        # Strip slash bass for voice leading
        quality = re.sub(r'/[A-G][#b]?$', '', quality)
        # Require at least something after the root (skip bare roots like "F#" alone)
        # unless they are natural roots A-G (single char) which can be major
        if not quality and len(root) == 2 and root[1] in '#b':
            continue  # F#, Bb etc. alone are probably parsing artifacts
        chord = _normalise_quality(root, quality)
        chords.append((start, chord))
        seen_positions.add(start)

    # Pass 2: find Quality+Root patterns (inverted notation)
    for m in _RE_QR.finditer(clean):
        start = m.start()
        if start in seen_positions:
            continue
        root = m.group(1)
        # The quality is everything before the root
        quality = m.group(0)[:-len(root)]
        chord = _normalise_quality(root, quality)
        chords.append((start, chord))

    # Sort by position and return chord symbols
    chords.sort(key=lambda x: x[0])
    result = [c for _, c in chords]

    # Deduplicate consecutive identical chords (repeats in iReal notation)
    deduped = []
    for c in result:
        if not deduped or c != deduped[-1]:
            deduped.append(c)

    return deduped if deduped else parse_plain(url_or_text)


def parse_grid(source: str) -> list[str]:
    """Auto-detect format and return list of chord symbols."""
    source = source.strip()
    if source.startswith('irealb://') or '=n=' in source:
        return _extract_irealb_chords(source)
    return parse_plain(source)
