import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.urtext.action import UrtextAction
else:
    from urtext.action import UrtextAction

class Scrape(UrtextAction):

    name=['SCRAPE']

    def execute(self, 
        param_string, 
        filename=None,
        file_pos=0,
        col_pos=0, 
        node_id=None):

        print(param_string)

 