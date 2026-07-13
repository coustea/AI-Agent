"""Generated official visual entry for mod_arithmetic."""

from app.algorithm_visualizer.official_runtime import run_registered_template


ALGORITHM_KEY = "mod_arithmetic"


def run(input_data: dict, tracer):
    return run_registered_template(ALGORITHM_KEY, input_data, tracer)
