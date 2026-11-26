"""Pytest wrapper ensuring all 5 Attesta benchmarks pass 100%."""

from __future__ import annotations

from scripts.run_benchmarks import run_all_benchmarks


def test_all_five_benchmarks_pass() -> None:
    res = run_all_benchmarks()
    assert res["byte_flip_tamper_caught"] == 100
    assert res["chain_break_caught"] == 50
    assert res["clean_chain_false_flags"] == 0
    assert res["idempotent_hits"] == 20
    assert res["log_formats_parsed"] == 5
    assert res["e2e_pipeline_valid"] is True
