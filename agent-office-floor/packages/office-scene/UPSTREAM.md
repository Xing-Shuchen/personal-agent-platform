# Upstream source record

- Repository: https://github.com/chaitanyagiri/munder-difflin
- Commit: `9e26ca5f692ba00d50334c79f4b6d36416e3bffa`
- Source license: MIT; see `../../notices/MD-LICENSE`.
- `SeatPool.ts` also records ancestry from `shahar061/the-office`; its ISC notice must be retained before redistributing a release that uses it.
- Upstream art is excluded pending separate authorization.

| Local file | Original path | Original SHA-256 | Local changes |
| --- | --- | --- | --- |
| `SeatPool.ts` | `src/renderer/src/scene/office/SeatPool.ts` | `b2394f02a00dc922f64d30b820863a78fe550eb6b7683a281166a99ae4d44381` | unmodified |
| `pathfinding.ts` | `src/renderer/src/scene/office/pathfinding.ts` | `38a7cf40dd5e2ffab00fda7df9433fd7a0e99615378c19e0294af7ef70e5d5b4` | unmodified |
| `Camera.ts` | `src/renderer/src/scene/office/Camera.ts` | `421bd95c8af7f8bfaabfd22bd3baadc7ccdfe04112cc8baa1675d2aaddca8701` | added immediate target snap for reduced motion |
| `glRecovery.ts` | `src/renderer/src/scene/office/glRecovery.ts` | `3ca31c8447a10f85c929e04454b3c73f7455fc051e4bb990f93c452e03f932a6` | moved retry budget to scene lifetime |
| `TiledMapRenderer.ts` | `src/renderer/src/scene/office/TiledMapRenderer.ts` | `86af95a6aea647bc340b2276ffabb04a15011a343cf82414f6c8300599c5dfa3` | unmodified |
| `DeskScreen.ts` | `src/renderer/src/scene/office/DeskScreen.ts` | `ccfe38977508052af3d9cf7747ddbfd9aa3e10ad4735e652ec73ed1da455f005` | adapted for explicit theme GIDs and 16 px owned art |
| `CharacterSprite.ts` | `src/renderer/src/scene/office/CharacterSprite.ts` | `360da47aeba2fa972e624d29b8ca8d87a34a1f5cd26ca229eed15b23826bf143` | added reduced-motion frame freeze and source comments |
| `cast.ts` | `src/renderer/src/scene/office/cast.ts` | `4a08c1b1188ed0b1a92fc9dfb36360899c01507f16bead7b920c489205ed66c2` | cache version and local import path |
| `portraitArt.ts` | `src/renderer/src/scene/office/portraitArt.ts` | `74b77b14b88bca629eb30f26369ffb4557176b2e64e7fe11746a439b88ae407d` | local import path |
| `Character.ts` | `src/renderer/src/scene/office/Character.ts` | `aeebcb005cb9824d8d4a1fe2c5487478c9c6628ffd27af86b999df4382e16d62` | rewritten around FloorState presentation and pathfinding |
| `ToolBubble.ts` | `src/renderer/src/scene/office/ToolBubble.ts` | `0f882bf603fa8e898cc55eb6407de18e11af7905496c87aea1e51d5aff7f0a6c` | show verified tool name only; add exact tool icons and reduced-motion snap |
| `ThoughtBubble.ts` | `src/renderer/src/scene/office/ThoughtBubble.ts` | `b41b7a57327dce69bfb98ec23c944dc11ec2fa89ccd347615aec5cd9310487c3` | show sourced, bounded FloorState summary only; use owned colors and reduced-motion snap |
| `MessageEnvelope.ts` | `src/renderer/src/scene/office/MessageEnvelope.ts` | `5aa0d2fa273f86d11b92e8107cae49644dbe3d3a6efb224a64f04aed4b237b10` | replace hive speech acts with verified FloorHandoff kinds and owned palette |
