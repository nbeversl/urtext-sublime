import re
import sys
from io import StringIO
from urtext.utils import force_list, get_id_from_link
from urtext.file import UrtextFile, UrtextBuffer
from urtext.node import UrtextNode
from urtext.timestamp import UrtextTimestamp
from urtext.directive import UrtextDirective
import urtext.syntax as syntax

python_code_regex = re.compile(r'(%%Python)(.*?)(%%)', re.DOTALL)

class Exec:

	name = ["EXEC"]

	def dynamic_output(self, text_contents):
		node_to_exec = get_id_from_link(self.argument_string)
		if node_to_exec in self.project.nodes:
			contents = self.project.nodes[node_to_exec].full_contents
			python_embed = python_code_regex.search(contents)
			if python_embed:
				python_code = python_embed.group(2)
				old_stdout = sys.stdout
				sys.stdout = mystdout = StringIO()
				localsParameter = {
					'ThisProject' : self.project,
					'UrtextFile' : UrtextFile,
					'UrtextBuffer' : UrtextBuffer,
					'UrtextNode' : UrtextNode,
					'UrtextTimestamp' : UrtextTimestamp,
					'UrtextDirective': UrtextDirective,
					'UrtextSyntax': syntax
					}
				try:
					exec(python_code, {}, localsParameter)
					sys.stdout = old_stdout
					message = mystdout.getvalue()
					return text_contents + message
				except Exception as e:
					sys.stdout = old_stdout
					return text_contents + ''.join([
						'error in | ',
						node_to_exec,
						' >',
						' ',
						str(e),
						'\n'
						])
		return text_contents + '(no Python code found)'
