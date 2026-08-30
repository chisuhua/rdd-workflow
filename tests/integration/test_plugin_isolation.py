"""Mock plugin raising exception must not crash main loop (acceptance #2).

Per phase-3-general-20260829063801: plugin MUST be isolated; exceptions
in plugin code MUST NOT propagate to caller.
"""
from _lib.plugins.sample_detector import SampleDetector


class BoomDetector(SampleDetector):
    """Variant that always raises — verifies isolation."""
    name = "boom-detector"

    def detect(self, context):
        raise RuntimeError("boom")


def test_plugin_exception_isolated():
    out = BoomDetector().run()
    assert isinstance(out, list)
    assert out[0]["finding"].startswith("plugin exception")
    assert out[0]["severity"] == "error"


def test_sample_detector_run_returns_list():
    out = SampleDetector().run()
    assert isinstance(out, list)
    assert out[0]["finding"] == "sample-detector fired"
    assert out[0]["severity"] == "info"