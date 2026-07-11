import logging
from typing import TYPE_CHECKING

from .sampler import DPAbstractSamplerNode

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dynamicprompts.sampling_context import SamplingContext


class DPMagicPrompt(DPAbstractSamplerNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._random_generator = None
        self._prompt_generator = None

    def _ensure_prompt_generator(self) -> None:
        """Load MagicPrompt only when this node is actually executed."""
        if self._prompt_generator is not None:
            return

        from dynamicprompts.generators import RandomPromptGenerator
        from dynamicprompts.generators.magicprompt import MagicPromptGenerator

        self._random_generator = RandomPromptGenerator(
            wildcard_manager=self._wildcard_manager,
        )
        self._prompt_generator = MagicPromptGenerator(
            prompt_generator=self._random_generator,
        )

    def get_prompt(self, text: str, seed: int, autorefresh: str) -> tuple[str]:
        """
        Main entrypoint for this node.
        Using the sampling context, generate a new prompt.
        """

        if text.strip() == "":
            return ("",)

        self._ensure_prompt_generator()

        if seed > 0:
            self.context.rand.seed(seed)

        try:
            prompt = self._prompt_generator.generate(text, 1)[0]

            return (str(prompt),)
        except Exception as e:
            logger.exception(e)
            return ("",)

    @property
    def context(self) -> "SamplingContext":
        self._ensure_prompt_generator()
        assert self._random_generator is not None
        return self._random_generator._context
