import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
	from Urtext.urtext.directive import UrtextDirective
else:
	from urtext.directive import UrtextDirective

class UrtextFiles(UrtextDirective):

	name = ["FILES"]
	phase = 300

	def dynamic_output(self, nodes):
		file_list = os.listdir(self.argument_string)
		output = []
		for f in file_list:
			output.append(''.join(['|/ ',f,' >\n']))
		return ''.join(output)