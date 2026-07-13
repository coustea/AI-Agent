"""Generated official visual entry for subset_enum."""

from app.algorithm_visualizer.official_runtime import run_registered_template


ALGORITHM_KEY = "subset_enum"


def run(input_data: dict, tracer):
    return run_registered_template(ALGORITHM_KEY, input_data, tracer)
