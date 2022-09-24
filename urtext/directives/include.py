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
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
	from Urtext.urtext.directive import UrtextDirectiveWithParamsFlags, UrtextDirectiveWithInteger
else:
	from urtext.directive import UrtextDirectiveWithParamsFlags, UrtextDirectiveWithInteger

class NodeQuery(UrtextDirectiveWithParamsFlags):

	name = ["QUERY"]
	phase = 100

	def build_list(self, passed_nodes):
		
		if self.have_flags('*'):
			if self.have_flags('-include_dynamic'):
				added_nodes = set([node_id for node_id in self.project.nodes])
			else:
				added_nodes = set([node_id for node_id in self.project.nodes if not self.project.nodes[node_id].dynamic])
	
		else: 
			added_nodes = set([])
			if self.have_flags('-blank'):
				added_nodes = set([node_id for node_id in self.project.nodes if self.project.nodes[node_id].blank])
			
			added_nodes = added_nodes.union(
				_build_group_and(
					self.project, 
					self.params, 
					include_dynamic=self.have_flags('-include_dynamic'))
				)
		
		passed_nodes = set(passed_nodes)
		passed_nodes.discard(self.dynamic_definition.target_id)           
		self.dynamic_definition.included_nodes = list(passed_nodes.union(set(added_nodes)))	
		return list(self.dynamic_definition.included_nodes)

	def dynamic_output(self, nodes):
		return self.build_list(nodes)

class Exclude(NodeQuery):
	
	name = ["EXCLUDE","-"]
	phase = 105

	def dynamic_output(self, nodes):
		excluded_nodes = set(self.build_list([]))
		self.dynamic_definition.excluded_nodes = list(excluded_nodes)
		return list(set(nodes) - excluded_nodes)
			 

class Include(NodeQuery):

	name = ["INCLUDE","+"] 	
	phase = 100

def _build_group_and(project, params, include_dynamic=False):
	
	found_sets = []
	new_group = set([])
	for group in params:
		key, value, operator = group
		if key.lower() == 'id' and operator == '=':
			value = value.split('/')[1]
			new_group = set([value])
		else:
			new_group = set(project.get_by_meta(key, value, operator))
		found_sets.append(new_group)
	
	for this_set in found_sets:
		new_group = new_group.intersection(this_set)

	if not include_dynamic:
		new_group = [f for f in new_group if f in project.nodes and not project.nodes[f].dynamic and not project.nodes[f].errors]
	
	return new_group

