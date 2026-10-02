"""
This module provides private utility functions for backends.

WARNING: The *pathspec._backends* package is not part of the public API. Its
contents and structure are likely to change.
"""

import re
from collections.abc import (
	Iterable)
from typing import (
	TypeVar,
	Union)  # Replaced by `X | Y` in 3.10.

from pathspec.pattern import (
	Pattern)

TPattern = TypeVar("TPattern", bound=Pattern)


def enumerate_patterns(
	patterns: Iterable[TPattern],
	filter: bool,
	reverse: bool,
) -> list[tuple[int, TPattern]]:
	"""
	Enumerate the patterns.

	*patterns* (:class:`Iterable` of :class:`.Pattern`) contains the patterns.

	*filter* (:class:`bool`) is whether to remove no-op patterns (:data:`True`),
	or keep them (:data:`False`).

	*reverse* (:class:`bool`) is whether to reverse the pattern order
	(:data:`True`), or keep the order (:data:`True`).

	Returns the enumerated patterns (:class:`list` of :class:`tuple`).
	"""
	out_patterns = [
		(__i, __pat)
		for __i, __pat in enumerate(patterns)
		if not filter or __pat.include is not None
	]
	if reverse:
		out_patterns.reverse()

	return out_patterns


def translate_end_anchor(regex: Union[str, bytes]) -> Union[str, bytes]:
	"""
	Translate Python's strict end anchor for the native regex backends.

	*regex* (:class:`str` or :class:`bytes`) is the Python regular expression.

	RE2 does not support ``\\Z``, and Hyperscan permits a final newline before
	``\\Z``. Both use ``\\z`` for the strict end-of-string assertion. Escaped
	backslashes must remain unchanged, including a literal ``\\Z`` in a name.

	Returns the translated regular expression with the same type as *regex*.
	"""
	if isinstance(regex, bytes):
		return re.sub(rb'\\[\\Z]', lambda m: rb'\z' if m[0] == rb'\Z' else m[0], regex)
	return re.sub(r'\\[\\Z]', lambda m: r'\z' if m[0] == r'\Z' else m[0], regex)
