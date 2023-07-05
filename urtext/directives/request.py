import urllib
import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
	from Urtext.urtext.directive import  UrtextDirective
else:
	from urtext.directive import  UrtextDirective

class Request(UrtextDirective):

	name = ["REQUEST"]
	phase = 300
		
	def dynamic_output(self, nodes):

		try:
			with urllib.request.urlopen(self.argument_string) as f:
				t = f.read().decode('utf-8')
			return '%%JSON\n'+ t +'\n%%\n'
		except urllib.error.URLError:
			return str(urllib.error.URLError)
