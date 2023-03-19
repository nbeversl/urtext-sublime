import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.urtext.extension import UrtextExtension
    from Urtext.anytree import Node
    import Urtext.urtext.syntax as syntax
else:
    from urtext.extension import UrtextExtension
    from anytree import Node
    import urtext.syntax as syntax

class UrtextAnyTree(UrtextExtension):

    name = ["TREE_EXTENSION"]

    def on_file_modified(self, filename):
        """ Build anytree elements """
        for node in self.project.files[filename].nodes:

            for pointer in node.pointers:
                alias_node = Node('ALIA$'+pointer['id']) # anytree Node, not UrtextNode 
                alias_node.position = pointer['position']
                alias_node.parent = node.tree_node
                self.project.files[filename].alias_nodes.append(alias_node)

            if node.parent:
                node.tree_node.parent = node.parent.tree_node

    def on_node_added(self, node):
        node.tree_node = Node(node.id)

    def on_node_title_changed(self, old_node_id, new_node_id):
        self.project.nodes[new_node_id].tree_node.name = new_node_id

    def on_file_removed(self, filename):
        for node_id in self.project.files[filename].nodes:
            self.project.nodes[node_id].tree_node.parent = None
            del self.project.nodes[node_id].tree_node
        for a in self.project.files[filename].alias_nodes:
            a.parent = None
            a.children = []
