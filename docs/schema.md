# Dataset schema

The Hub dataset has two splits: `conventional` and `sustainable`. Both splits use the same schema. Each row is one retained embedded raster image.

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
| `agriculture_photo_score` | `float32` | CLIP class preference for agricultural photography |
| `document_figure_score` | `float32` | CLIP class preference for document figures and graphics |
| `unrelated_photo_score` | `float32` | CLIP class preference for unrelated photographs |
| `caption` | `string` | Optional extracted PDF caption; never a filter |
| `source_url` | `string` | Original PDF URL |
| `pdf_sha256` | `string` | Retrieved PDF hash |
| `text` | `string` | English FinePDF text used for gating and classification |
| `n_images_in_doc` | `int32` | Number of retained images in the document |
| `extraction_version` | `int32` | Extraction contract version |

## Selection

The pipeline uses the broad lexicon before it fetches documents. This prevents the download of clearly unrelated documents. The pipeline assigns a passing document to the category that has the stronger exact-match score. It uses the extended conventional and sustainable lexicons. It drops ties. It also drops documents that have no category evidence. Then the pipeline considers all embedded images from the accepted documents.

The visual checks remove these items:

- invalid images and tiny images;
- single-colour images and nearly blank images;
- overwhelmingly flat-colour images;
- near-uniform low-colour placeholders;
- dense page-shaped grayscale scans;
- extreme aspect ratios;
- exact duplicates.

Then a pinned CLIP model compares farm photography with document figures and unrelated photos. The pipeline removes only confident negatives. Uncertain images stay. The three reported scores are model preferences. They are not calibrated probabilities.

The pipeline does not redistribute the PDFs. The URLs and the hashes keep the provenance. Source availability and licensing are not guaranteed.
