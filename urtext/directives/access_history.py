class AccessHistory:

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
                            self.syntax.link_opening_wrapper, 
                            node_id, 
                            self.syntax.link_closing_wrapper,
                        ]))
        self.last_visited = node_id

    def dynamic_output(self, input_contents):
        return False

urtext_directives=[AccessHistory]

