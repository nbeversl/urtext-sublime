class UrtextFiles:

	name = ["FILES"]

	def dynamic_output(self, text_contents):
		file_list = os.listdir(self.argument_string)
		output = []
		for f in file_list:
			output.append(''.join(['|/ ',f,' >\n']))
		return text_contents + ''.join(output)

urtext_directives=[UrtextFiles]