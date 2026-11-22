"""Errors the job status can show to the author."""


class RenderError(RuntimeError):
    """A render failed. ``str(self)`` is the message stored on the job."""
