"""Generated official visual entry for dp_fibonacci."""

from app.algorithm_visualizer.official_runtime import run_registered_template


ALGORITHM_KEY = "dp_fibonacci"


def run(input_data: dict, tracer):
    return run_registered_template(ALGORITHM_KEY, input_data, tracer)
