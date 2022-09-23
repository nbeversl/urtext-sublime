import os 
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
	from Urtext.urtext.directive import UrtextDirective
else:
	from urtext.directive import UrtextDirective

class Log(UrtextDirective):

	name = ["LOG"]    
	phase = 500
			
	def dynamic_output(self, node_list):
		output = []
		for k in self.project.messages:
			if k:
				file = 'f>'+k+'; '
			else:
				file = '(no file) '
			for message in self.project.messages[k]:
				output.append(file + ":" + message)

		return '\n'.join(output) + '\n'
