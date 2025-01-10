"""AI Agent to Find Capitals using Swarm and Printing Messages."""

from swarm import Agent

COUNTRY_TO_CAPITAL_MAPPING = {
    "France": "Paris",
    "Germany": "Berlin",
    "India": "New Delhi",
    "Japan": "Tokyo",
    "USA": "Washington, D.C.",
}


def get_capital(country_name: str) -> str:
    """Get the capital of a country."""
    return COUNTRY_TO_CAPITAL_MAPPING.get(country_name, "not_found")


def create_agent() -> Agent:
    """Create an agent that finds the capital of a country."""
    return Agent(
        name="Capital Finder Agent",
        instructions="""
        Use the get_capital tool call to get the capital of a country.
        If the user input doesn't contain a country name, fail the request with a pretty message.
        If the get_capital tool call returns 'not_found' then fail the request with a pretty message.
        Do not return the capital if the get_capital tool call returns 'not_found'.
        """,
        functions=[get_capital],
    )
