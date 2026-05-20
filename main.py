#!/usr/bin/env python3
"""
LoopAssistant — Voice leading generator for live loops.

Usage:
  python main.py "Cm7 F7 Bbmaj7 Eb7"
  python main.py --file grid.txt --midi out.mid --abc out.abc
  python main.py --ireal "irealb://..."
"""

import argparse
import sys
import os

from grid_parser import parse_grid
from voice_leading import voice_progression
from output import to_abc, to_midi, print_table


def main():
    parser = argparse.ArgumentParser(
        description='LoopAssistant: generate SATB voice leading from a chord grid'
    )
    parser.add_argument('grid', nargs='?', help='Chord symbols (space separated)')
    parser.add_argument('--file', '-f', help='Read chord grid from file')
    parser.add_argument('--ireal', help='iReal Pro URL (irealb://...)')
    parser.add_argument('--abc', help='Output ABC notation file (default: out.abc)')
    parser.add_argument('--midi', help='Output MIDI file (default: out.mid)')
    parser.add_argument('--title', default='Loop Assistant', help='Score title')
    parser.add_argument('--tempo', type=int, default=120, help='Tempo in BPM')
    parser.add_argument('--no-midi', action='store_true', help='Skip MIDI output')
    parser.add_argument(
        '--instruments',
        help='Voice→instrument mapping, e.g. "S=Violin,A=Viola,T=Cello,B=Bass"'
    )

    args = parser.parse_args()

    # Gather source text
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

    # Parse instruments mapping
    instruments = None
    if args.instruments:
        instruments = {}
        for pair in args.instruments.split(','):
            k, _, v = pair.partition('=')
            instruments[k.strip()] = v.strip()

    # Parse chords
    chords = parse_grid(source)
    if not chords:
        print("ERROR: No chords found in input.", file=sys.stderr)
        sys.exit(1)

    print(f"Chords detected ({len(chords)}): {' | '.join(chords)}\n")

    # Voice leading
    progression = voice_progression(chords)

    # Terminal table
    print_table(progression)
    print()

    # ABC output
    abc_file = args.abc or 'out.abc'
    abc_content = to_abc(progression, title=args.title, tempo=args.tempo,
                         instruments=instruments)
    with open(abc_file, 'w') as fh:
        fh.write(abc_content)
    print(f"ABC written → {abc_file}")

    # Try abc2pdf
    if os.system(f'which abc2pdf > /dev/null 2>&1') == 0:
        pdf_file = abc_file.replace('.abc', '.pdf')
        os.system(f'abc2pdf -o {pdf_file} {abc_file}')
        print(f"PDF written → {pdf_file}")
    elif os.system('which abcm2ps > /dev/null 2>&1') == 0:
        ps_file = abc_file.replace('.abc', '.ps')
        os.system(f'abcm2ps -O {ps_file} {abc_file}')
        print(f"PostScript written → {ps_file}")
    else:
        print("Tip: install abc2pdf or abcm2ps to render PDF scores.")

    # MIDI output
    if not args.no_midi:
        midi_file = args.midi or 'out.mid'
        try:
            to_midi(progression, midi_file, tempo_bpm=args.tempo)
            print(f"MIDI written → {midi_file}")
        except ImportError:
            print("Tip: pip install mido to enable MIDI output.")


if __name__ == '__main__':
    main()
