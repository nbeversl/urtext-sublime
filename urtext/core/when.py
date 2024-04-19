When Directive _

%%Python
class When:

	name = ["WHEN"]    
	
	def should_continue(self):
		if self.have_flags('-never'):
			return False
		for flag in self.flags:
			if flag in self.dynamic_definition.flags:
				return True
		return False

ThisProject.add_directive(When)
%%