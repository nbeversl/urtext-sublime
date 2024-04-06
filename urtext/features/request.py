import urllib

class Request:

	name = ["REQUEST"]
		
	def dynamic_output(self, text_contents):
		try:
			with urllib.request.urlopen(self.argument_string) as f:
				t = f.read().decode('utf-8')
			return text_contents + '%%JSON\n'+ t +'\n%%\n'
		except urllib.error.URLError:
			return text_contents + '\n' + str(urllib.error.URLError)

urtext_directives=[Request]