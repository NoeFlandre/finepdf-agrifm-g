# Automatic quality contract

The released pipeline has no human-in-the-loop step. These tasks are deterministic code paths. The run specification controls them:

- split assignment;
- image extraction;
- visual sanity checks;
- deduplication;
- packaging;
- verification.

The repository can contain historical inspection artifacts from earlier experiments. They are not inputs to the current build. They do not define the published split contract. Do not use them as release metrics.

For current quality evidence, use these items: the generated `stats.json`, the receipt hashes, the schema checks, the decoded-image checks, and the split-disjointness verification. The pipeline does the split-disjointness verification after the Grid’5000 run.
