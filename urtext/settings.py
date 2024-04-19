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