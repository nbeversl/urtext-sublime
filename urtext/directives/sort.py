import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
	from ..directive import  UrtextDirective
else:
	from urtext.directive import UrtextDirective

class Sort(UrtextDirective):

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
			value = node.metadata.get_first_value(k, return_type=True)	
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