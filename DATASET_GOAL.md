# FinePDF Agriculture Image Dataset Goal

Build a diverse, English-only dataset of real agricultural images from FinePDF for AGRIFM-G.
The dataset has two document-topic splits. A document is in only one split.

- `conventional`: tractors, tillers, combines, farm machinery and workers, fields, barns, silos,
  livestock facilities, irrigation, harvesting, and other operational or conventional farming.
- `sustainable`: permaculture, agroecology, agroforestry, organic and regenerative practices,
  hydroponics, aquaponics, conservation farming, biodiversity, and related systems.

Prefer useful photographs of farms, agricultural work, equipment, crops, livestock, and practices.
Remove these items: page scans, blank or near-solid placeholders, charts, tables, diagrams, maps,
screenshots, icons, and clearly unrelated images. Extract the actual embedded PDF images. Do not
publish a rendered page in place of its figures. Captions are optional metadata. A caption never
decides if the pipeline keeps an image. The automated filtering runs on Grid'5000. The build has
no manual review.
