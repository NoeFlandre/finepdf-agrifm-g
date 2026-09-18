Feature: Build a tiny FinePDF sample dataset
  As the AGRIFM-G team
  I want a reproducible, verifiable tiny dataset
  So that the extraction pipeline can be trusted before it is scaled up

  Scenario: Building the sample produces a complete, valid dataset directory
    Given a manifest of 3 documents drawn from a local fixture corpus
    When I build the dataset
    Then the output contains one PDF per document
    And metadata.jsonl holds one valid record per document
    And every referenced image file exists on disk
    And the dataset verifies clean

  Scenario: A document whose PDF cannot be read is left out rather than breaking the build
    Given a manifest of 3 documents whose PDFs are not readable
    When I build the dataset
    Then the dataset is empty but still verifies clean
