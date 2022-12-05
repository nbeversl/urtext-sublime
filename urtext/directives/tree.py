import datetime
import os

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.anytree import Node, RenderTree, PreOrderIter
    from Urtext.anytree.render import ContStyle
    from ..dynamic_output import DynamicOutput
    from ..timestamp import UrtextTimestamp
    from ..directive import UrtextDirective
else:
    from anytree import Node, RenderTree, PreOrderIter
    from anytree.render import ContStyle
    from urtext.dynamic_output import DynamicOutput
    from urtext.timestamp import UrtextTimestamp
    from urtext.directive import UrtextDirective

"""
Tree
"""

class Tree(UrtextDirective):

    phase = 310
    
    def __init__(self, project):
        super().__init__(project)
        self.depth = 1

    def dynamic_output(self, start_point, exclude=None):
        
        exclude=self.dynamic_definition.excluded_nodes
        from_root_of=False

        if self.have_flags('*'):
            self.depth = 999999
        
        start_point = start_point.tree_node
        if from_root_of == True:
            start_point = project.nodes[node_id].tree_node.root

        alias_nodes = self._has_aliases(start_point)

        while alias_nodes:  
            for leaf in alias_nodes:
                if leaf.name[:5] == 'ALIAS':
                    node_id = leaf.name[5:]
                    new_tree = self.duplicate_tree(self.project.nodes[node_id].tree_node, leaf)            
                    leaf.children = new_tree.children
            alias_nodes = self._has_aliases(start_point)
     
        tree_render = ''
                
        level = 0
        for pre, _, this_node in RenderTree(
                start_point, 
                style=ContStyle, 
                maxlevel=self.depth):

            indented_pre = '  ' + pre

            if self._tree_node_is_excluded(this_node, exclude):
                this_node.children = []
                continue

            if not this_node.name in self.project.nodes:
                if this_node.name[:5] == 'ALIAS' and this_node.name[5:] not in self.project.nodes:
                    tree_render += "%s%s" % (pre, this_node.name + ' NOT IN PROJECT (DEBUGGING)\n')    
                    continue

            if this_node.name[:11] == '! RECURSION':
                tree_render += "%s%s" % (pre, this_node.name + '\n')    
                continue

            if this_node.name[:5] == 'ALIAS':
                urtext_node = self.project.nodes[this_node.name[5:]]
            else:
                urtext_node = self.project.nodes[this_node.name]
            
            next_content = DynamicOutput(self.dynamic_definition.show, self.project.settings)
          
            if next_content.needs_title:
                next_content.title = urtext_node.title
           
            if next_content.needs_link:
                link = []
                if urtext_node.parent_project not in [self.project.title, self.project.path]:
                    link.extend(['=>"',urtext_node.parent_project,'"'])
                else:
                    link.append('| ')
                link.append(str(urtext_node.id + ' >'))
                next_content.link = ''.join(link)

            if next_content.needs_date:
                next_content.date = urtext_node.get_date(self.project.settings['node_date_keyname']).strftime(self.project.settings['timestamp_format'])

            if next_content.needs_meta:
                next_content.meta = urtext_node.consolidate_metadata(separator=':')

            if next_content.needs_contents: 
                next_content.contents = urtext_node.content_only().strip('\n').strip()

            for meta_key in next_content.needs_other_format_keys:
                
                k, ext = meta_key, ''
                if '.' in meta_key:
                    k, ext = meta_key.split('.')
                replacement = ''
                if ext in ['timestamp','timestamps'] or k in self.project.settings['use_timestamp']:  
                    timestamps = urtext_node.metadata.get_values(k, use_timestamp=True)
                    if timestamps:
                        if ext == 'timestamp':
                            replacement = timestamps[0].string
                        else:
                            replacement = ' - '.join([t.string for t in timestamps])
                else:
                    values = [v for v in urtext_node.metadata.get_values(k) if v ]
                    replacement = ' - '.join(values)
                next_content.other_format_keys[meta_key] = replacement

            if level == 0:
                prefix = pre
            else:
                prefix = indented_pre

            tree_render += "%s%s" % (prefix, next_content.output())

            level += 1

        return tree_render

    def on_project_init(self):        
        return
        
    
    def _tree_node_is_excluded(self, tree_node, excluded_nodes):

        if not excluded_nodes:
            return False

        node_id = tree_node.name

        if node_id in excluded_nodes:
            return True

        if node_id not in self.project.nodes:
            return True

        for ancestor in self.project.nodes[node_id].tree_node.ancestors:
            if ancestor.name in excluded_nodes:
                return True

        return False

    def _has_aliases(self, start_point):
        
        alias_nodes = []
        leaves = start_point.leaves  

        for leaf in leaves:
            ancestors = [a.name for a in leaf.ancestors]
            if 'ALIAS' in leaf.name and leaf.name[5:] in self.project.nodes and self.project.nodes[leaf.name[5:]].tree_node.children:
                if leaf.name not in ancestors:
                    alias_nodes.append(leaf)
                else:
                    leaf.name = '! RECURSION - (from alias) : '+ self.project.nodes[leaf.name].get_title() + ' >'+leaf.name

        return alias_nodes

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
     
            if 'ALIAS' in node.name:            
                node_id = node.name[5:]
                if node_id not in ancestors:
                    if node_id in self.project.nodes:
                        new_node = Node(node.name)
                        new_node.parent = new_root
                    else:
                        new_node = Node('! (Missing Node) >'+node_id)
                        new_node.parent = new_root            
                else:
                    new_node = Node('! RECURSION (from tree duplication) : '+ self.project.nodes[node_id].get_title() + ' >'+node_id)
                    new_node.parent = new_root  
                continue

            if node.parent == original_node:
                """ Recursively apply this function to children's children """
                new_node = self.duplicate_tree(node, leaf)
                new_node.parent = new_root

        return new_root

