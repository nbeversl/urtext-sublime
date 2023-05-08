import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.urtext.extension import UrtextExtension
    from Urtext.anytree import Node
else:
    from urtext.extension import UrtextExtension
    from anytree import Node

class UrtextAnyTree(UrtextExtension):

    name = ["TREE_EXTENSION"]

    def on_file_added(self, filename):
        if filename in self.project.files:
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

    def on_node_id_changed(self, old_node_id, new_node_id):
        self.project.nodes[new_node_id].tree_node.name = new_node_id

    def on_file_dropped(self, filename):
        for node in self.project.files[filename].nodes:
            node.tree_node.parent = None
            del node.tree_node
        for a in self.project.files[filename].alias_nodes:
            a.parent = None
            a.children = []

    def on_sub_tags_added(self, 
        node_id,
        entry, 
        next_node=None, 
        visited_nodes=None):
    
        visited_nodes = []

        for pointer in self.project.nodes[node_id].pointers:
            uid = node_id + pointer['id']
            if uid in visited_nodes:
                continue
            node_to_tag = pointer['id']
            if node_to_tag not in self.project.nodes:
                visited_nodes.append(uid)
                continue

            if uid not in visited_nodes and not self.project.nodes[node_to_tag].dynamic:
                self.project.nodes[node_to_tag].metadata.add_entry(
                    entry.keyname, 
                    entry.value, 
                    from_node=entry.from_node, 
                    recursive=entry.recursive)
                if node_to_tag not in self.project.nodes[entry.from_node].target_nodes:
                    self.project.nodes[entry.from_node].target_nodes.append(node_to_tag)

            visited_nodes.append(uid)        
            
            if entry.recursive:
                self.on_sub_tags_added(
                    pointer['id'],
                    entry,
                    next_node=node_to_tag, 
                    visited_nodes=visited_nodes)
