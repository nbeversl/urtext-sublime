import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.urtext.extension import UrtextExtension
    from Urtext.anytree import Node
else:
    from urtext.extension import UrtextExtension
    from anytree import Node

class UrtextAnyTree(UrtextExtension):

    name = ["TREE_EXTENSION"]

    def on_file_modified(self, filename):
        """ Build tree elements """

        parsed_items = self.project.files[filename].parsed_items
        positions = sorted(parsed_items.keys())
        for position in positions:

            # parse each marker, positioning it within its parent node
            if parsed_items[position][-2:].strip() == '>>':
                inserted_node_id = parsed_items[position][:-2].strip()
                parent_node = self.project.get_node_id_from_position(filename, position)
                if not parent_node:
                    continue
                alias_node = Node('ALIAS'+inserted_node_id)
                alias_node.parent = self.project.nodes[parent_node].tree_node
                self.project.files[filename].alias_nodes.append(alias_node)
                continue

            node_title = parsed_items[position].strip()
            if node_title not in self.project.nodes:
                continue

            if position == 0 and parsed_items[0] == '{':
                self.project.nodes[node_title].tree_node.parent = self.project.nodes[root_node_id].tree_node
                continue

            start_of_node = self.project.nodes[node_title].start_position()
            
            parent = self.project.get_node_id_from_position(filename, start_of_node - 1)
            if parent:
                while self.project.nodes[parent].compact:
                    start_of_node = self.project.nodes[parent].start_position()
                    if start_of_node == 0:
                        parent = self.project.nodes[self.project.files[filename].root_nodes[0]].title
                        break
                    else:
                        parent = self.project.get_node_id_from_position(filename, start_of_node - 1)
                        if not parent:
                            parent = self.project.nodes[self.project.files[filename].root_nodes[0]].title
                            break
                self.project.nodes[node_title].tree_node.parent = self.project.nodes[parent].tree_node

    def on_file_removed(self, filename):
        for node_id in self.project.files[filename].nodes:
            self.project.nodes[node_id].tree_node.parent = None
            self.project.nodes[node_id].tree_node = Node(node_id)
        for a in self.project.files[filename].alias_nodes:
            a.parent = None
            a.children = []
