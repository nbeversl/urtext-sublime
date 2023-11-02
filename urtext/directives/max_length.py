class MaxLength:

	phase = 800
	name = ["MAX_LENGTH"]

	def dynamic_output(self, contents):
		if self.argument_string:
			length = self.argument_string
			try:
				length = int(length)
			except:
				self.project._log_item(					
					self.project.nodes[self.dynamic_definition.source_id].filename,
					'MAX_LENGTH directive does not contain a number')
				return contents
			contents = contents.split('\n')			
			return '\n'.join(contents[:length])
		return contents

urtext_directives=[MaxLength]