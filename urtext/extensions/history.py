from urtext_sublime.urtext.extension import UrtextExtension
import os

class RenameHistoryFiles(UrtextExtension):

    def on_file_renamed(self, old_filename, new_filename):
        
        history_file = os.path.join(
            self.project.path, 
            'history',
            old_filename.replace('.txt','.diff'))
        if os.path.exists(history_file):
            os.rename(history_file,
                os.path.join(self.project.path,'history', new_filename.replace('.txt','.diff'))
                )


