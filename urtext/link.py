import urtext.syntax as syntax

class UrtextLink:

	def __init__(self, matching_string):
		self.matching_string = matching_string
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

	def rewrite(self, include_project=False):
		link_modifier = ''
		if self.is_action:
			link_modifier = syntax.link_modifiers['action']
		elif self.is_file:
			link_modifier = syntax.link_modifiers['file']
		return ''.join([
			syntax.other_project_link_prefix,
        	'"%s"' % self.project_name if self.project_name and include_project else '',
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
				node_contents[self.start_position+len(self.matching_string):]
				])
			self.project._set_node_contents(
				containing_node.id,
				replacement_contents,
				preserve_title=False)

	def end_position(self):
		return self.position_in_string + len(self.matching_string)
