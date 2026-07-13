"""Generated official visual entry for monotonic_queue."""

from app.algorithm_visualizer.official_runtime import run_registered_template


ALGORITHM_KEY = "monotonic_queue"


def run(input_data: dict, tracer):
    return run_registered_template(ALGORITHM_KEY, input_data, tracer)
