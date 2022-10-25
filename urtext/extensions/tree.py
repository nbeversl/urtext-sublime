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
        positions = sorted(parsed_items)
    
        for position in positions:

            node = parsed_items[position].strip()

            if node not in self.project.nodes:
                continue
           
            # parse each marker, positioning it within its parent node
            if node[-2:] == '>>':
                inserted_node_id = node[:-2]
                # print(inserted_node_id)
                parent_node = self.project.get_node_id_from_position(filename, position)  
                if not parent_node:
                    continue 
                alias_node = Node('ALIAS'+inserted_node_id)
                alias_node.parent = self.project.nodes[parent_node].tree_node
                self.project.files[filename].alias_nodes.append(alias_node)
                continue

            if position == 0 and parsed_items[0] == '{':
                self.project.nodes[node].tree_node.parent = self.project.nodes[root_node_id].tree_node
                continue

            start_of_node = self.project.nodes[node].ranges[0][0]
            
            parent = self.project.get_node_id_from_position(filename, start_of_node - 1)
            while parent in self.project.nodes and self.project.nodes[parent].compact:
                start_of_node = self.project.nodes[parent].ranges[0][0]
                parent = self.project.get_node_id_from_position(filename, start_of_node - 1)
            if parent:
                self.project.nodes[node].tree_node.parent = self.project.nodes[parent].tree_node

    def on_file_removed(self, filename):
        for node_id in self.project.files[filename].nodes:
            self.project.nodes[node_id].tree_node.parent = None
            self.project.nodes[node_id].tree_node = Node(node_id)
        for a in self.project.files[filename].alias_nodes:
            a.parent = None
            a.children = []
