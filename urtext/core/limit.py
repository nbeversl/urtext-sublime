class Limit:

	name = ["LIMIT"]

	def dynamic_output(self, text_contents):
		if self.argument_string:
			number = int(self.argument_string)
			if number:
				self.dynamic_definition.included_nodes = self.dynamic_definition.included_nodes[:number]

urtext_directives=[Limit]