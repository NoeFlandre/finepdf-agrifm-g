# Automatic quality contract

The released pipeline has no human-in-the-loop step. Split assignment, image extraction, visual sanity checks, deduplication, packaging, and verification are deterministic code paths driven by the run specification.

The repository may contain historical inspection artifacts from earlier experiments. They are not inputs to the current build, do not define the published split contract, and must not be treated as release metrics.

For current quality evidence, use the generated `stats.json`, receipt hashes, schema checks, decoded-image checks, and the split-disjointness verification performed after the Grid’5000 run.
