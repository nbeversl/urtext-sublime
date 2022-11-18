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
import re
import os

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
	from .directive import UrtextDirective
	from .utils import force_list
	from .directives.list import NodeList
	from .syntax import function_regex
else:
	from urtext.directive import UrtextDirective
	from urtext.utils import force_list
	from urtext.directives.list import NodeList
	from urtext.syntax import function_regex

class UrtextDynamicDefinition:

	def __init__(self, match, project):

		contents = match.group(0)[2:-2]
		self.location = match.start()
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
		self.init_self(contents)
		self.all_ops = []
		self.source_id = None # set by node once compiled
		
		
		if not self.show:
			self.show = '$link\n'
			
	def init_self(self, contents):

		for match in re.findall(function_regex,contents):

			func, argument_string = match[0], match[1]
			if func and func in self.project.directives:
				op = self.project.directives[func](self.project)
				op.set_dynamic_definition(self)
				op.parse_argument_string(argument_string)	
				self.operations.append(op)

			if func =='ID':
				## TODO: improve this prse
				node_id_match = argument_string.strip('>').strip('|').strip()
				self.target_id = node_id_match
				continue

			if func == 'FILE':
				# currently works for files in the project path only
				self.target_file = argument_string
				continue

			if func == "SHOW":
				self.show = argument_string
		
		self.all_ops = [t for op in self.operations for t in op.name]
		
		phases = [op.phase for op in self.operations]
		if all(i < 200 or i > 600 for i in phases):
			self.returns_text = False
		
		#needed?
		if 'SORT' not in self.all_ops:
			op = self.project.directives['SORT'](self.project)
			op.set_dynamic_definition(self)
			op.parse_argument_string('')		
			self.operations.append(op)

	def preserve_title_if_present(self):
		first_line_title = self.project.nodes[self.target_id].first_line_title
		if first_line_title:
			return ' ' + first_line_title + ' _\n'
		return ''

	def process_output(self, 
		phase=None, 
		max_phase=700):
		
		outcome = []
		
		for operation in sorted(self.operations, key = lambda op: op.phase) :		
			if operation.phase < max_phase:
				new_outcome = operation.dynamic_output(outcome)
				if new_outcome != False:
					outcome = new_outcome
		
		return outcome

