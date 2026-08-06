# Repository contribution rules

## Commit messages

- Use Conventional Commits: `<type>(optional-scope): <imperative summary>`.
- Use one of these prefixes unless another established type is more precise:
  `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`,
  or `revert`.
- Keep the title concise (preferably 72 characters or fewer), imperative, and
  without a trailing period.
- Always add a commit body after a blank line. Explain what changed and why;
  include important design choices, compatibility notes, or test evidence when
  useful.
- Mark breaking changes with `!` in the prefix and add a `BREAKING CHANGE:`
  footer describing the migration impact.
- Keep each commit focused on one coherent change and do not mix unrelated
  formatting or cleanup.

Example:

```text
feat(mesh): add geodesic grid generation

Generate an icosphere and its pentagon-hexagon dual topology with NumPy.
Document the supported subdivision levels and verify spherical area closure.
```

## Verification reports

- Create and maintain verification reports in both English and Korean. Keep
  the English report at `docs/verification/<name>.md` and its complete Korean
  translation at `docs/verification/<name>.ko.md`.
- Generate or update both language versions in the same change. Add reciprocal
  language links near the top of each document so readers can switch versions
  directly.
- Treat the English and Korean reports as a synchronized pair in both
  directions. Any content or wording change made first in the Korean version
  must also be reflected in the English original, just as an English change
  must be reflected in the Korean translation.
- Mirror the complete report structure in the Korean version. Preserve every
  table, figure, link, equation, command, file path, identifier, checksum,
  metric, and PASS/FAIL verdict; do not replace the translation with an
  abridged summary.
- Keep code, command-line options, mathematical notation, hashes, and numeric
  values unchanged. Translate headings, explanatory prose, captions, and
  human-readable table labels and cells.
- Before committing, compare the two versions for matching headings, table
  rows, image references, fenced command blocks, and verification verdicts.

### Korean prose quality

- Write Korean reports as natural Korean technical prose. Translate the
  meaning and reasoning, not the English sentence structure or word order.
  A Korean reader should not have to reconstruct the English source to follow
  the argument.
- Prefer active sentences with a concrete subject and verb. Use passive forms
  only when the actor is unknown or genuinely irrelevant; avoid repeated
  `-되다`, `-되어 있다`, and English-style inanimate-subject constructions.
- Replace stacked noun phrases and nominalizations with direct clauses. Split
  long English sentences when that improves readability, while preserving all
  qualifications, causal relationships, and scientific uncertainty.
- Use established Korean technical terms for ordinary prose. Retain English
  only for code identifiers, command-line options, standard acronyms, proper
  names, or terms whose translation would introduce ambiguity. When useful,
  introduce a Korean term with the English term in parentheses on first use
  and use one form consistently thereafter.
- Avoid translationese and literal calques such as unnatural uses of
  “문서화된,” “공개된 불확실성,” or “조용히 확장되다.” Also avoid vague,
  formulaic AI-style phrasing such as repeated “이는 … 보여준다,” “따라서,”
  “실질적인 개선,” “주목할 만하다,” or generic concluding restatements.
  State the concrete observation, evidence, and consequence directly.
- Do not add praise, emphasis, certainty, or interpretation absent from the
  English report. Preserve epistemic strength exactly, especially distinctions
  among confirmed causes, supported hypotheses, limitations, and unknowns.
- After drafting, read the Korean version independently from the English one.
  Revise sentences that sound translated, overlong, overly passive, or dense
  with untranslated English. Scan for repeated transition phrases and verify
  terminology consistency before running the structural parity checks above.

## Verification comparison plots

Use the Simpson–Taflove 2004 Figure 7 and Figure 8 comparison images as the
layout reference for new published-versus-reproduced verification plots.

- Place the published plot on the left and the reproduced plot on the right.
  Keep only the compact `Published` and `Reproduced` column headings; omit
  composite titles, paper captions, and paper panel markers such as `(a)` and
  `(b)`.
- Preserve every plot axis, tick label, axis label, legend, and scientifically
  meaningful annotation. Crop the published source tightly, but include the
  complete plot frame and enough space for all labels. Never cover, redraw, or
  clip a source frame merely to reduce whitespace.
- Match panel sizes by the data frame: the rectangular region enclosed by the
  axis spines, excluding tick labels, axis labels, and legends. Measure the
  published frame bounds in source pixels and place the reproduced Matplotlib
  `Axes` at the same target pixel width and height. Do not compare or match the
  outer raster-crop dimensions.
- Preserve the measured frame aspect ratio. When a figure contains multiple
  rows, measure each published frame independently, then scale and position
  each row so every published/reproduced pair has identical target frame
  dimensions.
- Maximize the data frames by trimming unused outer whitespace and using a
  sufficiently large canvas. Keep a clear inter-column gap so the reproduced
  y-axis label does not crowd the published frame. Prefer widening the canvas
  over shrinking matched frames or clipping labels.
- For reproduced plots, use 18-point axis labels and 16-point major tick labels
  and legends unless the source requires a larger accessible size. Use a white
  background and keep line, marker, grid, and legend styling consistent across
  comparison figures.
- Treat plot-layout changes as presentation-only work: do not recompute,
  smooth, rescale, truncate, or otherwise change verification data or metrics.
- Save final comparison images under `docs/verification/images/`. Before
  committing, inspect the rendered image visually, verify it with Pillow,
  assert the intended canvas and data-frame dimensions, run `git diff --check`,
  and confirm that no unrelated files changed.

Current geometry references:

- Figure 7 uses two matched `1200 x 955` pixel data frames per row on a
  `2880 x 2400` pixel canvas.
- Figure 8 uses matched `1250 x 988` pixel data frames on a `3040 x 1230`
  pixel canvas, with additional inter-column spacing for the enlarged
  reproduced y-axis label. Its reproduced panel uses 20-point axis labels and
  18-point major tick labels and legend text.
- Simpson–Taflove 2006 comparison plots use a `3400 x 1460` pixel canvas,
  20-point reproduced axis labels, and 18-point reproduced major tick labels
  and legend text. Their matched published/reproduced data frames are
  `1400 x 1111` pixels for Figure 5, `1400 x 1104` pixels for Figure 6, and
  `1400 x 1099` pixels for Figure 7, with a 300-pixel gap between the data
  frames. Measure these ratios from the original PDF page crops, not from a
  previously composed comparison image.
