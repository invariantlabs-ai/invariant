import re
from html.parser import HTMLParser

from pydantic import BaseModel, Field

from invariant.analyzer.runtime.functions import cached
from invariant.analyzer.runtime.runtime_errors import InvariantAttributeError
from invariant.analyzer.stdlib.invariant.nodes import ToolCall


class HiddenHTMLData(BaseModel):
    alt_texts: list[str] = Field(
        default_factory=list,
        description="List of alt texts extracted from HTML code.",
    )
    links: list[str] = Field(
        default_factory=list,
        description="List of links extracted from HTML code.",
    )

    def __invariant_attribute__(self, name: str):
        if name in ["alt_texts", "links"]:
            return getattr(self, name)
        raise InvariantAttributeError(
            f"Attribute {name} not found in HiddenHTMLData. Available attributes are: alt_texts, links"
        )


class HiddenDataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.alt_texts = []
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            for attr in attrs:
                if attr[0] == "alt":
                    self.alt_texts.append(attr[1])
        if tag == "a":
            for attr in attrs:
                if attr[0] == "href":
                    self.links.add(attr[1])

    def handle_data(self, data):
        pass

    def parse(self, data: str) -> None:
        self.feed(data)
        self.links = self.links.union(HiddenDataParser.get_links_regex(data))

    @staticmethod
    def get_links_regex(data: str) -> list[str]:
        """
        Extracts links from a string of HTML code.

        Returns:
            - list[str]: A list of links.
        """

        # link including path etc.
        pattern = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+" + r"(?:/[^ \n\"]+)*"
        return list(set(re.findall(pattern, data)))


@cached
def html_code(data: str | list | dict, **config: dict) -> HiddenHTMLData:
    """
    Parse the HTML code and extract the alt texts and links.

    Returns:
        - HiddenHTMLData: A dataclass containing the alt texts and links.
    """

    chat = (
        data if isinstance(data, list) else ([{"content": data}] if isinstance(data, str) else [data])
    )

    res = HiddenHTMLData(alt_texts=[], links=[])
    for message in chat:
        if message is None:
            continue
        if type(message) is ToolCall:
            content = str(message)
        else:
            if message.content is None:
                continue
            content = message.content
        parser = HiddenDataParser()
        parser.parse(content)

        res.alt_texts.extend(parser.alt_texts)
        res.links.extend(list(parser.links))

    return res


def links(data: str | list | dict, **config: dict) -> list[str]:
    """
    Extracts links from a string of HTML code or text.

    Returns:
        - list[str]: A list of links.
    """

    chat = (
        data if isinstance(data, list) else ([{"content": data}] if isinstance(data, str) else [data])
    )

    res = []
    for message in chat:
        if message is None:
            continue
        if message.content is None:
            continue
        res.extend(HiddenDataParser.get_links_regex(message.content))

    return res
