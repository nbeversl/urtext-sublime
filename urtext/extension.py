class UrtextExtension:

    name = ["EXTENSION"]
    phase = 0
    
    def __init__(self, project):
        self.project = project

    def on_node_visited(self, node_id):
        return

    def on_node_added(self, node):
        return

    def on_file_modified(self, filename):
        return

    def on_init(self, project):
        return

    def on_file_renamed(self, old_filename, new_filename):
        return

    def on_node_id_changed(self, old_node_id, new_node_id):
        return