import os
import re
from io import StringIO
import sys

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
	from Urtext.urtext.directive import UrtextDirectiveWithText
else:
	from urtext.directive import UrtextDirectiveWithText

python_code_regex = re.compile(r'(%%-PYTHON)(.*?)(%%-PYTHON-END)', re.DOTALL)

class Eval(UrtextDirectiveWithText):

	name = ["EVAL"]
	phase = 350

	def dynamic_output(self, input_contents):
		if self.text in self.project.nodes:
			contents = self.project.nodes[self.text].contents(do_strip_embedded_syntaxes=False)
		python_embed = python_code_regex.search(contents)
		if python_embed:
			python_code = python_embed.group(2)
			old_stdout = sys.stdout
			sys.stdout = mystdout = StringIO()
			localsParameter = {
				'UrtextProject' : self.project
			}
			try:
				exec(python_code, {}, localsParameter)
				sys.stdout = old_stdout
				message = mystdout.getvalue()
				return message
			except Exception as e:
				sys.stdout = old_stdout
				return str(e)
		return '(NO Python CODE FOUND)'

