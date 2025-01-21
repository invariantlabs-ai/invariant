from _pytest.outcomes import Failed

from invariant.testing.utils.packages import is_package_installed, is_program_installed


def should_fail_with(num_assertion: int | None = None):
    def decorator(fct):
        def wrapper(*args, **kwargs):
            try:
                fct(*args, **kwargs)
                if num_assertion != 0:
                    assert False, (
                        f"Expected test {fct.__name__} to fail, but it unexpectedly passed"
                    )
            except Failed as e:
                first_line = str(e).split("\n")[0]
                assert str(num_assertion) in first_line, (
                    f"Expected test case to fail with {num_assertion} Invariant assertion(s), but got {first_line}"
                )

        return wrapper

    return decorator


def test_is_program_installed():
    """Test the is_program_installed function."""
    assert is_program_installed("bash")
    assert is_program_installed("grep")
    assert not is_program_installed("nonexistent_program")
    assert not is_program_installed("bashbashbash123")


def test_is_package_installed():
    """Test the is_package_installed function."""
    assert is_package_installed("pytest")
    assert is_package_installed("pydantic")
    assert not is_package_installed("nonexistent_package")
    assert not is_package_installed("pytestpytestpytest")
