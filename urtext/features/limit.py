class Limit:

	name = ["LIMIT"]
	phase = 250

	def dynamic_output(self, nodes):
		if self.argument_string:
			number = int(self.argument_string)
			if number:
				return nodes[:number]
		return nodes

urtext_directives=[Limit]