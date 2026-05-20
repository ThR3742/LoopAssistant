# LoopAssistant

Voice leading generator for live looping. Give it a chord grid, tell it how many instruments you have, and it finds the smoothest note for each instrument on each chord — minimising movement, avoiding voice crossings, and covering all chord tones.

## What it does

```
Chords  (4): Dm7 | G7 | Cmaj7 | Am7
Voices  (3): Violin | Violin | Bass

Chord         Violin  Violin    Bass
------------------------------------
Dm7               F4      D4      C4
G7                F4      D4      B3
Cmaj7             E4      C4      B3
Am7               E4      C4      A3
```

Output: **ABC notation**, **PDF score**, and **MIDI** (one track per instrument).

## Requirements

```bash
# Python packages
pip install mido

# Score rendering (macOS)
brew install abcm2ps ghostscript

# Score rendering (Ubuntu/Debian)
sudo apt install abcm2ps ghostscript
```

## Usage

```bash
# Plain chord grid, 3 generic voices
python main.py "Dm7 G7 Cmaj7 Am7" --voices 3

# Name your instruments (sets pitch range + clef)
python main.py "Dm7 G7 Cmaj7" --voices "violin,violin,bass"

# Any number of voices — covers all chord tones when possible
python main.py "Dm7 G7 Cmaj7" --voices 5

# From iReal Pro (export as HTML, copy the irealb:// URL)
python main.py --ireal "irealb://..." --voices "violin,violin,bass"

# From a text file
python main.py --file grid.txt --voices "flute,violin,viola,cello,contrebasse"

# Set tempo and title
python main.py "C F G C" --voices 4 --tempo 90 --title "My Loop"

# Skip MIDI, write to custom files
python main.py "C F G C" --voices 3 --no-midi --abc score.abc
```

## Supported instruments

Each instrument name sets the playable MIDI range and the correct clef in the score.

| Instrument    | Range        | Clef   |
|---------------|--------------|--------|
| `violin`      | G3 – A6      | treble |
| `viola`       | C3 – A5      | treble |
| `cello`       | C2 – C5      | bass   |
| `bass`        | E1 – C4      | bass   |
| `contrebasse` | E1 – C4      | bass   |
| `guitar`      | E2 – E5      | treble |
| `flute`       | C4 – C7      | treble |
| `trumpet`     | E3 – C6      | treble |
| `saxophone`   | Bb3 – F#6    | treble |
| `voice`       | C3 – G5      | treble |
| `piano`       | A0 – C8      | treble |

Use a number (`--voices 3`) for generic voices with default ranges.

## Voice leading rules

- **Minimise movement** — each voice moves as few semitones as possible between chords.
- **No voice crossing** — voice 1 stays above voice 2, etc. (penalty-based).
- **Full chord coverage** — the engine penalises uncovered chord tones, so with enough voices all notes are present. With fewer voices than chord tones, it covers as many as possible.
- **Unisons and octave doublings are fine** — two voices can share the same or octave-doubled note.

## Output files

| File      | Description                                  |
|-----------|----------------------------------------------|
| `out.abc` | ABC notation (text, open in any ABC editor)  |
| `out.pdf` | Rendered score (requires abcm2ps + ghostscript) |
| `out.mid` | MIDI file, one track per voice (requires mido) |
