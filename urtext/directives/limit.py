from urtext_sublime.urtext.directive import UrtextDirectiveWithInteger

class Limit(UrtextDirectiveWithInteger):

	name = ["LIMIT"]
	phase = 150

	def dynamic_output(self,nodes):
		if self.number:
			return nodes[:self.number]
		return nodes
