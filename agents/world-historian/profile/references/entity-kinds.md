# World Historian entity kinds

Use exactly one of these 13 canonical kinds for every entity:

- `company` — a commercial business; example: OpenAI.
- `organization` — a non-commercial institution or organized group; example: CERN.
- `person` — an individual human; example: Sam Altman.
- `product` — a named offering to users; example: ChatGPT.
- `model` — a named AI or statistical model; example: GPT-5.
- `software` — software that is not principally a product brand; example: Linux.
- `benchmark` — a named evaluation suite or test; example: MMLU.
- `aggregator` — a service that aggregates information or content; example: Google News.
- `media` — a publication, broadcaster, or news outlet; example: Reuters.
- `government` — a public authority or state body; example: European Commission.
- `place` — a geographical location; example: San Francisco.
- `concept` — an idea, policy, standard, or abstract subject; example: AI safety.
- `unknown` — a pre-classification sentinel; example: an as-yet-unreviewed name.

`unknown` is only for existing stock awaiting maintenance. A capture or follow
bundle must never write `unknown`: classify the entity before persisting it.
