import os 
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
	from Urtext.urtext.directive import UrtextDirective
	import Urtext.urtext.syntax as syntax
else:
	from urtext.directive import UrtextDirective
	import urtext.syntax as syntax

class Log(UrtextDirective):

	name = ["LOG"]    
	phase = 300
			
	def dynamic_output(self, node_list):
		output = []
		for k in self.project.messages:
			if k:
				file = syntax.file_link_opening_wrapper + k + syntax.link_closing_wrapper
			else:
				file = '(no file) '
			for message in self.project.messages[k]:
				output.append(''.join([
	                'in file : ',
	                file,
	                '\n']) + message)

		return '\n'.join(output) + '\n'
