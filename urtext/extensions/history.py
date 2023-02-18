import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.urtext.extension import UrtextExtension
else:
    from urtext.extension import UrtextExtension

class RenameHistoryFiles(UrtextExtension):

    def on_file_renamed(self, old_filename, new_filename):
        
        old_history_file = os.path.join(
            os.path.dirname(old_filename), 
            'urtext_history',
            os.path.basename(old_filename) + '.diff')
        
        if os.path.exists(old_history_file):
            if not os.path.exists(os.path.join(
                    os.path.dirname(new_filename),
                    'urtext_history'
                    )):
                os.mkdir(
                    os.path.join(
                        os.path.dirname(new_filename), 
                        'urtext_history'))
            new_history_file = os.path.join(
                os.path.dirname(new_filename),
                'urtext_history',
                os.path.basename(new_filename) + '.diff')
            os.rename(old_history_file, new_history_file)


