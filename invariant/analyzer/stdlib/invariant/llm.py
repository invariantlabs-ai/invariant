from invariant.analyzer.runtime.functions import cached
from invariant.analyzer.runtime.utils.base import get_openai_client

SYSTEM_PROMPT = """You are a helpful assistant."""
CONFIRMATION_SYSTEM_PROMPT = """You are a highly precise binary classification system that confirms if a given property holds for a given input."""

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

CONFIRMATION_PROMPT = """\
Below is a description of a property that you should confirm as true or false.

Description and Data:
{property_description}

Please respond with a single word, "YES" or "NO". Do not response with any other text.
"""

async def llm_confirm(
    property_description: str,
    system_prompt: str = CONFIRMATION_SYSTEM_PROMPT,
    model: str = "openai/gpt-4o",
    temperature: float = 0.2,
    max_tokens: int = 500,
) -> bool:
    """Predicate used to run an LLM for YES/NO confirmation.

    The property description can be a high-level description of the property you 
    want to confirm (e.g. "Is this string about the topic of AI safety?: {msg.content}").

    It will automatically be embedded into a prompt template that ensures the LLM returns 
    a boolean response, no need for explicit prompting for that.

    Available parameters in the config:
        - property_description: description of the property to confirm
        - system_prompt: system prompt for the LLM
        - model: llm used. must be in form {provider}/{model}. For now only supported openai.
        - temperature: float [0, 1]
        - max_token: max n of generated tokens. 
    """
    result = await llm(
        CONFIRMATION_PROMPT.format(property_description=property_description),
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens
    )
    if result.lower().strip() == "yes":
        return True
    elif result.lower().strip() == "no":
        return False
    else:
        return False
