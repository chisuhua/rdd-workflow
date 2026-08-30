"""Reference plugin: emits a fixed detection result.

Per phase-3-general-20260829063801: plugin in independent namespace;
exception here MUST NOT crash main loop (verified in isolation test).
"""


class SampleDetector:
    name = "sample-detector"

    def detect(self, context):
        return [{"finding": "sample-detector fired", "severity": "info"}]

    def run(self):
        try:
            return self.detect({})
        except Exception as exc:
            return [{"finding": f"plugin exception: {exc}", "severity": "error"}]