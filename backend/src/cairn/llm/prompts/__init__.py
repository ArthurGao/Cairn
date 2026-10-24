"""Versioned prompt templates; the version is recorded with every call (design §16)."""

from importlib.resources import files

_VERSION_PREFIX = "<!-- version: "


def load_prompt(name: str) -> tuple[str, str]:
    """(version, text) of `prompts/<name>.md`; the first line is `<!-- version: N -->`."""
    raw = files(__package__).joinpath(f"{name}.md").read_text(encoding="utf-8")
    first, _, text = raw.partition("\n")
    if not first.startswith(_VERSION_PREFIX):
        raise ValueError(f"prompt {name} has no version line")
    return first.removeprefix(_VERSION_PREFIX).removesuffix(" -->").strip(), text.lstrip("\n")
