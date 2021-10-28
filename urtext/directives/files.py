from urtext_sublime.urtext.directive import UrtextDirective
import os

class UrtextFiles(UrtextDirective):

	name = ["FILES"]
	phase = 300

	def dynamic_output(self, nodes):
		file_list = os.listdir(os.path.join(self.project.path, self.argument_string))
		output = []
		for f in file_list:
			output.append(join(['>f',f,'\n']))
		return ''.join(output)