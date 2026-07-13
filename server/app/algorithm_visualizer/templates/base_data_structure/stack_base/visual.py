"""Generated official visual entry for stack_base."""

from app.algorithm_visualizer.official_runtime import run_registered_template


ALGORITHM_KEY = "stack_base"


def run(input_data: dict, tracer):
    return run_registered_template(ALGORITHM_KEY, input_data, tracer)
