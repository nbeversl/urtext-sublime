class Sort:

	name = ["SORT","S"]
	phase = 220
		
	def dynamic_output(self, nodes):
		sorted_nodes = []
		if self.keys_with_flags:
			for key_with_flags in self.keys_with_flags:
				key, flags = key_with_flags
				reverse = '-r' in flags or '-reverse' in flags
				flags = strip_reverse(flags)
				group_to_sort = [n for n in nodes if n.metadata.get_values(key)]
				sorted_nodes.extend(
					sorted(
						group_to_sort,
						key=lambda node: self.sort_values(
							node, 
							key,
							flags,
							),
						reverse=reverse)
					)
				nodes = [n for n in nodes if n not in group_to_sort]
			sorted_nodes.extend(nodes)
			return sorted_nodes
		return nodes

	def sort_values(self, 
		node, 
		key,
		flags):

		t = []
		k, ext = key, ''
		if '.' in k:
			k, ext = k.split('.')

		order_by=None
		if flags:
			order_by = flags[0]
		use_timestamp=False
		if ext == 'timestamp':
			use_timestamp= True
		value = node.metadata.get_first_value(
			k,
			order_by=order_by,
			use_timestamp=use_timestamp)
		
		if use_timestamp:
			value = value.datetime
		if isinstance(value, str):
			value = value.lower()			
		t.append(value)
	
		if self.have_flags('-num'):
			try:
				nt = [int(n) for n in t]
			except ValueError:
				return tuple([])
			return tuple(nt)
		return tuple(t)

def strip_reverse(flags):
	flags=list(flags)
	while '-r' in flags:
		flags.remove('-r')
	while '-reverse' in flags:
		flags.remove('-reverse')
	return flags


urtext_directives=[Sort]