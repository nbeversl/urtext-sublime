class Sort:

	name = ["SORT","S"]
	phase = 220
		
	def dynamic_output(self, nodes):
		sorted_nodes = []
		if self.keys_with_flags:
			for key_with_flags in self.keys_with_flags:
				key = key_with_flags[0]
				reverse = '-r' in key_with_flags[1] or '-reverse' in key_with_flags[1]
				sorted_nodes.extend(
					sorted(
						nodes,
						key=lambda node: self.sort_values(
							node, 
							key),
						reverse=reverse)
					)
			return sorted_nodes
		return nodes

	def sort_values(self, 
		node, 
		key):

		t = []
		k, ext = key, ''
		if '.' in k:
			k, ext = k.split('.')

		use_timestamp=False
		if ext == 'timestamp':
			use_timestamp= True
		value = node.metadata.get_first_value(
			k,
			use_timestamp=use_timestamp)
		if not value:
			return tuple([])
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

urtext_directives=[Sort]