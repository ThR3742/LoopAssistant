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


# iReal Pro chord token pattern
_IREAL_CHORD = re.compile(
    r'\*[A-Z]|'           # section markers — skip
    r'T\d\d|'             # time sig — skip
    r'([A-Ga-g][#b]?'     # root
    r'(?:maj7|maj9|maj|M7|mM7|m7b5|m7|m9|m6|min7|min|'
    r'dim7|dim|aug|ø7|Δ7|Δ|sus4|sus2|sus|'
    r'6/9|6|7|9|11|13|-7|-)?'
    r'(?:/[A-Ga-g][#b]?)?)'  # slash bass
)

_SKIP_TOKENS = re.compile(r'^(\*[A-Z]|T\d\d|[xXnNWpP\[\]{}()\s<>U]|LZ|QZ|SZ|Y|y|\d)$')


def _extract_irealb_chords(url_or_text: str) -> list[str]:
    """Extract chord list from iReal Pro irealb:// URL or exported text."""
    # Try to find the encoded music string
    if 'irealb://' in url_or_text:
        payload = url_or_text.split('irealb://')[1]
    else:
        payload = url_or_text

    # URL-decode
    payload = urllib.parse.unquote(payload)

    # iReal obfuscation: characters are shuffled in 50-char blocks
    def deobfuscate(s: str) -> str:
        result = []
        for i in range(0, len(s), 50):
            block = list(s[i:i + 50])
            if len(block) == 50:
                # swap first 25 and last 25 pairs
                for j in range(0, 24, 2):
                    block[j], block[49 - j - 1] = block[49 - j - 1], block[j]
                    block[j + 1], block[49 - j] = block[49 - j], block[j + 1]
            result.extend(block)
        return ''.join(result)

    # Find the music data section (after the last `=` in the song block)
    # iReal format: SongTitle=Composer=Style=Key=n=MusicData=
    parts = payload.split('=')
    music = None
    for part in reversed(parts):
        if len(part) > 20 and re.search(r'[A-Ga-g]', part):
            music = deobfuscate(part)
            break

    if not music:
        # Fallback: treat the whole thing as plain text
        return parse_plain(url_or_text)

    chords = []
    for m in _IREAL_CHORD.finditer(music):
        token = m.group(1)
        if token and not _SKIP_TOKENS.match(token):
            chords.append(token)

    return chords if chords else parse_plain(url_or_text)


def parse_grid(source: str) -> list[str]:
    """
    Auto-detect format and return list of chord symbols.
    """
    source = source.strip()
    if source.startswith('irealb://') or '=n=' in source:
        return _extract_irealb_chords(source)
    return parse_plain(source)
