from functools import lru_cache

from dynamicprompts.enums import SamplingMethod
from dynamicprompts.sampling_context import SamplingContext

from .sampler import DPAbstractSamplerNode


class DPRandomGenerator(DPAbstractSamplerNode):
    @classmethod
    def INPUT_TYPES(cls):
        input_types = super().INPUT_TYPES()
        for input_name in ("seed", "autorefresh"):
            input_types["required"][input_name][1]["advanced"] = True
        return input_types

    @property
    @lru_cache(maxsize=1)
    def context(self) -> SamplingContext:
        return SamplingContext(
            wildcard_manager=self._wildcard_manager,
            default_sampling_method=SamplingMethod.RANDOM,
        )
