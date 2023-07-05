import os 
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
	from Urtext.urtext.directive import UrtextDirective
	import Urtext.urtext.syntax as syntax
else:
	from urtext.directive import UrtextDirective
	import urtext.syntax as syntax

class When(UrtextDirective):

	name = ["WHEN"]    
	phase = 50
	
	def should_continue(self):
		if self.have_flags('-never'):
			return False
		for flag in self.flags:
			if flag in self.dynamic_definition.flags:
				return True
		return False
