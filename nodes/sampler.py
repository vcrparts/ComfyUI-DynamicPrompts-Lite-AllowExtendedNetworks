from __future__ import annotations

import logging
from abc import ABC, abstractproperty
from collections.abc import Iterable

from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.wildcards import WildcardManager

from .wildcard_refresh import get_wildcards_folder, wildcard_refresh_state

logger = logging.getLogger(__name__)


class DPAbstractSamplerNode(ABC):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "dynamicPrompts": False}),
                "seed": ("INT", {"default": 0, "display": "number"}),
                "autorefresh": (["Yes", "No"], {"default": "No"}),
            },
        }

    @classmethod
    def IS_CHANGED(cls, text: str, seed: int, autorefresh: str):
        # Force re-evaluation of the node
        return float("NaN")

    RETURN_TYPES = ("STRING",)
    FUNCTION = "get_prompt"
    CATEGORY = "Dynamic Prompts"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        wildcards_folder = self._find_wildcards_folder()
        self._wildcard_manager = WildcardManager(path=wildcards_folder)
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

    def get_prompt(self, text: str, seed: int, autorefresh: str) -> tuple[str]:
        """
        Main entrypoint for this node.
        Using the sampling context, generate a new prompt.
        """

        if seed > 0:
            self.context.rand.seed(seed)

        if text.strip() == "":
            return ("",)

        self._refresh_wildcards_if_needed()

        if self.has_prompt_changed(text):
            self._current_prompt = text
            self._prompts = self.context.sample_prompts(self._current_prompt)

        if self._prompts is None:
            logger.exception("Something went wrong. Prompts is None!")
            return ("",)

        if self._current_prompt is None:
            logger.exception("Something went wrong. Current prompt is None!")
            return ("",)

        new_prompt = self._get_next_prompt(self._prompts, self._current_prompt)
        print(f"New prompt: {new_prompt}")

        return (str(new_prompt),)

    @abstractproperty
    def context(self) -> SamplingContext:
        ...
