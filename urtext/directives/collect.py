import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
	from Urtext.urtext.dynamic_output import DynamicOutput
	from Urtext.anytree import Node, PreOrderIter, RenderTree
	from Urtext.urtext.timestamp import UrtextTimestamp, default_date
	from Urtext.urtext.directive import UrtextDirective
	import Urtext.urtext.syntax as syntax
else:
	from urtext.directive import UrtextDirective
	from urtext.dynamic_output import DynamicOutput
	from anytree import Node, PreOrderIter, RenderTree
	from urtext.timestamp import UrtextTimestamp, default_date
	from urtext.directive import UrtextDirective
	import urtext.syntax as syntax

class Collect(UrtextDirective):

	name = ["COLLECT"]
	phase = 300

	""" 
	generates a collection of context-aware metadata 
	anchors in list or tree format 
	"""

	def dynamic_output(self, nodes):
	   
		m_format = self.dynamic_definition.show
		keys = {}
		
		for entry in self.params:
			k, v, operator = entry
			if operator == '!=' and k in keys:
				keys[k].remove(v)
				continue
			if k =='*':
				for k in self.project.get_all_keys():
					keys[k] = [v.lower()]
			else:
				keys[k] = [v.lower()]

		found_stuff = []
		for node in nodes:
			for k in keys:
				use_timestamp = k in self.project.settings['use_timestamp']
				for v in keys[k]:
					if v == '*':
						entries = node.metadata.get_entries(k)
					else:
						entries = node.metadata.get_matching_entries(k, v)

					for entry in entries:
						found_item = {}
						if v == '*':
							if use_timestamp:
								value = entry.timestamps[0].datetime
							else:
								value = entry.value
						else:
							if use_timestamp and entry.timestamps[0].datetime == v:
								value =entry.timestamps[0].datetime
							else:
								value = entry.value

						found_item['node_id'] = node.id
						found_item['title'] = node.title
						found_item['dt_string'] = entry.timestamps[0].unwrapped_string if entry.timestamps else ''

						if use_timestamp:
							found_item['value'] = entry.timestamps[0].unwrapped_string
							found_item['sort_value'] = entry.timestamps[0].datetime
					   
						else:
							found_item['value'] = value
							sort_value = value
							if self.have_flags('-sort_numeric'):
								try:
									sort_value = float(value)
								except ValueError: 
									sort_value = 99999999
							else:
								sort_value = str(sort_value)
		
							found_item['sort_value'] = sort_value

						found_item['keyname'] = k
						full_contents = node.contents(preserve_length=True)
						
						context = []
						length = 0
						lines = full_contents.split('\n')
						for line in lines:
							length += len(line)
							if entry.end_position < length:
								break

						found_item['context'] = line.strip().replace('_',' ')
						while syntax.pointer_closing_wrapper in found_item['context']:
							found_item['context'] = found_item['context'].replace(
								syntax.pointer_closing_wrapper,
								syntax.node_closing_wrapper)

						# this will be position in NODE, not FILE:
						found_item['position'] = str(entry.position + 1)
						found_stuff.append(found_item)
	
		if not found_stuff:
			 return ''
		
		if '-tree' not in self.flags:

			collection = []
		
			sorted_stuff = sorted(found_stuff, 
				key=lambda x: ( x['sort_value'] ),
				reverse=self.have_flags('-sort_reverse'))

			for item in sorted_stuff:

				next_content = DynamicOutput(m_format, self.project.settings)

				next_content.title = item['title']
				next_content.entry = item['keyname'] + ' :: ' +  str(item['value'])
				next_content.key = item['keyname']
				next_content.values = item['value']
				
				position_suffix = ''
				if item['position'] != '0':
					position_suffix = ''.join([':', item['position']])
				
				next_content.link =''.join([
					syntax.link_opening_wrapper,
					item['node_id'],
					syntax.link_closing_wrapper,
					position_suffix,
					])

				next_content.date = item['dt_string']
				next_content.meta = self.project.nodes[
					item['node_id']].consolidate_metadata()

				contents = item['context']
				while '\n\n' in contents:
					contents = contents.replace('\n\n', '\n')
				next_content.contents = contents

				#TODO refactor with same in tree.py
				for meta_key in next_content.needs_other_format_keys:
					next_content.other_format_keys[
                    meta_key] = self.project.nodes[
						item['node_id']].get_extended_values(
                        meta_key)

				collection.extend([next_content.output()])

			return ''.join(collection)

		if '-tree' in self.flags:
			# TODO be able to pass an m_format for Dynamic Output here.

			contents = ''
			for k in sorted(keys.keys()):
				root = Node(k)
				if not contains_different_types(keys[k]):
				   keys[k] = sorted(keys[k], key=meta_value_sort_criteria)
				
				for v in keys[k]:
					f = None
					if isinstance(v, UrtextTimestamp):
						t=Node(v.unwrapped_string)
					else:
						t = Node(v) 
					for node in nodes:
						for n in node.metadata.get_matching_entries(k,value):
							f = Node(node.id + ' >' + node.id) #?
							f.parent = t
						if f:                        
							t.parent = root
				for pre, _, node in RenderTree(root):
					contents += "%s%s\n" % (pre, node.name)

			return contents

def meta_value_sort_criteria(v):
	if isinstance(v,UrtextTimestamp):
		return v.datetime
	return v

def contains_different_types(list_to_check):
	if len(list_to_check) < 2:
		return False
	i = type(list_to_check[0])
	for y in list_to_check:
		if type(y) != i:
			return True
	return False