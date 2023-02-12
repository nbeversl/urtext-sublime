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

        parsed_items = self.project.files[filename].parsed_items
        positions = sorted(parsed_items.keys())

        # parse each pointer, positioning it within its parent node
        for position in positions:

            if syntax.pointer_closing_wrapper_c.match(parsed_items[position][len(syntax.pointer_closing_wrapper) * - 1:]):                
                inserted_node_id = parsed_items[position][:len(syntax.pointer_closing_wrapper) * - 1].strip()
                parent_node = self.project.get_node_id_from_position(filename, position)
                if not parent_node:
                    continue
                alias_node = Node('ALIAS to '+inserted_node_id) # anytree Node, not UrtextNode 
                alias_node.parent = self.project.nodes[parent_node].tree_node
                self.project.files[filename].alias_nodes.append(alias_node)
                continue

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
