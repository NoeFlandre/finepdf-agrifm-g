from agrifm_g.adapters.finepdf import DEFAULT_SHARD, FinePdfRow, ParquetRowSource


class StubSource(ParquetRowSource):
    def _read_row_group(self):
        return [
            {"id": f"d{i}", "url": f"https://example.org/{i}.pdf", "text": f"t{i}"}
            for i in range(4)
        ]


def test_the_window_is_the_row_group_and_is_read_once():
    source = StubSource()
    assert source.total() == 4
    assert source.rows([0, 3]) == [
        FinePdfRow(doc_id="d0", url="https://example.org/0.pdf", text="t0"),
        FinePdfRow(doc_id="d3", url="https://example.org/3.pdf", text="t3"),
    ]
    assert source.rows([1])[0].doc_id == "d1"


def test_the_hub_path_points_at_the_configured_shard():
    assert ParquetRowSource().path.endswith(f"/eng_Latn/train/{DEFAULT_SHARD}")
