from invariant.analyzer.runtime.functions import cached
from invariant.analyzer.runtime.utils.base import get_openai_client

SYSTEM_PROMPT = """You are a helpful assistant."""

@cached
async def llm(
    prompt: str,
    system_prompt: str = SYSTEM_PROMPT,
    model: str = "openai/gpt-4o",
    temperature: float = 0.2,
    max_tokens: int = 500,
) -> str:
    """Predicate used to run an LLM within guardrails.

    Available parameters in the config:
        - prompt: prompt for the LLM
        - system_prompt: system prompt for the LLM
        - model: llm used. must be in form {provider}/{model}. For now only supported openai.
        - temperature: float [0, 1]
        - max_token: max n of generated tokens. 
    """
    model_provider = model.split("/")[0]
    if model_provider != "openai":
        raise NotImplementedError("Only OpenAI models are supported for now.")
    
    model_name = model.split("/")[1]
    response = await get_openai_client().chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content