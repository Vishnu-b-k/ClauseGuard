"""
Interface every ADK agent must satisfy (FR-104).

Mirrors the two-agent split in the architecture: an analysis agent and a
synthesis agent, each with a build_prompt() (real, CRISPE-formatted, usable
today) and a call method that currently returns a mocked structured result
instead of calling the real Google ADK runtime.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ADKAgent(ABC):
    @abstractmethod
    def build_prompt(self, *args, **kwargs) -> str:
        """Returns the exact CRISPE-formatted prompt that would be sent to
        the LLM. Real and usable now -- only the call that sends it is
        mocked."""
        raise NotImplementedError
