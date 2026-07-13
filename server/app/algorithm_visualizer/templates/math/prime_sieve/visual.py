"""Generated official visual entry for prime_sieve."""

from app.algorithm_visualizer.official_runtime import run_registered_template


ALGORITHM_KEY = "prime_sieve"


def run(input_data: dict, tracer):
    return run_registered_template(ALGORITHM_KEY, input_data, tracer)
