import urllib

class Request:

	name = ["REQUEST"]
	phase = 300
		
	def dynamic_output(self, nodes):

		try:
			with urllib.request.urlopen(self.argument_string) as f:
				t = f.read().decode('utf-8')
			return '%%JSON\n'+ t +'\n%%\n'
		except urllib.error.URLError:
			return str(urllib.error.URLError)

urtext_directives=[Request]