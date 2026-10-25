# Examples

Generate the fixtures with:

```bash
python examples/make_examples.py
```

| File | What it demonstrates |
|------|----------------------|
| `sample.png` | A valid RGB PNG — magic identification, chunk structure (IHDR/IDAT/IEND), region map. |
| `sample.zip` | A deflate ZIP — central-directory + local-header parsing and per-entry sizes. |
| `packed.bin` | A low-entropy header followed by a high-entropy (random) payload — the sliding-window entropy chart jumps to ~8 bits/byte, mimicking a packed/encrypted section. |
| `polyglot.bin` | A plain wrapper with a PNG and JPEG embedded at non-zero offsets — embedded-file carving. |
| `script.sh` | A shebang text file — text magic, ASCII strings and high printable ratio. |

Try:

```bash
bytelens analyze examples/polyglot.bin
bytelens structures examples/sample.zip
bytelens entropy examples/packed.bin
bytelens serve examples/polyglot.bin
```
