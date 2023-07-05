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

    def __init__(self, project):
        super().__init__(project)
        self.last_visited = None

    def on_node_visited(self, node_id):
        self.dynamic_definition.process_output(max_phase=200)
        if node_id in self.dynamic_definition.included_nodes and node_id != self.last_visited:
            for target_id in self.dynamic_definition.target_ids:
                if target_id in self.project.nodes:
                    self.project.nodes[target_id].prepend_content(''.join([
                            '\n',
                            self.project.timestamp(as_string=True), 
                            ' ',
                            syntax.link_opening_wrapper, 
                            node_id, 
                            syntax.link_closing_wrapper,
                        ]))
        self.last_visited = node_id

    def dynamic_output(self, input_contents):
        return False

