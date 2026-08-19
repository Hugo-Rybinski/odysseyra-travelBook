"""Validate a travel JSON and report problems with line numbers.

Split across submodules: :mod:`.jsonpos` (position-tracking parser),
:mod:`.findings` (Finding + rendering), :mod:`.specs` (field specs and value
validators) and :mod:`.validator` (the validation pass)."""

from .findings import Finding, format_findings
from .jsonpos import load_with_lines
from .validator import FRAGMENT_KINDS, validate_fragment, validate_text

__all__ = ["FRAGMENT_KINDS", "Finding", "format_findings", "load_with_lines",
           "validate_fragment", "validate_text"]
