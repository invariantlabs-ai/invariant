import os
from typing import Union

import regex
from openai import AsyncOpenAI

from invariant.analyzer.runtime.functions import cached
from invariant.analyzer.runtime.nodes import text


@cached
async def fuzzy_contains(search_text: str, query: str, query_similarity_threshold: float = 0.8, use_semantic: bool = True, **config) -> bool:
    assert 0 <= query_similarity_threshold <= 1, "query_similarity_threshold must be between 0 and 1"
    # Import Interpreter here to avoid circular import
    from invariant.analyzer.runtime.evaluation import Interpreter

    # Calculate error tolerance based on query length, not search_text length
    error_tolerance = int(len(query) * (1 - query_similarity_threshold))
    pattern = regex.compile(f'(?:{query}){{e<={error_tolerance}}}')
    match = None

    match = pattern.search(search_text)
    if match:
        # Mark the matched text
        Interpreter.current().mark(search_text, match.span()[0], match.span()[1])
    elif use_semantic:
        # Only try semantic matching if regex matching failed and it's enabled
        try:
            match = await _semantic_contains(search_text, query)
            if match:
                Interpreter.current().mark(search_text, 0, len(search_text))
        except Exception as e:
            pass

    return match is not None


@cached
async def _semantic_contains(text: str, query: str, model: str = "gpt-4.1-nano") -> bool:
    prompt = f"""
Analyze if the text contains or relates to "{query}". Consider:
1. Direct mentions or synonyms of "{query}"
2. Conceptual relationships or implementations of "{query}"
3. Patterns that represent "{query}" even without explicitly naming it

The text to analyze: "{text}"

Answer with only one word: 'yes' or 'no'.
"""

    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY")
    )

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that answers with only yes or no."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=10
    )

    answer = response.choices[0].message.content.strip().lower()
    print(f"Semantic match: {answer}")
    return "yes" in answer
