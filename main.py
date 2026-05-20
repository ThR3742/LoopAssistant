#!/usr/bin/env python3
"""
LoopAssistant -- Voice leading generator for live loops.

Each voice gets one note per chord. Voices are ordered from highest to lowest.
Specify instruments to set realistic pitch ranges.

Usage:
  python main.py "Cm7 F7 Bbmaj7" --voices 3
  python main.py "Dm7 G7 Cmaj7"  --voices "violin,violin,bass"
  python main.py "Dm7 G7 Cmaj7"  --voices "violin,cello,contrebasse"
  python main.py --ireal "irealb://..." --voices 5
  python main.py --file grid.txt --voices "flute,violin,viola,cello,bass"

Available instruments (define pitch range):
  violin, viola, cello, bass, contrebasse, guitar, piano,
  flute, trumpet, saxophone, voice
  (or use a number: --voices 3  for 3 generic voices)
"""

import argparse
import sys
import os

from grid_parser import parse_grid
from voice_leading import voice_progression, resolve_range, INSTRUMENT_RANGES
from output import to_abc, to_midi, print_table


def parse_voices_arg(raw: str) -> tuple[list[str], list[tuple[int, int]]]:
    """
    Parse --voices argument. Returns (labels, ranges).
    - "3"                       → 3 generic voices with default ranges
    - "violin,violin,bass"      → 3 named voices with instrument ranges
    - "violin,2,bass"           → mixed (numeric = generic range for that slot)
    """
    parts = [p.strip() for p in raw.split(',')]

    # Pure number: e.g. "3"
    if len(parts) == 1 and parts[0].isdigit():
        n = int(parts[0])
        if n < 1:
            raise ValueError("Need at least 1 voice.")
        labels = [f'Voice {i+1}' for i in range(n)]
        ranges = [resolve_range(None, i) for i in range(n)]
        return labels, ranges

    # List of instrument names (or numbers as slot indices)
    labels, ranges = [], []
    for i, p in enumerate(parts):
        if p.isdigit():
            labels.append(f'Voice {i+1}')
            ranges.append(resolve_range(None, i))
        else:
            key = p.lower()
            if key not in INSTRUMENT_RANGES:
                print(f"Warning: unknown instrument '{p}', using default range.")
            labels.append(p.capitalize())
            ranges.append(resolve_range(p, i))
    return labels, ranges


def main():
    parser = argparse.ArgumentParser(
        description='LoopAssistant: voice leading for live loops',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('grid', nargs='?', help='Chord symbols, space separated')
    parser.add_argument('--file',   '-f',  help='Read grid from file')
    parser.add_argument('--ireal',         help='iReal Pro URL (irealb://...)')
    parser.add_argument('--voices', '-v',  default='4',
                        help='Number of voices OR comma-separated instrument list')
    parser.add_argument('--abc',           help='ABC output file (default: out.abc)')
    parser.add_argument('--midi',          help='MIDI output file (default: out.mid)')
    parser.add_argument('--title',         default='Loop Assistant')
    parser.add_argument('--tempo',         type=int, default=120)
    parser.add_argument('--no-midi',       action='store_true')
    parser.add_argument('--arpeggio', '-a', nargs='?', const='all', default=None,
                        metavar='VOICES',
                        help='Arpeggiate voices: omit for all, or "1,3" for specific voices')

    args = parser.parse_args()

    # --- Voices ---
    try:
        labels, ranges = parse_voices_arg(args.voices)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Source ---
    if args.ireal:
        source = args.ireal
    elif args.file:
        source = open(args.file).read()
    elif args.grid:
        source = args.grid
    else:
        print("Enter chord grid (e.g. Cm7 F7 Bbmaj7 Eb7):", end=' ', flush=True)
        source = input().strip()
        if not source:
            parser.print_help()
            sys.exit(1)

    # --- Parse chords ---
    chords = parse_grid(source)
    if not chords:
        print("ERROR: No chords found.", file=sys.stderr)
        sys.exit(1)

    print(f"Chords  ({len(chords)}): {' | '.join(chords)}")
    print(f"Voices  ({len(labels)}): {' | '.join(labels)}\n")

    # --- Arpeggio voices ---
    n_voices = len(labels)
    arp_voices: set[int] = set()
    if args.arpeggio == 'all':
        arp_voices = set(range(n_voices))
    elif args.arpeggio:
        for part in args.arpeggio.split(','):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < n_voices:
                    arp_voices.add(idx)

    # --- Voice leading ---
    try:
        progression = voice_progression(chords, ranges,
                                        arpeggio_voices=arp_voices or None)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print_table(progression, labels)
    print()

    # --- ABC ---
    abc_file = args.abc or 'out.abc'
    with open(abc_file, 'w') as fh:
        fh.write(to_abc(progression, labels, title=args.title, tempo=args.tempo,
                        arpeggio_voices=arp_voices or None))
    print(f"ABC  -> {abc_file}")

    pdf = abc_file.replace('.abc', '.pdf')
    if os.system('which abc2pdf > /dev/null 2>&1') == 0:
        os.system(f'abc2pdf -o {pdf} {abc_file}')
        print(f"PDF  -> {pdf}")
    elif os.system('which abcm2ps > /dev/null 2>&1') == 0:
        ps = abc_file.replace('.abc', '.ps')
        os.system(f'abcm2ps -O {ps} {abc_file}')
        if os.system('which ps2pdf > /dev/null 2>&1') == 0:
            os.system(f'ps2pdf {ps} {pdf}')
            print(f"PDF  -> {pdf}")
        else:
            print(f"PS   -> {ps}  (install ghostscript for PDF)")
    else:
        print("Tip: install abcm2ps + ghostscript to render PDF.")

    # --- MIDI ---
    if not args.no_midi:
        midi_file = args.midi or 'out.mid'
        try:
            to_midi(progression, labels, midi_file, tempo_bpm=args.tempo,
                    arpeggio_voices=arp_voices or None)
            print(f"MIDI -> {midi_file}")
        except ImportError:
            print("Tip: pip install mido for MIDI output.")


if __name__ == '__main__':
    main()
