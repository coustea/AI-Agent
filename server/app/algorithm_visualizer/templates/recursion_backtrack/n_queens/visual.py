"""Generated official visual entry for n_queens."""

from app.algorithm_visualizer.official_runtime import run_registered_template


ALGORITHM_KEY = "n_queens"


def run(input_data: dict, tracer):
    return run_registered_template(ALGORITHM_KEY, input_data, tracer)
