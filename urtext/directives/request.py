from urtext_sublime.urtext.directive import  UrtextDirective
import urllib

class Request(UrtextDirective):

	name = ["REQUEST"]
	phase = 300
		
	def dynamic_output(self, nodes):

		try:
			with urllib.request.urlopen(self.argument_string) as f:
				t = f.read().decode('utf-8')
			return '%%-JSON\n'+ t +'\n%%-JSON-END\n'
		except urllib.error.URLError:
			return str(urllib.error.URLError)
