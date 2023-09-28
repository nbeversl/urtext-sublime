import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
	from Urtext.urtext.directives.tree_directive import Tree
else:
	from urtext.directives.tree import Tree

class NodeList:

	name = ["TREE"]    
	phase = 300
	
	def __init__(self, project):
		super().__init__(project)
		self.tree = Tree(project)

	def dynamic_output(self, node_list):

		self.tree.set_dynamic_definition(self.dynamic_definition)
		self.tree.parse_argument_string(self.argument_string)

		contents = []
		for n in node_list:		
			if self.tree.have_flags('*'):
				self.tree.depth = 99999
			else:
				if self.argument_string:
					try:
						self.tree.depth = int(self.argument_string)
					except:
						self.tree.depth = 1
				else:
					self.tree.depth = 1
					
			contents.append(self.tree.dynamic_output(n))
		return ''.join(contents)

	def on_file_modified(self, filename):
		self.tree.on_file_modified(filename)

urtext_directives = [NodeList]
