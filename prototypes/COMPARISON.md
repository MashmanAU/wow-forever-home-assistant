# v1.9.1 presentation comparison

The five prototypes use the same supplied 18-character roster. The new previews include clearly labelled illustrative 24-hour level movement so the ordering and `-` behaviour can be reviewed. No generative image model is used. Re-run `python prototypes/render_prototypes.py` to reproduce every output.

| Option | Output | Strengths | Trade-offs | Recommended use |
|---|---|---|---|---|
| Improved native embed | `native_embed_preview.md` and `native_embed_payload.json` | Searchable, accessible, compact, lowest delivery risk | Discord controls typography and does not support per-name colours | Safe fallback and text-first preference |
| Components V2 | `components_v2_preview.md` and `components_v2_payload.json` | Cleaner native grouping and separators; strong mobile behaviour | Commentary must be a separate normal message; arbitrary text colours remain unavailable | Best fully native layout |
| Deterministic Pillow image | `image_two_column_preview.png` | Genuine class colours, bars, balanced two-column layout, identical on every client | Image text is not selectable; attachment permission required | Legacy detailed graphical mode |
| Minimal image | `minimal_image_preview.png` | 660 px canvas, flat 48 px rows, heavy 34 px names, large class glyphs and clear Level → 24h reading order | Deliberately omits secondary facts by default | Preferred graphical mode |
| Monospaced table | `table_preview.md` | Searchable, exact, compact, Unicode-width aware and mobile-conscious | No arbitrary class colours or graphical icons | Preferred information mode |

## Release decision

v1.9.1 keeps `minimal_image` as the default, preserves `table`, `image`, `native_embed` and `components_v2`, and removes the displayed `/60` level suffix from all five. Existing Home Assistant installations normally retain their saved configuration on update. The scheduled report and `/daily-live-test` call the same delivery function, so the live test remains a true dress rehearsal of the selected mode.
