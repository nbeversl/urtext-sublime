import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
	from Urtext.urtext.directive import UrtextDirectiveWithInteger
else:
	from urtext.directive import UrtextDirectiveWithInteger

class Limit(UrtextDirectiveWithInteger):

	name = ["LIMIT"]
	phase = 250

	def dynamic_output(self,nodes):
		if self.number:
			return nodes[:self.number]
		return nodes
