class AccessHistory:

    name = ["ACCESS_HISTORY"]
    phase = 700

    def __init__(self, project):
        super().__init__(project)
        self.project.variables['access_history_last_visited'] = None

    def on_node_visited(self, node_id):
        self.dynamic_definition.process_output(max_phase=200)
        if node_id in self.dynamic_definition.included_nodes and node_id != self.project.variables['access_history_last_visited']:
            for target_id in self.dynamic_definition.target_ids:
                if target_id in self.project.nodes:
                    current_contents = self.project.nodes[target_id].contents(
                        stripped=False,
                        strip_first_line_title=True)
                    new_contents = ''.join([
                            self.project.timestamp(as_string=True), 
                            ' ',
                            self.syntax.link_opening_wrapper, 
                            node_id, 
                            self.syntax.link_closing_wrapper,
                            current_contents
                        ]) 
                    new_contents = self.dynamic_definition.post_process(target_id, new_contents)
                    self.project.nodes[target_id].set_content(new_contents)
                    self.project.variables['access_history_last_visited'] = node_id

    def dynamic_output(self, input_contents):
        return False

urtext_directives=[AccessHistory]

