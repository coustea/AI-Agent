"""Generated official visual entry for gcd_euclidean."""

from app.algorithm_visualizer.official_runtime import run_registered_template


ALGORITHM_KEY = "gcd_euclidean"


def run(input_data: dict, tracer):
    return run_registered_template(ALGORITHM_KEY, input_data, tracer)
