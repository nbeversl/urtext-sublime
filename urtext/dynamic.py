# -*- coding: utf-8 -*-
"""
This file is part of Urtext.

Urtext is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Urtext is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Urtext.  If not, see <https://www.gnu.org/licenses/>.

"""
import os

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
	from .directive import UrtextDirective
	from .utils import force_list, get_id_from_link
	import Urtext.urtext.syntax as syntax
else:
	from urtext.directive import UrtextDirective
	from urtext.utils import force_list, get_id_from_link
	import urtext.syntax as syntax

phases = [
	000, # Pre-checks, such as WHEN()
	100, # Queries, building and sorting list of nodes included/excluded
	200, # Expects list of node objects. Sorting, limiting, transforming the node list.
	300, # Build text. Expects list of node objects. Convert selected nodes to text output
	400, # Adding header/footer, preserving other elements as needed
	500, # Transform built text further (exports, etc.)
	600, # currently unused
	700, # custom operations
	800, # post-process (formatting per target, preserving title/definition, etc.)
]

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
		self.returns_text = True
		self.param_string = param_string
		self.init_self(param_string)	
		self.source_id = None # set by node once compiled
		if not self.show: self.show = '$_link\n'

	def init_self(self, contents):

		self.operations = []
		self.flags = []
		self.contents = contents

		for match in syntax.function_c.finditer(contents):
			
			func, argument_string = match.group(1), match.group().strip(match.group(1)).strip(')(')
			argument_string = match.group(2)
			if func and func in self.project.directives:
				op = self.project.directives[func](self.project)
				op.argument_string = argument_string
				op.set_dynamic_definition(self)
				op.parse_argument_string(argument_string)	
				self.operations.append(op)

			if func in ['TARGET', '>']:
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

			if func == "SHOW":
				self.show = argument_string
		
		self.phases = list(set([op.phase for op in self.operations]))
		
		#TODO rewrite -- 
		#is_custom_output = max(self.phases) >= 700 if self.phases else False
		#if not is_custom_output and not has_text_output(self.operations):
		if not has_text_output(self.operations):
			# add simple list output if none supplied
			op = self.project.directives['TREE'](self.project)
			op.parse_argument_string('1')	
			op.set_dynamic_definition(self)
			self.operations.append(op)
			self.phases.append(300)

		if all(i < 300 or i > 600 for i in self.phases):
			self.returns_text = False

	def preserve_title_if_present(self, target):
		if target == '@self' and self.source_id in self.project.nodes:
			return ' ' + self.project.nodes[self.source_id].title + syntax.title_marker +'\n'
		node_id = get_id_from_link(target)
		if node_id in self.target_ids and node_id in self.project.nodes and self.project.nodes[node_id].first_line_title:
			return ' ' + self.project.nodes[node_id].title + syntax.title_marker +'\n'
		return ''

	def process_output(self, max_phase=700):

		outcome = []
		phases_to_process = [p for p in phases if p <= max_phase]
		all_operations = sorted(
			list(self.operations), 
			key = lambda op: op.phase)

		for p in phases_to_process:	
			if p == 200: 
				# convert node_id list to node objects for remaining processing
				self.included_nodes = outcome
				outcome = [
					self.project.nodes[nid] for nid in outcome if (
						nid in self.project.nodes)
					]

			next_phase = p + 100
			ops_this_phase = [op for op in all_operations if p <= op.phase < next_phase]
			
			if len(ops_this_phase) > 1 and 300 <= p < 400:
				accumulated_text = ''
				for operation in ops_this_phase:
					next_outcome = operation._dynamic_output(outcome)
					if next_outcome != False:
						accumulated_text += next_outcome
				outcome = accumulated_text
			else:
				for operation in ops_this_phase:
					new_outcome = operation._dynamic_output(outcome)					
					if new_outcome == False:
						return False
					outcome = new_outcome

		self.flags = []
		return outcome		

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
			if self.source_id not in self.project.nodes:
				continue
			if target_id not in self.project.nodes:
				filename = self.project.nodes[self.source_id].filename
				self.project._log_item(filename, ''.join([
							'Dynamic node definition in node ',
							syntax.link_opening_wrapper,
							self.source_id,
							syntax.link_closing_wrapper,
							' pointing to nonexistent node ',
							'|? ',
							target_id,
							syntax.link_closing_wrapper]))

		output = self.process_output()
		if output == False: return
		if not self.returns_text: return
		if self.spaces: output = indent(output, spaces=self.spaces)
		return output

	def post_process(self, target, output):
		output = self.preserve_title_if_present(target) + output
		if target == '@self':
			output += self.get_definition_text()
		post_process_ops = [op for op in list(self.operations) if op.phase >= 800]
		for op in post_process_ops:
			output = op._dynamic_output(output)
		return output


def has_text_output(operations):
	for op in operations:
		if 300 <= op.phase < 400:
			return True
	return False

def indent(contents, spaces=4):
	content_lines = contents.split('\n')
	content_lines[0] = content_lines[0].strip()
	for index, line in enumerate(content_lines):
		if line.strip() != '':
			content_lines[index] = '\t' * spaces + line
	return '\n'+'\n'.join(content_lines)