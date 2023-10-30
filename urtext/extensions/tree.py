import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.anytree import Node
else:
    from anytree import Node

class UrtextAnyTree:

    name = ["TREE_EXTENSION"]

    def on_file_added(self, filename):
        for node in self.project.files[filename].nodes:
            node.tree_node = Node(node.id)
            node.tree_node.position = self.project.nodes[node.id].start_position
        self.project.files[filename].alias_nodes = []
        for node in self.project.files[filename].nodes:
            for pointer in node.pointers:
                alias_node = Node('ALIA$'+pointer['id']) # anytree Node, not UrtextNode 
                alias_node.position = pointer['position']
                alias_node.parent = node.tree_node
                self.project.files[filename].alias_nodes.append(alias_node)
            if node.parent and node.parent in self.project.files[filename].nodes:
                node.tree_node.parent = node.parent.tree_node

    def on_node_id_changed(self, old_node_id, new_node_id):
        if new_node_id in self.project.nodes:
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
                    entry.meta_values,
                    self.project.nodes[node_to_tag],
                    from_node=entry.from_node, 
                    tag_descendants=entry.tag_descendants)
                if node_to_tag not in self.project.nodes[entry.from_node].target_nodes:
                    self.project.nodes[entry.from_node].target_nodes.append(node_to_tag)

            visited_nodes.append(uid)        
            
            if entry.tag_descendants:
                self.on_sub_tags_added(
                    pointer['id'],
                    entry,
                    next_node=node_to_tag, 
                    visited_nodes=visited_nodes)

urtext_extensions = [UrtextAnyTree]
