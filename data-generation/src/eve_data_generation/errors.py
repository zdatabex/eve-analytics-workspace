"""Errors raised by configuration, generation, and loading."""


class ConfigError(ValueError):
    """The generation configuration contradicts itself or the contracts."""


class GenerationError(RuntimeError):
    """A dataset cannot be generated for the supplied configuration."""


class ValidationError(GenerationError):
    """A generated row breaks a source contract rule."""
