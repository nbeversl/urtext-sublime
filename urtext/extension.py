import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    import Urtext.urtext.syntax as syntax
else:
    import urtext.syntax as syntax

class UrtextExtension:

    phase = 0
    syntax = syntax
    name = []
    
    def __init__(self, project):
        self.project = project
        self.folder = None

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