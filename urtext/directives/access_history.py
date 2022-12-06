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
    last_visited = None

    def on_node_visited(self, node_id):
        self.dynamic_definition.process_output(max_phase=200)
        if node_id in self.dynamic_definition.included_nodes and node_id != self.last_visited:
            if self.dynamic_definition.target_id in self.project.nodes:
                contents = self.project.nodes[self.dynamic_definition.target_id].contents()
                if self.project.nodes[self.dynamic_definition.target_id].first_line_title:
                    contents = self.strip_first_line_title(contents)
                contents = ''.join([ 
                        self.dynamic_definition.preserve_title_if_present(),
                        '\n',
                        self.project.timestamp(), 
                        ' | ', 
                        self.project.nodes[node_id].get_title(), 
                        ' >', 
                        contents
                    ])
                access_history_file = self.project.get_file_name(self.dynamic_definition.target_id)
                self.project.visit_file(access_history_file)
                self.project._set_node_contents(self.dynamic_definition.target_id, contents)
                self.project.visit_file(access_history_file)
                self.last_visited = node_id # prevents duplicates from multiple calls

    def strip_first_line_title(self, contents):
        title = syntax.title_regex_c.search(contents)
        return title.group().strip() + ' _'

    def dynamic_output(self, input_contents):
        return False # do not change existing output.



