class Sort:

	name = ["SORT","S"]
	phase = 220
		
	def dynamic_output(self, nodes):

		if self.keys:
			return sorted(
				nodes,
				key=lambda node: self.sort_values(node, self.keys),
				reverse=self.have_flags(['-reverse','-r'])
				)
	
		return nodes

	def sort_values(self, node, keys):
		t = []
		for k in keys:
			k, ext = k, ''
			if '.' in k:
				k, ext = k.split('.')

			use_timestamp=False
			if ext == 'timestamp':
				use_timestamp= True

			value = node.metadata.get_first_value(
				k, 
				return_type=True,
				use_timestamp=use_timestamp)
			if isinstance(value, str):
				value=value.lower()			
			t.append(value)
		if self.have_flags('-num'):
			try:
				nt = [int(n) for n in t]
			except ValueError:
				return tuple([])
			return tuple(nt)
		return tuple(t)

urtext_directives=[Sort]