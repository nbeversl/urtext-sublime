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
            for pointer in self.project.nodes[node].pointers:
                alias_node = Node('ALIA$'+pointer['id']) # anytree Node, not UrtextNode 
                alias_node.position = pointer['position']
                alias_node.parent = self.project.nodes[node].tree_node
                self.project.files[filename].alias_nodes.append(alias_node)

        for node_title in self.project.files[filename].nodes:
            if self.project.nodes[node_title].parent:
                self.project.nodes[node_title].tree_node.parent = self.project.nodes[node_title].parent.tree_node

    def on_file_removed(self, filename):
        for node_id in self.project.files[filename].nodes:
            self.project.nodes[node_id].tree_node.parent = None
            self.project.nodes[node_id].tree_node = Node(node_id)
        for a in self.project.files[filename].alias_nodes:
            a.parent = None
            a.children = []
