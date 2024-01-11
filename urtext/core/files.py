class UrtextFiles:

	name = ["FILES"]
	phase = 300

	def dynamic_output(self, nodes):
		file_list = os.listdir(self.argument_string)
		output = []
		for f in file_list:
			output.append(''.join(['|/ ',f,' >\n']))
		return ''.join(output)

urtext_directives=[UrtextFiles]