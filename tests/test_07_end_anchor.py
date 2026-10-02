"""
Test that gitignore patterns require the actual end of a filename.
"""

import re
import unittest

from pathspec import (
	GitIgnoreSpec,
	PathSpec,
	RegexPattern)
from pathspec._backends._utils import (
	translate_end_anchor)
from pathspec.patterns.gitignore.basic import (
	GitIgnoreBasicPattern)
from pathspec.patterns.gitignore.spec import (
	GitIgnoreSpecPattern)

from .util import (
	require_backend)


class EndAnchorTest(unittest.TestCase):
	"""
	Test literal and wildcard endings with a trailing newline in the filename.
	"""

	def test_pattern_endings(self):
		"""
		A final newline is part of the name, not an end-of-string boundary.
		"""
		for pattern_type in (GitIgnoreBasicPattern, GitIgnoreSpecPattern):
			for pattern, path in (
				('target', 'target'),
				('*.txt', 'file.txt'),
				('file?', 'file1'),
				('[ab]', 'a'),
				('root/target', 'root/target'),
			):
				for as_bytes in (False, True):
					with self.subTest(pattern_type=pattern_type, pattern=pattern, as_bytes=as_bytes):
						compiled = pattern_type(pattern.encode()) if as_bytes else pattern_type(pattern)
						for suffix, expected in (('', True), ('\n', False), ('\n\n', False), ('/child', True)):
							file = path + suffix
							match = compiled.match_file(file.encode()) if as_bytes else compiled.match_file(file)
							self.assertEqual(
								match is not None,
								expected,
								repr(file),
							)

	def test_backends(self):
		"""
		Every backend must preserve filename endings and negation decisions.
		"""
		for backend in ('simple', 're2', 'hyperscan'):
			with self.subTest(backend=backend):
				require_backend(backend)
				for spec_type in (PathSpec, GitIgnoreSpec):
					for patterns, file, expected in (
						(['*.txt'], 'file.txt', True),
						(['*.txt'], 'file.txt\n', False),
						(['*.txt'], 'dir\n/file.txt', True),
						(['*', '!keep.txt'], 'keep.txt', False),
						(['*', '!keep.txt'], 'keep.txt\n', True),
						(['root/*'], 'root/child/\n', False),
						(['root/*'], 'root/child\n', True),
						([r'file\\Z'], 'file\\Z', True),
						([r'file\\Z'], 'file\\z', False),
					):
						with self.subTest(spec_type=spec_type, patterns=patterns, file=file):
							if spec_type is PathSpec:
								spec = PathSpec.from_lines('gitignore', patterns, backend=backend)
							else:
								spec = GitIgnoreSpec.from_lines(patterns, backend=backend)
							# GitIgnoreSpec correctly includes descendants of an ignored
							# directory, while the basic pattern matches one level here.
							if patterns == ['root/*'] and file == 'root/child/\n' and spec_type is GitIgnoreSpec:
								expected = True
							self.assertEqual(spec.match_file(file, separators=('/',)), expected)

	def test_native_end_anchor_translation(self):
		"""
		Translate anchors without changing escaped backslashes, for both types.
		"""
		for count in range(6):
			regex = 'file' + '\\' * count + 'Z'
			expected = regex[:-1] + 'z' if count % 2 else regex
			for as_bytes in (False, True):
				with self.subTest(regex=regex, as_bytes=as_bytes):
					actual = translate_end_anchor(regex.encode() if as_bytes else regex)
					self.assertEqual(actual, expected.encode() if as_bytes else expected)

	def test_compiled_regex_endings(self):
		"""
		Native backends preserve a precompiled Python pattern's strict ending.
		"""
		for backend in ('simple', 're2', 'hyperscan'):
			with self.subTest(backend=backend):
				require_backend(backend)
				for count in range(3):
					file = 'file' + '\\' * count
					regex = re.compile(re.escape(file) + r'\Z')
					for spec_type in (PathSpec, GitIgnoreSpec):
						with self.subTest(spec_type=spec_type, file=file):
							if spec_type is PathSpec:
								spec = PathSpec([RegexPattern(regex, include=True)], backend=backend)
							else:
								spec = GitIgnoreSpec(
									[GitIgnoreSpecPattern(regex, include=True)], backend=backend,
								)
							self.assertTrue(spec.match_file(file, separators=('/',)))
							self.assertFalse(spec.match_file(file + '\n', separators=('/',)))
