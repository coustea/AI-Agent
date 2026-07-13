"""Generated official visual entry for quick_partition."""

from app.algorithm_visualizer.official_runtime import run_registered_template


ALGORITHM_KEY = "quick_partition"


def run(input_data: dict, tracer):
    return run_registered_template(ALGORITHM_KEY, input_data, tracer)
