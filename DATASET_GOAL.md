# FinePDF Agriculture Image Dataset Goal

Build a diverse, English-only dataset of real agricultural imagery from FinePDF for AGRIFM-G.
The dataset has two mutually exclusive document-topic splits:

- `conventional`: tractors, tillers, combines, farm machinery and workers, fields, barns, silos,
  livestock facilities, irrigation, harvesting, and other operational or conventional farming.
- `sustainable`: permaculture, agroecology, agroforestry, organic and regenerative practices,
  hydroponics, aquaponics, conservation farming, biodiversity, and related systems.

Prefer useful photographs of farms, agricultural work, equipment, crops, livestock, and practices.
Remove page scans, blank/near-solid placeholders, charts, tables, diagrams, maps, screenshots,
icons, and clearly unrelated images. Extract actual embedded PDF images; do not publish a rendered
page as a substitute for its figures. Captions are optional metadata and never decide whether an
image is kept. Automated filtering runs on Grid'5000; no manual review is part of the build.
