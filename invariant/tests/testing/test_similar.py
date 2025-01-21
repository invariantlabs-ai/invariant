# get Failed exception from pytest

from invariant.testing import IsSimilar, Trace, assert_that
from invariant.tests.testing.testutils import should_fail_with


@should_fail_with(num_assertion=0)
def test_is_similar_levenshtein():
    # not passing metrics parameter, default using Levenshtein metric or pass IsSimilar.LEVENSHTEIN
    trace = Trace(trace=[{"role": "user", "content": "Hello there"}])
    with trace.as_context():
        # test case: expected value is longer than actual value
        assert_that(trace.messages()[0]["content"], IsSimilar("hello where", 0.5))


@should_fail_with(num_assertion=0)
def test_is_similar_levenshtein_1():
    # not passing metrics parameter, default using Levenshtein metric or pass IsSimilar.LEVENSHTEIN
    trace = Trace(trace=[{"role": "user", "content": "Hello there"}])
    with trace.as_context():
        # test case: expected value is longer than actual value
        assert_that(trace.messages()[0]["content"], IsSimilar("hello where", 0.5))


@should_fail_with(num_assertion=1)
def test_is_similar_levenshtein_2():
    # not passing metrics parameter, default using Levenshtein metric or pass IsSimilar.LEVENSHTEIN
    trace = Trace(trace=[{"role": "user", "content": "Hello there"}])
    with trace.as_context():
        # test case: expected value is longer than actual value
        assert_that(trace.messages()[0]["content"], IsSimilar("hello where", 0.5))

        assert_that(
            trace.messages()[0]["content"],
            IsSimilar(
                "Hello there Hello there Hello there",
                0.4,
                IsSimilar.LEVENSHTEIN,
            ),
        )


@should_fail_with(num_assertion=2)
def test_is_similar_levenshtein_3():
    # not passing metrics parameter, default using Levenshtein metric or pass IsSimilar.LEVENSHTEIN
    trace = Trace(trace=[{"role": "user", "content": "Hello there"}])
    with trace.as_context():
        # test case: expected value is shorter than actual value, empty
        assert_that(trace.messages()[0]["content"], IsSimilar("hello", 0.8))
        assert_that(
            trace.messages()[0]["content"],
            IsSimilar("", 0.5, IsSimilar.LEVENSHTEIN),
        )


@should_fail_with(num_assertion=3)
def test_is_similar_levenshtein_4():
    # not passing metrics parameter, default using Levenshtein metric or pass IsSimilar.LEVENSHTEIN
    trace = Trace(trace=[{"role": "user", "content": "Hello there"}])
    with trace.as_context():
        # test case: expected value is shorter than actual value, empty
        assert_that(trace.messages()[0]["content"], IsSimilar("hello", 0.8))
        assert_that(
            trace.messages()[0]["content"],
            IsSimilar("", 0.5, IsSimilar.LEVENSHTEIN),
        )

        assert_that(trace.messages()[0]["content"], IsSimilar("there", 0.5))


@should_fail_with(num_assertion=1)
def test_is_similar_levenshtein_5():
    # not passing metrics parameter, default using Levenshtein metric or pass IsSimilar.LEVENSHTEIN
    trace = Trace(trace=[{"role": "user", "content": "Hello there"}])
    with trace.as_context():
        # test case: expected value is the same length as actual value
        assert_that(
            trace.messages()[0]["content"],
            IsSimilar("hello aaaaa", 0.3, IsSimilar.LEVENSHTEIN),
        )
        assert_that(
            trace.messages()[0]["content"],
            IsSimilar("hello THERe", 0.9, IsSimilar.LEVENSHTEIN),
        )


@should_fail_with(num_assertion=1)
def test_is_similar_levenshtein_6():
    # not passing metrics parameter, default using Levenshtein metric or pass IsSimilar.LEVENSHTEIN
    trace = Trace(trace=[{"role": "user", "content": "Hello there"}])
    with trace.as_context():
        assert_that(trace.messages()[0]["content"], IsSimilar("iiiii THERE", 0.5))


def test_is_similar_embedding_passing():
    # pass IsSimilar.EMBEDDING as parameter
    trace = Trace(trace=[{"role": "user", "content": "Hello there"}])
    with trace.as_context():
        # test case: similar meaning
        assert_that(
            trace.messages()[0]["content"],
            IsSimilar("hi there", 0.8, IsSimilar.EMBEDDING),
        )
        assert_that(
            trace.messages()[0]["content"],
            IsSimilar("how are you", 0.4, IsSimilar.EMBEDDING),
        )
        # test case: unrelated meaning but similar spell
        assert_that(
            trace.messages()[0]["content"],
            IsSimilar("hello where", 0.5, IsSimilar.EMBEDDING),
        )
        assert_that(
            trace.messages()[0]["content"],
            IsSimilar("hello three", 0.5, IsSimilar.EMBEDDING),
        )


@should_fail_with(num_assertion=1)
def test_is_similar_embedding_1():
    # pass IsSimilar.EMBEDDING as parameter
    trace = Trace(trace=[{"role": "user", "content": "Hello there"}])
    with trace.as_context():
        # test case: unrelated meaning and different spell
        assert_that(
            trace.messages()[0]["content"],
            IsSimilar("where are you", 0.5, IsSimilar.EMBEDDING),  # fails
        )


@should_fail_with(num_assertion=1)
def test_is_similar_embedding_2():
    # pass IsSimilar.EMBEDDING as parameter
    trace = Trace(trace=[{"role": "user", "content": "Hello there"}])
    with trace.as_context():
        assert_that(
            trace.messages()[0]["content"],
            IsSimilar("I am fine", 0.5, IsSimilar.EMBEDDING),  # fails
        )
