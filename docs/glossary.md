# Glossary

This page defines the project terms. Each term has one meaning in all the documentation.

| Term | Meaning |
| --- | --- |
| AGRIFM-G | The name of the project and of the dataset. |
| FinePDF | The public source dataset of PDF documents. It stores URLs and text. It does not store PDF bytes. |
| Pipeline | The automatic sequence of steps that converts FinePDF documents into images. |
| Split | A named part of the dataset. The two splits are `conventional` and `sustainable`. |
| `conventional` | The split for conventional or industrial agriculture. |
| `sustainable` | The split for sustainable or alternative agriculture. |
| Lexicon | A list of English terms. The pipeline uses it to classify the text of a document. |
| Text gate | The broad text check. It rejects documents that are not about agriculture. |
| Category | The group (`conventional` or `sustainable`) that the pipeline assigns to a document. |
| Embedded raster image | An image that is stored inside a PDF as pixels. |
| Pixel check | A cheap check on the pixels of an image. It removes blank images, near-solid images, and page-shaped scans. |
| CLIP | The pinned zero-shot model that compares an image with text prompts. |
| Screen | The CLIP step. It removes only the images that it confidently rates as document-like or unrelated. |
| Score | A model preference value. It is not a calibrated probability. |
| Caption | Optional text that the extractor finds near an image. It is metadata. It is never a filter. |
| Provenance | The source URL and the hashes of a row. They show where the image comes from. |
| Grid’5000 | The computing platform where the heavy build runs. |
| Node | One reserved machine on Grid’5000. |
| Run | One execution of the scaled build. A run has a `run-id`. |
| Row group | A block of rows in a parquet file. The pipeline saves one checkpoint for each row group. |
| Checkpoint | A saved state of a run. It lets a run resume. |
| Receipt | The record of a run. It has the hashes that the verification uses. |
| Hub | The Hugging Face Hub. It hosts the published dataset. |
| ADR | Architecture decision record. It records one design decision. |
