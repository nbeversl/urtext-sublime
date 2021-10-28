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

node_id_regex = r'>[0-9,a-z]{3}\b'
function_regex = re.compile('([A-Z_\-\+]+)\((.*?)\)', re.DOTALL)
from .directive import UrtextDirective
from .utils import force_list
from .directives.list import NodeList

class UrtextDynamicDefinition:

	def __init__(self, match, project):

		contents = match.group(0)[2:-2]

		self.location = match.start()
		self.target_id = None
		self.target_file = None
		self.included_nodes = []
		self.excluded_nodes = []
		self.used_functions = []
		self.operations = []
		self.spaces = 0
		self.project = project
		self.preformat = False
		self.show = None
		self.multiline_meta = False
		self.init_self(contents)
		
		if not self.show:
			self.show = '$title $link\n'
			
	def init_self(self, contents):

		for match in re.findall(function_regex,contents):

			func, argument_string = match[0], match[1]
			if func and func in self.project.directives:
				op = self.project.directives[func](self.project)
				op.set_dynamic_definition(self)
				op.parse_argument_string(argument_string)	
				self.operations.append(op)

			if func =='ID':
				node_id_match = re.search(node_id_regex, argument_string)
				if node_id_match:
					self.target_id = node_id_match.group(0)[1:]
					continue

			if func == 'FILE':
				# currently works for files in the project path only
				self.target_file = argument_string
				continue

			if func == "SHOW":
				self.show = argument_string
		
		all_ops = [t for op in self.operations for t in op.name]
		
		if 'ACCESS_HISTORY' not in all_ops  and 'TREE' not in all_ops and 'COLLECT' not in all_ops:
			op = self.project.directives['TREE'](self.project)
			op.parse_argument_string('1')		
			op.set_dynamic_definition(self)
			self.operations.append(op)
		
		if 'SORT' not in all_ops:
			op = self.project.directives['SORT'](self.project)
			op.set_dynamic_definition(self)
			op.parse_argument_string('')		
			self.operations.append(op)

	def process_output(self, max_phase=600):
		outcome = []
		
		for operation in sorted(self.operations, key = lambda op: op.phase) :		
		
			if operation.phase < max_phase:
				new_outcome = operation.dynamic_output(outcome)
				if new_outcome != False:
					outcome = new_outcome
		return outcome
