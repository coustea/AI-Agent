"""Generated official visual entry for kmp_match."""

from app.algorithm_visualizer.official_runtime import run_registered_template


ALGORITHM_KEY = "kmp_match"


def run(input_data: dict, tracer):
    return run_registered_template(ALGORITHM_KEY, input_data, tracer)
