import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
	from Urtext.urtext.directive import UrtextDirective
else:
	from urtext.directive import UrtextDirective

class NodeQuery(UrtextDirective):

	name = ["QUERY"]
	phase = 100

	def build_list(self, passed_nodes):

		added_nodes = set([])
		if self.have_flags('*'):
			added_nodes = set([node_id for node_id in self.project.nodes])
		
		added_nodes = added_nodes.union(_build_group_and(
				self.project, 
				self.params, 
				self.dynamic_definition,
				include_dynamic=self.have_flags('-include_dynamic'))
			)

		if self.have_flags('-title_only'): # ONLY IF blank
			added_nodes = set([node_id for node_id in added_nodes if self.project.nodes[node_id].title_only])

		if self.have_flags('-untitled'): # ONLY IF blank
			added_nodes = set([node_id for node_id in added_nodes if self.project.nodes[node_id].untitled])
		
		if not self.have_flags('-include_dynamic'):		
			added_nodes = [f for f in added_nodes if f in self.project.nodes and not self.project.nodes[f].dynamic]

		passed_nodes = set(passed_nodes)
		passed_nodes.discard(self.dynamic_definition.target_id)   
		self.dynamic_definition.included_nodes = list(passed_nodes.union(set(added_nodes)))	

		return self.dynamic_definition.included_nodes

	def dynamic_output(self, nodes):
		return self.build_list(nodes)

class Exclude(NodeQuery):
	
	name = ["EXCLUDE","-"]
	phase = 105

	def dynamic_output(self, nodes):
		excluded_nodes = set(self.build_list([]))
		if self.have_flags('-including_descendants'):
			self.dynamic_definition.excluded_nodes = list(excluded_nodes)
		return list(set(nodes) - excluded_nodes)

class Include(NodeQuery):

	name = ["INCLUDE","+"] 	
	phase = 100

def _build_group_and(
	project, 
	params, 
	dd,
	include_dynamic=False):

	found_sets = []
	new_group = set([])
	for group in params:
		key, value, operator = group
		if key.lower() == 'id' and operator == '=':
			if '"' not in value and value != "@parent":
				print('NO READABLE VALUE in ', value)
				continue
			value = value.split('"')[1]
			new_group = set([value])
		else:
			if value == "@parent" and project.nodes[dd.source_id].parent:
				value = project.nodes[dd.source_id].parent.id
			new_group = set(project.get_by_meta(key, value, operator))
		found_sets.append(new_group)
	
	for this_set in found_sets:
		new_group = new_group.intersection(this_set)
	
	return new_group