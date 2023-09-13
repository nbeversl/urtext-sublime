class UrtextExtension:

    phase = 0
    
    def __init__(self, project):
        self.project = project

    def after_project_initialized(self):
        return

    def on_file_parsed(self, filename):
        return

    def on_node_visited(self, node_id):
        return

    def on_new_file_node(self, node_id):
        return

    def on_node_added(self, node):
        return

    def on_file_modified(self, filename):
        return

    def on_file_added(self, filename):
        return

    def on_file_dropped(self, filename):
        return

    def on_file_deleted(self, filename):
        return

    def on_sub_tags_added(self,
        node_id, 
        entry, 
        next_node=None,
        visited_nodes=None):
        return

    def on_init(self, project):
        return

    def on_file_renamed(self, old_filename, new_filename):
        return

    def on_node_id_changed(self, old_node_id, new_node_id):
        return