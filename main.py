#!/usr/bin/env python3
"""
LoopAssistant -- Voice leading generator for live loops.

Usage:
  python main.py "Cm7 F7 Bbmaj7 Eb7"
  python main.py "Dm7 G7 Cmaj7" --voices 2
  python main.py "Dm7 G7 Cmaj7" --voices S,A,B --instruments "S=Violon bow,A=Alto,B=Bass"
  python main.py --file grid.txt --voices 3 --midi out.mid
  python main.py --ireal "irealb://..." --voices 4
"""

import argparse
import sys
import os

from grid_parser import parse_grid
from voice_leading import voice_progression, select_voices, ALL_VOICES
from output import to_abc, to_midi, print_table


def parse_voices_arg(raw: str) -> list[str]:
    """
    Accept either a number ("3") or a comma-separated voice list ("S,A,B").
    Returns a validated list of voice IDs.
    """
    raw = raw.strip()
    if raw.isdigit():
        n = int(raw)
        if not 1 <= n <= 4:
            raise ValueError(f"--voices must be between 1 and 4, got {n}")
        return select_voices(n)
    # Comma-separated list
    ids = [v.strip().upper() for v in raw.split(',')]
    for v in ids:
        if v not in ALL_VOICES:
            raise ValueError(f"Unknown voice '{v}'. Choose from {ALL_VOICES}")
    return ids


def main():
    parser = argparse.ArgumentParser(
        description='LoopAssistant: generate voice leading from a chord grid',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
voices:
  --voices 1       Single melody line (Soprano)
  --voices 2       Two parts: Soprano + Bass
  --voices 3       Three parts: Soprano + Alto + Bass  (default for 3)
  --voices 4       Full SATB  (default)
  --voices S,T,B   Custom selection of S A T B voices
        """
    )
    parser.add_argument('grid', nargs='?', help='Chord symbols (space separated)')
    parser.add_argument('--file', '-f',   help='Read chord grid from file')
    parser.add_argument('--ireal',        help='iReal Pro URL (irealb://...)')
    parser.add_argument('--voices', '-v', default='4',
                        help='Number of voices (1-4) or list e.g. S,A,B (default: 4)')
    parser.add_argument('--abc',          help='Output ABC file (default: out.abc)')
    parser.add_argument('--midi',         help='Output MIDI file (default: out.mid)')
    parser.add_argument('--title',        default='Loop Assistant', help='Score title')
    parser.add_argument('--tempo',        type=int, default=120, help='Tempo BPM')
    parser.add_argument('--no-midi',      action='store_true', help='Skip MIDI output')
    parser.add_argument(
        '--instruments',
        help='Label overrides per voice, e.g. "S=Violon bow,A=Alto,T=Cello,B=Contrebasse"'
    )

    args = parser.parse_args()

    # --- Voices ---
    try:
        voices = parse_voices_arg(args.voices)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Source ---
    if args.ireal:
        source = args.ireal
    elif args.file:
        with open(args.file) as fh:
            source = fh.read()
    elif args.grid:
        source = args.grid
    else:
        print("Enter chord grid (e.g. Cm7 F7 Bbmaj7 Eb7):", end=' ', flush=True)
        source = input().strip()
        if not source:
            parser.print_help()
            sys.exit(1)

    # --- Instruments ---
    instruments = None
    if args.instruments:
        instruments = {}
        for pair in args.instruments.split(','):
            k, _, v = pair.partition('=')
            instruments[k.strip().upper()] = v.strip()

    # --- Parse chords ---
    chords = parse_grid(source)
    if not chords:
        print("ERROR: No chords found in input.", file=sys.stderr)
        sys.exit(1)

    print(f"Chords  ({len(chords)}): {' | '.join(chords)}")
    print(f"Voices  ({len(voices)}): {' '.join(voices)}\n")

    # --- Voice leading ---
    progression = voice_progression(chords, voices=voices)
    print_table(progression)
    print()

    # --- ABC output ---
    abc_file = args.abc or 'out.abc'
    with open(abc_file, 'w') as fh:
        fh.write(to_abc(progression, title=args.title, tempo=args.tempo,
                        instruments=instruments))
    print(f"ABC written -> {abc_file}")

    if os.system('which abc2pdf > /dev/null 2>&1') == 0:
        pdf = abc_file.replace('.abc', '.pdf')
        os.system(f'abc2pdf -o {pdf} {abc_file}')
        print(f"PDF written -> {pdf}")
    elif os.system('which abcm2ps > /dev/null 2>&1') == 0:
        ps = abc_file.replace('.abc', '.ps')
        os.system(f'abcm2ps -O {ps} {abc_file}')
        print(f"PostScript written -> {ps}")
    else:
        print("Tip: install abc2pdf or abcm2ps to render PDF scores.")

    # --- MIDI output ---
    if not args.no_midi:
        midi_file = args.midi or 'out.mid'
        try:
            to_midi(progression, midi_file, tempo_bpm=args.tempo)
            print(f"MIDI written -> {midi_file}")
        except ImportError:
            print("Tip: pip install mido to enable MIDI output.")


if __name__ == '__main__':
    main()
