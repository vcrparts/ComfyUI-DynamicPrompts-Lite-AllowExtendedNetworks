from __future__ import annotations

import logging
import re
from abc import ABC, abstractproperty
from collections.abc import Iterable

from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.wildcards import WildcardManager

from .wildcard_refresh import get_wildcards_folder, wildcard_refresh_state

logger = logging.getLogger(__name__)


def escape_angle_tags(text: str) -> str:
    """Escape unescaped < and > characters so dynamicprompts ignores extra-network tags."""
    if not text:
        return text
    text = re.sub(r"(?<!\\)<", r"\\<", text)
    text = re.sub(r"(?<!\\)>", r"\\>", text)
    return text


def unescape_angle_tags(text: str) -> str:
    """Restore \\< and \\> back to < and > for downstream LoRA and ratio nodes."""
    if not text:
        return text
    return text.replace(r"\<", "<").replace(r"\>", ">")


class PassthroughWildcardManager(WildcardManager):
    """WildcardManager subclass that optionally escapes < and > inside wildcard files."""

    def __init__(self, path, allow_extra_networks: bool = True):
        super().__init__(path=path)
        self.allow_extra_networks = allow_extra_networks

    def get_values(self, wildcard: str):
        values = super().get_values(wildcard)
        if not self.allow_extra_networks:
            return values
        return [escape_angle_tags(v) if isinstance(v, str) else v for v in values]

    def get_all_values(self, wildcard: str):
        values = super().get_all_values(wildcard)
        if not self.allow_extra_networks:
            return values
        return [escape_angle_tags(v) if isinstance(v, str) else v for v in values]


class DPAbstractSamplerNode(ABC):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "dynamicPrompts": False}),
                "seed": ("INT", {"default": 0, "display": "number"}),
                "autorefresh": (["Yes", "No"], {"default": "No"}),
                "allow_extra_networks": ("BOOLEAN", {"default": True}),
            },
        }

    @classmethod
    def IS_CHANGED(cls, seed, **kwargs):
        return seed

    RETURN_TYPES = ("STRING",)
    FUNCTION = "get_prompt"
    CATEGORY = "Dynamic Prompts"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        wildcards_folder = self._find_wildcards_folder()
        self._wildcard_manager = PassthroughWildcardManager(
            path=wildcards_folder,
            allow_extra_networks=True,
        )
        self._current_prompt = None
        self._prompts = None
        self._wildcards_revision = wildcard_refresh_state.revision

    def _find_wildcards_folder(self):
        return get_wildcards_folder()

    def _refresh_wildcards_if_needed(self) -> None:
        revision = wildcard_refresh_state.revision
        if revision == self._wildcards_revision:
            return

        self._wildcard_manager.clear_cache()
        self._current_prompt = None
        self._prompts = None
        self._wildcards_revision = revision
        logger.info("Wildcard cache refreshed for %s", type(self).__name__)

    def _get_next_prompt(self, prompts: Iterable[str], current_prompt: str) -> str:
        """
        Get the next prompt from the prompts generator.
        """
        try:
            return next(prompts)
        except (StopIteration, RuntimeError):
            self._prompts = self.context.sample_prompts(current_prompt)
            try:
                return next(self._prompts)
            except StopIteration:
                logger.exception("No more prompts to generate!")
                return ""

    def has_prompt_changed(self, text: str) -> bool:
        """
        Check if the prompt has changed.
        """
        return self._current_prompt != text

    def get_prompt(
        self,
        text: str,
        seed: int,
        autorefresh: str,
        allow_extra_networks: bool = True,
    ) -> tuple[str]:
        """
        Main entrypoint for this node.
        Using the sampling context, generate a new prompt.
        """

        if seed > 0:
            self.context.rand.seed(seed)

        if text.strip() == "":
            return ("",)

        self._refresh_wildcards_if_needed()

        # Sync toggle state with WildcardManager and reset generator if toggled
        if self._wildcard_manager.allow_extra_networks != allow_extra_networks:
            self._wildcard_manager.allow_extra_networks = allow_extra_networks
            self._current_prompt = None
            self._prompts = None

        processed_text = escape_angle_tags(text) if allow_extra_networks else text

        if self.has_prompt_changed(processed_text):
            self._current_prompt = processed_text
            self._prompts = self.context.sample_prompts(self._current_prompt)

        if self._prompts is None:
            logger.exception("Something went wrong. Prompts is None!")
            return ("",)

        if self._current_prompt is None:
            logger.exception("Something went wrong. Current prompt is None!")
            return ("",)

        new_prompt = str(self._get_next_prompt(self._prompts, self._current_prompt))
        if allow_extra_networks:
            new_prompt = unescape_angle_tags(new_prompt)

        print(f"New prompt: {new_prompt}")

        return (new_prompt,)

    @abstractproperty
    def context(self) -> SamplingContext:
        ...
