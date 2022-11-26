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
	from .utils import force_list
	from .directives.list import NodeList
	import Urtext.urtext.syntax as syntax
else:
	from urtext.directive import UrtextDirective
	from urtext.utils import force_list
	from urtext.directives.list import NodeList
	import urtext.syntax as syntax

phases = [
	100, # Queries, building and sorting list of nodes included/excluded
	200, # Expects list of node objects. Sorting, limiting, transforming 
	300, # Expects list of node objects. Convert selected nodes to text output
	400, # currently unused, left for future.
	500, # Adding header/footer, preserving other elements as needed
	600, # Transform built text further (exports, etc.)
	700, # custom operations
]

class UrtextDynamicDefinition:

	def __init__(self, param_string, project, location):

		
		self.location = location
		self.target_id = None
		self.target_file = None
		self.included_nodes = []
		self.excluded_nodes = []
		self.operations = []
		self.spaces = 0
		self.project = project
		self.preformat = False
		self.show = None
		self.multiline_meta = False
		self.returns_text = True
		self.init_self(param_string)
		self.all_ops = []
		self.source_id = None # set by node once compiled
		
		if not self.show:
			self.show = '$link\n'
			
	def init_self(self, contents):

		for match in syntax.function_c.findall(contents):

			func, argument_string = match[0], match[1]
			if func and func in self.project.directives:
				op = self.project.directives[func](self.project)
				op.set_dynamic_definition(self)
				op.parse_argument_string(argument_string)	
				self.operations.append(op)

			if func =='ID':
				## TODO: improve this prse
				self.target_id = argument_string.strip('>').strip('|').strip()
				continue

			if func == 'FILE':
				# currently works for files in the project path only
				self.target_file = argument_string
				continue

			if func == "SHOW":
				self.show = argument_string
		
		self.phases = [op.phase for op in self.operations]
		is_custom_output = max(self.phases) >= 700 if self.phases else False
		if not is_custom_output and not has_text_output(self.operations):
			# add simple list output if none supplied
			op = self.project.directives['TREE'](self.project)
			op.parse_argument_string('1')	
			op.set_dynamic_definition(self)
			self.operations.append(op)
			self.phases.append(300)

		self.all_ops = [t for op in self.operations for t in op.name]

		if all(i < 300 or i > 600 for i in self.phases):
			self.returns_text = False

	def preserve_title_if_present(self):
		if self.project.nodes[self.target_id].first_line_title:
			return ' ' + self.project.nodes[self.target_id].title + ' _\n'
		return ''

	def process_output(self, max_phase=800):
		
		outcome = [] # initially
		phases_to_process = [p for p in phases if p <= max_phase]
		operations = list(self.operations)
		
		all_operations = sorted(operations, key = lambda op: op.phase)
		for p in phases_to_process:
			if p == 200:
				# convert node_id list to node objects for remaining processing
				self.included_nodes = outcome
				outcome = [self.project.nodes[nid] for nid in outcome]
			next_phase = p + 100
			for operation in [op for op in all_operations if p <= op.phase < next_phase]:
				new_outcome = operation.dynamic_output(outcome)
				if new_outcome != False:
					outcome = new_outcome
		return outcome

def has_text_output(operations):
	for op in operations:
		if 300 <= op.phase < 400:
			return True
	return False 
