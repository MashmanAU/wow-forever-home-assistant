# v1.8.0 real-data presentation comparison

The three prototypes use the same 18 characters and factual values transcribed from the supplied `/daily-live-test` screenshot. No generative image model is used. Re-run `python prototypes/render_prototypes.py` to reproduce every output.

| Option | Output | Strengths | Trade-offs | Recommended use |
|---|---|---|---|---|
| Improved native embed | `native_embed_preview.md` and `native_embed_payload.json` | Searchable, accessible, compact, lowest delivery risk | Discord controls typography and does not support per-name colours | Safe fallback and text-first preference |
| Components V2 | `components_v2_preview.md` and `components_v2_payload.json` | Cleaner native grouping and separators; strong mobile behaviour | Commentary must be a separate normal message; arbitrary text colours remain unavailable | Best fully native layout |
| Deterministic Pillow image | `image_two_column_preview.png` | Genuine class colours, bars, balanced two-column layout, identical on every client | Image text is not selectable; attachment permission required | Default graphical mode |

## Release decision

v1.8.0 defaults to `image`, preserves `native_embed` as both a selectable mode and automatic fallback, and includes `components_v2` for users who prefer an entirely Discord-native layout. The scheduled report and `/daily-live-test` call the same delivery function, so the live test is a true dress rehearsal of the selected mode.
