# Dataset schema

The Hub dataset exposes two splits: `conventional` and `sustainable`. Both use the same schema and contain one row per retained embedded raster image.

```python
from datasets import load_dataset

dataset = load_dataset("NoeFlandre/finepdf-agrifm-g")
dataset["conventional"][0]
dataset["sustainable"][0]
```

| Field | Type | Meaning |
| --- | --- | --- |
| `image` | `Image` | Decoded embedded raster image |
| `doc_id` | `string` | Normalised FinePDF document id |
| `agriculture_split` | `string` | `conventional` or `sustainable` |
| `page` | `int32` | Zero-based source page |
| `image_index` | `int32` | Image position within the document |
| `width`, `height` | `int32` | Image dimensions in pixels |
| `image_sha256` | `string` | Image content hash |
| `image_path` | `string` | Temporary build-relative image path |
| `n_colours` | `int32` | Diagnostic colour count |
| `edge_density` | `float32` | Diagnostic edge share |
| `caption` | `string` | Optional extracted PDF caption; never a filter |
| `source_url` | `string` | Original PDF URL |
| `pdf_sha256` | `string` | Retrieved PDF hash |
| `text` | `string` | English FinePDF text used for gating and classification |
| `n_images_in_doc` | `int32` | Number of retained images in the document |
| `extraction_version` | `int32` | Extraction contract version |

## Selection

The broad lexicon is used before fetching to avoid downloading clearly unrelated documents. A passing document is assigned to the category with the stronger exact-match score from the extended conventional and sustainable lexicons. Ties and documents with no category evidence are dropped. All embedded images from accepted documents are then considered.

Visual checks remove invalid or tiny images, single-colour and nearly blank images, overwhelmingly flat-colour images, near-uniform low-colour placeholders, dense page-shaped grayscale document scans, extreme aspect ratios, and exact duplicates. A full-page colour photograph or figure remains eligible. These are narrow noise checks, not topical image classifiers.

The PDFs themselves are not redistributed. URLs and hashes preserve provenance, but source availability and licensing are not guaranteed.
