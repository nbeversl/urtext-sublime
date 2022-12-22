import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from .node import UrtextNode
    import Urtext.urtext.syntax as syntax
else:
    from urtext.node import UrtextNode
    import urtext.syntax as syntax

class UrtextSettings():
	""" gets ProjectList settings from a single urtext file"""

	def __init__(self, settings_file):
		self.settings_file = UrtextFile(settings_file)

	def to_dict(self):
		settings = {}
		for entry in self.settings_file.metadata.all_entries:
			settings.setdefault(entry.key, [])
			settings[entry.key].append(entry.value)
		return settings