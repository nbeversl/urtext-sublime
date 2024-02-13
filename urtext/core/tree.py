import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.anytree import Node, RenderTree, PreOrderIter
    from Urtext.anytree.render import ContStyle
    from Urtext.urtext.dynamic_output import DynamicOutput
else:
    from anytree import Node, RenderTree, PreOrderIter
    from anytree.render import ContStyle
    from urtext.dynamic_output import DynamicOutput

class UrtextAnyTree:

    name = ["TREE_EXTENSION"]

    def __init__(self, project):
        super().__init__(project)
        self.treed_nodes = []

    def on_file_added(self, filename):
        for node in self.project.files[filename].nodes:
            node.tree_node = Node(node.id)
            node.tree_node.position = self.project.nodes[node.id].start_position
            self.treed_nodes.append(node)
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
            self.project.nodes[new_node_id].tree_node = Node(new_node_id)

    def on_file_dropped(self, filename):
        for node in self.project.files[filename].nodes:
            if node in self.treed_nodes:
                self.treed_nodes.remove(node)
                node.tree_node.parent = None
                del node.tree_node
        for a in self.project.files[filename].alias_nodes:
            a.parent = None
            a.children = []

    def on_sub_tags_added(self, 
        node_id,
        entry, 
        next_node=None, 
        visited_nodes=[]):
    
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
                if node_to_tag not in entry.from_node.target_nodes:
                    entry.from_node.target_nodes.append(node_to_tag)

            visited_nodes.append(uid)        
            
            if entry.tag_descendants:
                self.on_sub_tags_added(
                    pointer['id'],
                    entry,
                    next_node=node_to_tag, 
                    visited_nodes=visited_nodes)


class TreeDirective:

    phase = 310
    name = ['TREE']
    
    def __init__(self, project):
        super().__init__(project)
        self.depth = 1

    def dynamic_output(self, start_points):
        if self.have_flags('*'):
            self.depth = float('inf')
        else:
            try:
                self.depth = int(self.argument_string)
            except:
                self.depth = 1

        tree_render = ''
        for start_point in start_points:
            start_point = start_point.tree_node

            pointers = self._has_pointers(start_point)
            while pointers:  
                for leaf in pointers:
                    if leaf.name[:5] == 'ALIA$':
                        node_id = leaf.name[5:]
                        new_tree = self.duplicate_tree(
                            self.project.nodes[node_id].tree_node,
                            leaf)            
                        leaf.children = new_tree.children
                pointers = self._has_pointers(start_point)
         
            level = 0
            for pre, _, this_node in RenderTree(
                    start_point, 
                    style=ContStyle, 
                    maxlevel=self.depth):

                if self._tree_node_is_excluded(this_node):
                    this_node.children = []
                    continue

                # handle pointers
                if this_node.name[:5] == 'ALIA$':
                    alias_node_id = this_node.name[5:]
                    if alias_node_id not in self.project.nodes:
                        tree_render += "%s%s" % (
                            indented_pre, 
                            ''.join([
                                self.syntax.missing_link_opening_wrapper,
                                alias_node_id,
                                self.syntax.link_closing_wrapper,
                                '\n']
                                ))
                        continue
                    else:
                        urtext_node = self.project.nodes[alias_node_id]
                else:

                    if this_node.name[:11] == '! RECURSION':
                        tree_render += "%s%s" % (pre, this_node.name + '\n')    
                        continue
                        
                    if this_node.name not in self.project.nodes:
                        tree_render += "%s | %s > <! not in project !>)\n" % (pre, this_node.name)    
                        continue

                    urtext_node = self.project.nodes[this_node.name]
                
                #TODO implement better ?
                #currently mixes nodes with pointers
                this_node.children = sorted(
                    this_node.children,
                    key=lambda n: self.project.nodes[n.name].start_position if (
                        n.name in self.project.nodes ) else n.position)

                indented_pre = '  ' + pre

                next_content = DynamicOutput(
                    self.dynamic_definition.show, 
                    self.project.settings)

                next_content.title = urtext_node.title
               
                link = []
                #TODO refactor
                if urtext_node.project.settings['project_title'] not in [self.project.settings['paths']] and urtext_node.project.settings['project_title'] != self.project.settings['project_title']:
                    link.extend(['=>"', urtext_node.project.settings['project_title'],'"'])
                else:
                    link.append(self.syntax.link_opening_wrapper)
                link.append(urtext_node.id + self.syntax.link_closing_wrapper)
                next_content.link = ''.join(link)

                next_content.pointer = ''.join([
                    self.syntax.link_opening_wrapper,
                    urtext_node.id,
                    self.syntax.pointer_closing_wrapper
                    ])

                next_content.date = urtext_node.get_date(
                    self.project.settings[
                        'node_date_keyname']).strftime(
                            self.project.settings['timestamp_format'])

                next_content.meta = urtext_node.consolidate_metadata(separator=':')

                if next_content.needs_contents:
                    next_content.contents = urtext_node.stripped_contents

                for meta_key in next_content.needs_other_format_keys:
                    next_content.other_format_keys[
                        meta_key] = urtext_node.metadata.get_extended_values(
                            meta_key)

                if level == 0:
                    prefix = pre
                else:
                    prefix = indented_pre

                tree_render += "%s%s" % (prefix, next_content.output())

                level += 1

        return tree_render
        
    def _tree_node_is_excluded(self, tree_node):

        if tree_node.name in self.dynamic_definition.target_ids:
            return True

        if self.dynamic_definition.excluded_nodes:

            node_id = tree_node.name.replace('ALIA$','')
            if node_id in self.dynamic_definition.excluded_nodes:
                return True

            if node_id not in self.project.nodes:
                return True

            for ancestor in self.project.nodes[node_id].tree_node.ancestors:
                if ancestor.name in self.dynamic_definition.excluded_nodes:
                    return True

        return False

    def _has_pointers(self, start_point):
        
        pointers = []
        for leaf in start_point.leaves:
            ancestors = [a.name for a in leaf.ancestors]
            if 'ALIA$' in leaf.name:
                pointer_id = leaf.name[5:]
                if pointer_id in self.project.nodes and self.project.nodes[pointer_id].tree_node.children:
                    if leaf.name not in ancestors:
                        pointers.append(leaf)
                    else:
                        leaf.name = '! RECURSION - (from pointer) : '+ pointer_id + ' >'+leaf.name
        return pointers

    def duplicate_tree(self, original_node, leaf):

        new_root = Node(original_node.name)
        ancestors = [ancestor.name for ancestor in leaf.ancestors]
        ancestors.extend([ancestor.name for ancestor in original_node.ancestors])
        ancestors.append(leaf.name)
        ancestors.append(original_node.root.name)
        ancestors.append(original_node.name)

        # iterate immediate children only
        all_nodes = PreOrderIter(original_node, maxlevel=2)  

        for node in all_nodes: 
     
            if 'ALIA$' in node.name:    
                node_id = node.name[5:]
                if node_id not in ancestors:                
                    new_node = Node(node.name)
                    new_node.parent = new_root
                    new_node.position = node.position
                else:
                    new_node = Node('! RECURSION (from tree duplication) : '+ node_id + ' >')
                    new_node.parent = new_root
                    new_node.position = node.position
                    
                continue

            if node.parent == original_node:
                """ Recursively apply this function to children's children """
                new_node = self.duplicate_tree(node, leaf)
                new_node.parent = new_root

        return new_root

urtext_directives = TreeDirective
urtext_extensions = UrtextAnyTree
