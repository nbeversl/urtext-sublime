class When:

	name = ["WHEN"]    
	phase = 50
	
	def should_continue(self):
		if self.have_flags('-never'):
			return False
		for flag in self.flags:
			if flag in self.dynamic_definition.flags:
				return True
		return False

urtext_directives = [ When ]