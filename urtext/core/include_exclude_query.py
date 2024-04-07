import re

class NodeQuery:

	name = ["QUERY"]

	def build_list(self):
		added_nodes = set([l.node_id for l in self.links if l.node_id and l.node_id in self.project.nodes])

		for arg in self.arguments:
			if re.match(self.syntax.virtual_target_marker+'self', arg):
				added_nodes.update(self.dynamic_definition.source_node.id)
				break

			if re.match(self.syntax.virtual_target_marker+'parent', arg):
				if self.dynamic_definition.source_node.parent:
					added_nodes.update(self.dynamic_definition.source_node.parent.id)
				break

		if not added_nodes:	
			added_nodes = set()
			if self.have_flags('*'):
				added_nodes.update([node_id for node_id in self.project.nodes])
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
		
		for target_id in self.dynamic_definition.target_ids:
			added_nodes.discard(target_id)  

		return list(added_nodes)

class Exclude(NodeQuery):
	
	name = ["EXCLUDE","-"]

	def dynamic_output(self, nodes):
		excluded_nodes = set(self.build_list())
		# this flag will have to be reimplemented
		# if self.have_flags('-including_as_descendants'):
		self.dynamic_definition.excluded_nodes.extend(
			[self.project.nodes[nid] for nid in list(excluded_nodes) if nid in self.project.nodes])
		

class Include(NodeQuery):

	name = ["INCLUDE","+"] 	

	def dynamic_output(self, nodes):
		included_nodes = self.build_list()
		self.dynamic_definition.included_nodes.extend(
			[self.project.nodes[nid] for nid in list(included_nodes) if nid in self.project.nodes])


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
			if value == "@parent" and dd.source_node.parent:
				value = dd.source_node.parent.id
			new_group = set(project.get_by_meta(key, value, operator))
		found_sets.append(new_group)
	
	for this_set in found_sets:
		new_group = new_group.intersection(this_set)
	
	return new_group

urtext_directives=[Include, Exclude]