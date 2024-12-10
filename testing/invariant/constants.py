"""Constants for the Invariant Test Runner."""

INVARIANT_RUNNER_TEST_RESULTS_DIR = ".invariant/test_results"
INVARIANT_AP_KEY_ENV_VAR = "INVARIANT_API_KEY"
INVARIANT_TEST_RUNNER_CONFIG_ENV_VAR = "INVARIANT_TEST_RUNNER_CONFIG"

# used to pass the actual terminal width to the test runner
# (if not available, we'll use a fallback, but nice to have)
INVARIANT_TEST_RUNNER_TERMINAL_WIDTH_ENV_VAR = "INVARIANT_TERMINAL_WIDTH"

# used to pass the agent params to the test runner
INVARIANT_AGENT_PARAMS_ENV_VAR = "INVARIANT_AGENT_PARAMS"
