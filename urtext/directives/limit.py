import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
	from Urtext.urtext.directive import UrtextDirective
else:
	from urtext.directive import UrtextDirective

class Limit(UrtextDirective):

	name = ["LIMIT"]
	phase = 250

	def dynamic_output(self, nodes):
		if self.argument_string:
			number = int(self.argument_string)
			if number:
				return nodes[:number]
		return nodes
