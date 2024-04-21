import datetime
from urtext.utils import force_list, get_id_from_link
import urtext.syntax as syntax
from urtext.timestamp import UrtextTimestamp

class UrtextDynamicDefinition:

	def __init__(self, param_string, project, position):

		self.position = position
		self.contents = None
		self.target_ids = []
		self.targets = []
		self.included_nodes = []
		self.excluded_nodes = []
		self.spaces = 0
		self.project = project
		self.preformat = False
		self.show = None
		self.param_string = param_string
		self.system_contents = []
		self.init_self(param_string)	
		self.source_node = None # set by node once compiled
		if not self.show:
			self.show = '$_link\n'

	def init_self(self, contents):

		self.operations = []
		self.flags = []
		self.contents = contents

		for match in syntax.function_c.finditer(contents):
			
			func, argument_string = match.group(1), match.group().strip(match.group(1)).replace(')(','')
			argument_string = match.group(2)
			if func and func in self.project.directives:
				op = self.project.directives[func](self.project)
				op.argument_string = argument_string
				op.dynamic_definition= self
				op.parse_argument_string(argument_string)	
				self.operations.append(op)
				continue

			elif func in ['TARGET', '>']:
				output_target = syntax.virtual_target_match_c.match(argument_string)
				if output_target:
					self.targets.append(output_target.group())
				else:
					target_id = get_id_from_link(argument_string)
					if target_id:
						self.target_ids.append(target_id)
					else:
						self.targets.append(argument_string)
				continue

			else:
				self.system_contents.append('directive "%s" not found' % func)

	def preserve_title_if_present(self, target):
		if target == '@self' and self.source_node.id in self.project.nodes:
			return ' ' + self.project.nodes[self.source_node.id].title + syntax.title_marker +'\n'
		node_id = get_id_from_link(target)
		if node_id in self.target_ids and node_id in self.project.nodes and self.project.nodes[node_id].first_line_title:
			return ' ' + self.project.nodes[node_id].title + syntax.title_marker +'\n'
		return ''

	def process_output(self):
		self.project._run_hook('on_dynamic_def_process_started', self)
		accumulated_text = ''

		for operation in self.operations:
			nodes_included = [self.project.nodes[nid] for nid in self.included_nodes if (
					nid in self.project.nodes) and nid not in self.excluded_nodes]

			# if not self.nodes_sorted:
			# this should not happen on every iteration.
			# SORT() will now modify the list directly without text output.

			# sorted_nodes = sorted(
			# 	nodes_included,
			# 	key=lambda node: node.title)
			# sorted_nodes = sorted(
			# 	sorted_nodes,
			# 	key=lambda node: node.metadata.get_first_value(
			# 			'_oldest_timestamp').datetime if (
			# 				node.metadata.get_first_value('_oldest_timestamp')) else (
			# 			datetime.datetime(
			# 				1,1,1,
			# 				tzinfo=datetime.timezone.utc)),
			# 	reverse=True)
			current_text = accumulated_text
			try:
				transformed_text = operation.dynamic_output(current_text)
			except Exception as e:
				accumulated_text += ''.join([
					'error in ',
					str(operation.name),
					': ',
					str(e),
					'\n'
					])
				continue
			if transformed_text == False: # not None !
				return current_text
			if transformed_text == None:
				accumulated_text = current_text
				continue
			accumulated_text = transformed_text
		self.flags = []
		self.project._run_hook('on_dynamic_def_process_ended', self)
		if self.system_contents:
			accumulated_text += '\n'.join(self.system_contents)
		return accumulated_text

	def have_flags(self, flag):
		if flag in self.flags:
			return True
		return False

	def get_definition_text(self):
		return '\n' + ''.join([
			syntax.dynamic_def_opening_wrapper,
			'\n'.join([line.strip() for line in self.contents.split('\n')]),
			syntax.dynamic_def_closing_wrapper
			])

	def process(self, flags=[]):
		self.flags = flags
		for target_id in self.target_ids:
			if self.source_node.id not in self.project.nodes:
				continue
			if target_id not in self.project.nodes:
				filename = self.project.nodes[self.source_node.id].filename
				self.project._log_item(filename, ''.join([
							'Dynamic node definition in ',
							self.source_node.link(),
							'\n',
							'points to nonexistent node ',
							syntax.missing_link_opening_wrapper,
							target_id,
							syntax.link_closing_wrapper]))

		output = self.process_output()
		if self.spaces:
			output = self.indent(output, spaces=self.spaces)
		return output

	def post_process(self, target, output):
		output = self.preserve_title_if_present(target) + output
		if target == '@self':
			output += self.get_definition_text()
		return output

	def indent(contents, spaces=4):
		content_lines = contents.split('\n')
		content_lines[0] = content_lines[0].strip()
		for index, line in enumerate(content_lines):
			if line.strip() != '':
				content_lines[index] = '\t' * spaces + line
		return '\n'+'\n'.join(content_lines)
