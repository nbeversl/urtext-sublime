import os
import pprint
from .url import url_match
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
	import Urtext.urtext.syntax as syntax
	import Urtext.urtext.utils as utils
else:
	import urtext.syntax as syntax
	import urtext.utils as utils

class UrtextLink:

	def __init__(self, string, filename, col_pos=0):
		self.string = string.strip()
		self.filename = filename
		self.col_pos = col_pos
		self.project_name = None
		self.project_link = None
		self.is_http = False
		self.is_node = False
		self.node_id = None
		self.is_file = False
		self.is_action = False
		self.is_missing = False
		self.dest_node_position = 0
		self.url = None
		self.path = None
		self.is_usable = False
		self.matching_strings = []
		self._parse_string()

	def _parse_string(self):
		parse_string = self.string
		http_link = url_match(parse_string)
		urtext_link = syntax.any_link_or_pointer_c.search(parse_string)
		if http_link:
			if not urtext_link or (urtext_link and self.col_pos <= http_link.end()):
				http_link = http_link.group().strip()
				self.is_http = True
				self.url = http_link
				self.is_usable = True
				self.matching_strings.append(http_link)
				return

		if urtext_link:
			print(urtext_link.groups())
			self.matching_strings.append(urtext_link.group())
			if urtext_link.group(3):
				self.project_name = urtext_link.group(3)
				self.project_link = urtext_link.group(1)
				self.is_usable = True
				self.matching_strings.append(urtext_link.group())	

			kind = None
			if urtext_link.group(5) in syntax.link_modifiers.values():
				for kind in syntax.link_modifiers:
					if urtext_link.group(5) == syntax.link_modifiers[kind]:
						kind = kind.upper()
						break

			if kind == 'FILE':
				self.is_file = True
				path = urtext_link.group(9).strip()
				if path[0] == '~':
					path = os.path.expanduser(path)
				self.path = path  
				self.is_usable = True
				self.matching_strings.append(urtext_link.group())
				return True

			if kind == 'ACTION':
				self.is_action = True

			if kind == 'MISSING':
				self.missing = True

			
			if urtext_link.group(9):
				self.node_id = urtext_link.group(9).strip()
				self.is_node = True
				if urtext_link.group(11):
					self.dest_node_position = int(urtext_link.group(11)[1:])
				self.matching_strings.append(urtext_link.group())
				self.is_usable = True


	def remaining_string(self):
		string = self.string
		for substring in self.matching_strings:
			string = string.replace(substring, '')
		return string

