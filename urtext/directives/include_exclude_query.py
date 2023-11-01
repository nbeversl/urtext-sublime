import re

class NodeQuery:

	name = ["QUERY"]
	phase = 100

	def build_list(self, passed_nodes):
		added_nodes = [l for l in self.links if l in self.project.nodes]		

		for arg in self.arguments:
			if re.match(self.syntax.virtual_target_marker+'self', arg):
				added_nodes.append(self.dynamic_definition.source_id)
				break

			if re.match(self.syntax.virtual_target_marker+'parent', arg):
				if self.project.nodes[
						self.dynamic_definition.source_id].parent:
					added_nodes.append(
						self.project.nodes[
							self.dynamic_definition.source_id].parent.id)
				break

		if not added_nodes:	
			added_nodes = set([])
			if self.have_flags('*'):
				added_nodes = set([node_id for node_id in self.project.nodes])
			added_nodes = added_nodes.union(_build_group_and(
					self.project, 
					self.params, 
					self.dynamic_definition,
					include_dynamic=self.have_flags('-dynamic'))
				)

		# flags specify how to LIMIT the query, whether it is + or -
		if self.have_flags('-title_only'):
			added_nodes = set([node_id for node_id in added_nodes if self.project.nodes[node_id].title_only])

		if self.have_flags('-untitled'):
			added_nodes = set([node_id for node_id in added_nodes if self.project.nodes[node_id].untitled])

		if self.have_flags('-is_meta'):
			added_nodes = set([node_id for node_id in added_nodes if self.project.nodes[node_id].is_meta])
		
		if self.have_flags('-is_not_meta'):
			added_nodes = set([node_id for node_id in added_nodes if not self.project.nodes[node_id].is_meta])

		if self.have_flags('-dynamic'):		
			added_nodes = set([node_id for node_id in added_nodes if self.project.nodes[node_id].dynamic])

		passed_nodes = set(passed_nodes)
		for target_id in self.dynamic_definition.target_ids:
			passed_nodes.discard(target_id)   
		self.dynamic_definition.included_nodes = list(passed_nodes.union(set(added_nodes)))
		return self.dynamic_definition.included_nodes

	def dynamic_output(self, nodes):
		return self.build_list(nodes)

class Exclude(NodeQuery):
	
	name = ["EXCLUDE","-"]
	phase = 105

	def dynamic_output(self, nodes):
		excluded_nodes = set(self.build_list([]))
		if self.have_flags('-including_as_descendants'):
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

urtext_directives=[Include, Exclude]