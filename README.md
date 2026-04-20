# Yedi Benchmark

A multi-dimensional strategic-reasoning benchmark for large language and
vision-language models. Yedi is a card-merging game with up to seven
independent cognitive dimensions (numerical, visual, spatial, verbal, and
three secondary axes); merge outcomes compound *multiplicatively* across
the active dimensions, so one weak dimension collapses an otherwise
strong merge. This produces a clean probe of compositional reasoning
that single-axis and additive benchmarks cannot provide.

## Paper

The preprint describing the benchmark is in this repository:
**[`paper/yedi_benchmark.pdf`](paper/yedi_benchmark.pdf)**

## Links

- **Video walkthroughs of the original mobile game**:
  <https://www.youtube.com/@mindfreegames7459>
- **Code and benchmark** (this repo): <https://github.com/yilmazozgur/yedi-v4>

## What this repo contains

- `Assets/` — Unity project for the game itself and the agent bridge.
- `yedi_benchmark/` — Python package with the Gymnasium environment,
  FastAPI server, agent wrappers (random, greedy, LLM, VLM), benchmark
  configurations, and analysis scripts.
- `paper/` — LaTeX source and compiled PDF of the benchmark paper.

## License

TBD.
