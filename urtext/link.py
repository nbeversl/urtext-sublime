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
		self._parse_string()
		pprint.pprint(self.__dict__) # debugging

	def _parse_string(self):
		parse_string = self.string
		project = syntax.project_link_c.search(parse_string)
		if project:
			self.is_usable = True
			self.project_name = project.group(2)
			self.project_link = project.group()
			parse_string = parse_string.replace(self.project_link, '')

		urtext_link = None
		http_link_present = False

		http_link = url_match(parse_string)
		if http_link:
			if self.col_pos <= http_link.end():
				http_link_present = True
				link_start = http_link.start()
				link_end = http_link.end()
				http_link = in_project_link = http_link.group().strip()

		for match in syntax.any_link_or_pointer_c.finditer(parse_string):
			if self.col_pos <= match.end():
				if http_link_present and (
					link_end < match.end()) and (
					link_end < match.start()):
					break
				urtext_link = match.group()
				link_start = match.start()
				link_end = match.end()
				in_project_link = match.group()
				break

		if http_link and not urtext_link:
			self.http = True
			self.url = http_link
			self.is_usable = True
			return

		kind = None
		if urtext_link:
			if urtext_link[1] in syntax.link_modifiers.values():
				for kind in syntax.link_modifiers:
					if urtext_link[1] == syntax.link_modifiers[kind]:
						kind = kind.upper()
						break

			if kind == 'FILE':
				self.is_file = True
				path = urtext_link[2:-2].strip()
				if path[0] == '~':
					path = os.path.expanduser(path)
				self.path = path  
				self.is_usable = True
				return True

			if kind == 'ACTION':
				self.is_action = True

			if kind == 'MISSING':
				self.missing = True

			self.is_node = True
			self.node_id = utils.get_id_from_link(in_project_link)
			if match.group(11):
				self.dest_node_position = int(match.group(11)[1:])
			self.is_usable = True

