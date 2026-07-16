"""Generated official visual entry for bubble_sort."""

from app.algorithm_visualizer.official_runtime import run_registered_template


ALGORITHM_KEY = "bubble_sort"


def run(input_data: dict, tracer):
    return run_registered_template(ALGORITHM_KEY, input_data, tracer)
