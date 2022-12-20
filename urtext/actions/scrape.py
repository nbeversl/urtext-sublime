import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.urtext.action import UrtextAction
    from Urtext.urtext.dynamic import UrtextDynamicDefinition
    import Urtext.urtext.syntax as syntax
else:
    from urtext.action import UrtextAction
    from urtext.dynamic import UrtextDynamicDefinition
    import urtext.syntax as syntax

class Scrape(UrtextAction):

    name=['SCRAPE']

    def execute(self, 
        param_string, 
        filename=None,
        action_span=None,
        file_pos=0,
        col_pos=0, 
        node_id=None):
        
        dd = UrtextDynamicDefinition(''.join([
            syntax.dynamic_def_opening_wrapper,
            param_string,
            dynamic_def_closing_wrapper]), self.project, None)  
        self.project.files[filename]._replace_contents(
            dd.process_output(), [file_pos, file_pos + action_span[1]])
        