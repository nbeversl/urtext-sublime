import os
import pprint
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
	import Urtext.urtext.syntax as syntax
	from Urtext.urtext.url import url_match_c
else:
	import urtext.syntax as syntax
	from urtext.url import url_match_c

class UrtextLink:

	def __init__(self, string,  col_pos=0):
		self.matching_string = string
		self.containing_node = None
		self.filename = None
		self.project_name = None
		self.is_http = False
		self.is_node = False
		self.node_id = None
		self.is_pointer = False
		self.is_file = False
		self.is_action = False
		self.is_missing = False
		self.position_in_string = None
		self.dest_node_position = 0
		self.url = None
		self.path = None

	def remaining_string(self):
		return self.string.replace(self.matching_string, '')

	def rewrite(self, include_project=False):
		link_modifier = ''
		if self.is_action:
			link_modifier = syntax.link_modifiers['action']
		elif self.is_file:
			link_modifier = syntax.link_modifiers['file']
		return ''.join([
			project_link(self.project_name) if self.project_name and include_project else '',
			syntax.link_opening_wrapper,
			link_modifier,
			syntax.pointer_closing_wrapper if self.is_pointer else syntax.link_closing_wrapper,
			(':%s' % dest_node_position) if self.dest_node_position else ''
			])

	def replace(self, replacement):
		if self.containing_node:
			node_contents = self.containing_node.contents(stripped=False)
			replacement_contents = ''.join([
				node_contents[:self.start_position],
				replacement,
				node_contents[:self.start_position+len(self.string)]
				])
			self.containing_node.set_content(replacement_contents, preserve_title=False)

def project_link(project_name):
	return ''.join([
		syntax.other_project_link_prefix,
		"%s" % project_name
		])

def get_all_links_from_string(string, include_http=False):
	stripped_contents = string
	replaced_contents = string
	links = []

	if include_http:
		for match in url_match_c.finditer(replaced_contents):
			http_link = match.group(3)
			link = UrtextLink(http_link)			
			link.is_http = True
			link.url = http_link
			link.position_in_string = match.start()
			links.append(link)
			replaced_contents = replaced_contents.replace(http_link,' ', 1)
			stripped_contents = stripped_contents.replace(http_link, '', 1)

	for match in syntax.cross_project_link_with_node_c.finditer(replaced_contents):
		link = UrtextLink(match.group())		
		link.project_name = match.group(2)
		link.node_id = match.group(7)
		link.is_node = True
		if match.group(10):
			link.dest_node_position = match.group(10)[1:]
		link.position_in_string = match.start()
		links.append(link)
		replaced_contents = replaced_contents.replace(match.group(),' ', 1)
		stripped_contents = stripped_contents.replace(match.group(), '', 1)

	for match in syntax.node_link_or_pointer_c.finditer(replaced_contents):
		link = UrtextLink(match.group())

		kind = None
		if match.group(1) in syntax.link_modifiers.values():
			for kind in syntax.link_modifiers:
				if match.group(1) == syntax.link_modifiers[kind]:
					kind = kind.upper()
					break

		if kind == 'FILE':
			link.is_file = True
			path = match.group(5).strip()
			if path[0] == '~':
				path = os.path.expanduser(path)
			link.path = path  

		if kind == 'ACTION':
			link.is_action = True

		if kind == 'MISSING':
			link.missing = True

		if match.group(5):
			link.node_id = match.group(5).strip()
			link.is_node = True
			if match.group(8):
				link.dest_node_position = int(match.group(8)[1:])

		if match.group(8) == syntax.pointer_closing_wrapper:
			link.is_pointer = True	
		link.position_in_string = match.start()
		links.append(link)
		replaced_contents = replaced_contents.replace(match.group(),' ', 1)
		stripped_contents = stripped_contents.replace(match.group(), '', 1)
	
	for match in syntax.project_link_c.finditer(replaced_contents):
		link = UrtextLink(match.group())		
		link.project_name = match.group(2)		
		link.position_in_string = match.start()
		links.append(link)
		replaced_contents = replaced_contents.replace(match.group(),' ', 1)
		stripped_contents = stripped_contents.replace(match.group(), '', 1)

	return links, replaced_contents, stripped_contents