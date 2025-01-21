"""Test the factuality module."""

from invariant.testing import IsFactuallyEqual, Trace, assert_false, assert_that


def test_is_factually_equal():
    """Test the IsFactuallyEqual assertion."""
    question = "Who wins the American Election of 2024?"

    # Test case: super strict agreement
    trace = Trace(trace=[{"role": "user", "content": "Trump"}])
    with trace.as_context():
        expected_output = "Trump"
        assert_that(trace.messages()[0]["content"], IsFactuallyEqual(expected_output, question))
        expected_output = "Donald Trump"
        assert_that(
            trace.messages()[0]["content"],
            IsFactuallyEqual(expected_output, question, IsFactuallyEqual.Agreement.FUZZY_AGREEMENT),
        )

    # Test case: disagreement
    trace = Trace(trace=[{"role": "user", "content": "Harris"}])
    with trace.as_context():
        expected_output = "Trump"
        assert_false(
            trace.messages()[0]["content"].matches(IsFactuallyEqual(expected_output, question))
        )
        expected_output = "Donald Trump"
        assert_false(
            trace.messages()[0]["content"].matches(IsFactuallyEqual(expected_output, question))
        )

    # Test case: strict agreement:
    question = "who's the best Japanese directors"
    trace = Trace(
        trace=[
            {
                "role": "user",
                "content": "Akira Kurosawa, Hayao Miyazaki,Takeshi Kitano,Isao Takahata",
            }
        ]
    )
    with trace.as_context():
        expected_output = "Isao Takahata"
        # under strict agreement, the output is not close to the expected output (only 1/4 directors are correct)
        assert_false(
            trace.messages()[0]["content"].matches(
                IsFactuallyEqual(
                    expected_output,
                    question,
                    IsFactuallyEqual.Agreement.SUPER_STRICT_AGREEMENT,
                )
            )
        )
        # under strict agreement, the output is close to the expected output (3/4 directors are correct)
        assert_false(
            trace.messages()[0]["content"].matches(
                IsFactuallyEqual(
                    expected_output,
                    question,
                    IsFactuallyEqual.Agreement.SUPER_STRICT_AGREEMENT,
                )
            )
        )

    # sTest case: fuzzy agreement:
    question = "who's the best Japanese directors"
    trace = Trace(
        trace=[
            {
                "role": "user",
                "content": "Akira Kurosawa, Hayao Miyazaki,Takeshi Kitano,Isao Takahata",
            }
        ]
    )
    with trace.as_context():
        expected_output = "Akira Kurosawa, Yasujiro Ozu,Hayao Miyazaki,Kenji Mizoguchi,Hirokazu Kore-eda,Takeshi Kitano,Masaki Kobayashi,Isao Takahata"
        assert_that(
            trace.messages()[0]["content"],
            IsFactuallyEqual(expected_output, question, IsFactuallyEqual.Agreement.FUZZY_AGREEMENT),
        )
        assert_that(
            trace.messages()[0]["content"],
            IsFactuallyEqual(expected_output, question, IsFactuallyEqual.Agreement.FUZZY_AGREEMENT),
        )
