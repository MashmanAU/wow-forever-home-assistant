# v1.10.0 presentation comparison

## Split Image — Components V2 delivery candidate

`split_image_components_v2_preview.png` shows the new production path: the corrected 540 px Minimal Image is divided into ranks 1–5, 6–10, 11–15 and 16–18. Each PNG is placed in a separate one-item Media Gallery so Discord should stack the blocks vertically instead of shrinking them into a gallery grid.

Select `split_image` and use `/daily-live-test` to assess the real Discord inline presentation. The existing modes below remain available unchanged.

The five prototypes use the same supplied 18-character roster. The new previews include clearly labelled illustrative 24-hour level movement so the ordering and `-` behaviour can be reviewed. No generative image model is used. Re-run `python prototypes/render_prototypes.py` to reproduce every output.

| Option | Output | Strengths | Trade-offs | Recommended use |
|---|---|---|---|---|
| Improved native embed | `native_embed_preview.md` and `native_embed_payload.json` | Searchable, accessible, compact, lowest delivery risk | Discord controls typography and does not support per-name colours | Safe fallback and text-first preference |
| Components V2 | `components_v2_preview.md` and `components_v2_payload.json` | Cleaner native grouping and separators; strong mobile behaviour | Commentary must be a separate normal message; arbitrary text colours remain unavailable | Best fully native layout |
| Deterministic Pillow image | `image_two_column_preview.png` | Genuine class colours, bars, balanced two-column layout, identical on every client | Image text is not selectable; attachment permission required | Legacy detailed graphical mode |
| Minimal image | `minimal_image_preview.png` | 540 px canvas, flat 54 px rows, 48 px class glyphs, 46 px level badges, 18 px bold movement and 27 px bold class-coloured names | Deliberately omits secondary facts by default | Preferred graphical mode |
| Monospaced table | `table_preview.md` | Searchable, exact, compact, Unicode-width aware and mobile-conscious | No arbitrary class colours or graphical icons | Preferred information mode |

## Release decision

v1.9.2 keeps `minimal_image` as the default, fixes the production Alpine font path, preserves `table`, `image`, `native_embed` and `components_v2`, and keeps the displayed `/60` level suffix removed from all five. Existing Home Assistant installations normally retain their saved configuration on update. The scheduled report and `/daily-live-test` call the same delivery function, so the live test remains a true dress rehearsal of the selected mode.
