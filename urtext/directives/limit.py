from ..context import CONTEXT

if CONTEXT == 'Sublime Text':
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
