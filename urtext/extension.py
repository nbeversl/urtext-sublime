import Urtext.urtext.syntax as syntax
import urtext.syntax as syntax
from urtext.dynamic_output import DynamicOutput
from anytree import Node, RenderTree, PreOrderIter
from anytree.render import ContStyle
from urtext.timestamp import UrtextTimestamp

class UrtextExtension:

    syntax = syntax
    name = []
    DynamicOutput = DynamicOutput
    Node = Node
    RenderTree = RenderTree
    PreOrderIter = PreOrderIter
    UrtextTimestamp = UrtextTimestamp
    
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

    def on_buffer_added(self, filename):
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