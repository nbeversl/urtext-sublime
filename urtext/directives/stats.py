import os
import sys

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
	from Urtext.urtext.directive import UrtextDirective
else:
	from urtext.directive import UrtextDirective

class UrtextStats(UrtextDirective):

	name = ["STATS"]
	phase = 300

	def dynamic_output(self, nodes):

		contents = []
		contents.append('Project Title : '+self.project.settings['project_title'])
		contents.append('project size in memory (bytes): '+ str(sys.getsizeof(self.project)))

		n_memory = 0
		for node_id in self.project.nodes:
			n_memory += sys.getsizeof(self.project.nodes[node_id])
		contents.append('nodes size in memory (kB): '+ str(n_memory / 1000))
		contents.append('# files : '+ str(len(self.project.files)))
		contents.append('# nodes : '+ str(len(self.project.nodes)))
		contents.append('# dynamic defs : '+ str(len(self.project.dynamic_definitions)))
		contents.append('compile time :' + str(self.project.last_compile_time))
		return '\n'.join(contents)