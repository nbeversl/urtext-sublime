class UrtextHistoryDiffRename:

	def on_file_renamed(self, old_filename, new_filename):
	    history_file = os.path.join(
	    	os.path.dirname(old_filename),
	    	'_diff', 
	    	os.path.basename(old_filename) + '.diff')

	    if os.path.exists(history_file):
	        os.rename(
	            history_file,
	            os.path.join(os.path.dirname(old_filename), 
	                '_diff', 
	                os.path.basename(new_filename) + '.diff')
	           	)