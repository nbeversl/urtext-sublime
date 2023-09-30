class Log:

	name = ["LOG"]    
	phase = 300

	def dynamic_output(self, node_list):
		output = []
		for k in self.project.messages:
			if k:
				file = ''.join([
					self.syntax.file_link_opening_wrapper,
					k, 
					self.syntax.link_closing_wrapper
					])
			else:
				file = '(no file)'
			for message in self.project.messages[k]:
				output.append(''.join([
	                'in file ',
	                file,
	                ' ',
	                message,
	                '\n'
	                ]))
		return '\n'.join(output) + '\n'

urtext_directives=[Log]