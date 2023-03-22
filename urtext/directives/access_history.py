import os

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.urtext.directive import UrtextDirective
    import Urtext.urtext.syntax as syntax
else:
    from urtext.directive import UrtextDirective
    import urtext.syntax as syntax

class AccessHistory(UrtextDirective):

    name = ["ACCESS_HISTORY"]
    phase = 700

    def on_node_visited(self, node_id):
        
        self.dynamic_definition.process_output(max_phase=200)
        last_visited = None
        if len(self.project.navigation) > 1:
            last_visited = self.project.navigation[-2]
        if node_id in self.dynamic_definition.included_nodes and node_id != last_visited:
            if self.dynamic_definition.target_id in self.project.nodes:
                contents = self.project.nodes[self.dynamic_definition.target_id].contents(
                    strip_first_line_title=True)
                contents = ''.join([ 
                        self.dynamic_definition.preserve_title_if_present(),
                        '\n',
                        self.project.timestamp(as_string=True), 
                        ' ',
                        syntax.node_link_opening_wrapper, 
                        self.project.nodes[node_id].id, 
                        syntax.link_closing_wrapper, 
                        contents
                    ])
                self.project._set_node_contents(
                    self.dynamic_definition.target_id, 
                    contents,
                    parse=False)

    def dynamic_output(self, input_contents):
        return False # do not change existing output.
