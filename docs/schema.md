# Dataset schema

A build produces one directory:

```
out/dataset/
├── metadata.jsonl        one JSON record per document
├── pdfs/<doc_id>.pdf     the source document as retrieved
└── images/<doc_id>/000.png, 001.png, …
```

## One record

```json
{
  "doc_id": "urn_uuid_3aa6728e-f35e-437a-a520-56fb2fab71c9",
  "source_url": "https://example.org/report.pdf",
  "pdf_path": "pdfs/urn_uuid_3aa6728e-….pdf",
  "text": "…the FinePDF extraction of the document…",
  "images": [
    {"path": "images/urn_uuid_3aa6728e-…/000.png", "page": 0,
     "width": 960, "height": 540, "format": "png"}
  ],
  "n_images": 1,
  "extraction_version": 1
}
```

| Field | Meaning |
| --- | --- |
| `doc_id` | FinePDF id, lowercased and reduced to `[a-z0-9-_]` |
| `source_url` | where the PDF was crawled from — the provenance record |
| `pdf_path` | dataset-relative path to the stored PDF |
| `text` | FinePDF's own extracted text, carried through unchanged |
| `images` | every usable embedded raster image, in page order, re-encoded to PNG |
| `n_images` | derived from `images`, never stored independently |
| `extraction_version` | bumped whenever extraction changes the stored bytes |

Images smaller than 32 px on either side are dropped as rules, bullets and artefacts.
Everything else is kept: **no agricultural filtering happens at this stage**.
