from anytree import Node, RenderTree, PreOrderIter
from anytree.render import ContStyle
from .dynamic_output import DynamicOutput
import datetime

"""
Tree building
"""
def _set_tree_elements(self, filename):
    """ Builds tree elements within the file's nodes, after the file is parsed."""

    parsed_items = self.files[filename].parsed_items
    positions = sorted(parsed_items)

    for index, position in enumerate(positions):

        node = parsed_items[position]

        # parse each marker, positioning it within its parent node
        if node[:2] == '>>':
            inserted_node_id = node[2:]
            parent_node = self.get_node_id_from_position(filename,position)      
            alias_node = Node('ALIAS'+inserted_node_id)
            alias_node.parent = self.nodes[parent_node].tree_node
            self.files[filename].alias_nodes.append(alias_node)
            continue

        """
        in case this node begins the file and is an an inline node,
        set the inline node's parent as the root node manually.
        """
        if position == 0 and parsed_items[0] == '{':
            self.nodes[node].tree_node.parent = self.nodes[root_node_id].tree_node
            continue
        
        start_of_node = self.nodes[node].ranges[0][0]
        if start_of_node == 0 and self.nodes[node].compact:
            parent = self.files[filename].root_nodes[0]
        else:
            if not self.nodes[node].compact:
                parent = self.get_node_id_from_position(filename, start_of_node - 1)
            else:
                parent = self.get_node_id_from_position(filename, start_of_node - 2)
        if parent:
            self.nodes[node].tree_node.parent = self.nodes[parent].tree_node

def _tree_node_is_excluded(self, tree_node, excluded_nodes):

    node_id = tree_node.name[-3:]

    if node_id in excluded_nodes:
        return True

    if node_id not in self.nodes:
        return True

    for ancestor in self.nodes[node_id].tree_node.ancestors:
        if ancestor.name[-3:] in excluded_nodes:
            return True

    return False

def has_aliases(self, start_point):
    alias_nodes = []
    leaves = start_point.leaves  

    for leaf in leaves:
        ancestors = [a.name for a in leaf.ancestors]
        if 'ALIAS' in leaf.name and leaf.name[-3:] in self.nodes and self.nodes[leaf.name[-3:]].tree_node.children:
            if leaf.name[-3:] not in ancestors:
                alias_nodes.append(leaf)
            else:
                leaf.name = '! RECURSION - (from alias) : '+ self.nodes[leaf.name[-3:]].title + ' >'+leaf.name[-3:]

    return alias_nodes

def show_tree_from(self, 
                   node_id,
                   dynamic_definition,
                   exclude=None,
                   from_root_of=False):

    if node_id not in self.nodes:
        self._log_item(root_node_id + ' is not in the project')
        return None
   
    start_point = self.nodes[node_id].tree_node
    if from_root_of == True:
        start_point = self.nodes[node_id].tree_node.root

    alias_nodes = self.has_aliases(start_point)

    while alias_nodes:  
        for leaf in alias_nodes:
            if leaf.name[:5] == 'ALIAS':
                node_id = leaf.name[-3:]
                new_tree = self.duplicate_tree(self.nodes[node_id].tree_node, leaf)            
                leaf.children = new_tree.children
        alias_nodes = self.has_aliases(start_point)
 
    tree_render = ''
    for pre, _, this_node in RenderTree(
            start_point, 
            style=ContStyle, 
            maxlevel=dynamic_definition.depth):

        if self._tree_node_is_excluded(this_node, exclude):
            continue

        if this_node.name[:11] == '! RECURSION':
            tree_render += "%s%s" % (pre, this_node.name + '\n')    
            continue

        if this_node.name[:5] == 'ALIAS':
            urtext_node = self.nodes[this_node.name[-3:]]
        else:
            urtext_node = self.nodes[this_node.name]
        
        next_content = DynamicOutput(dynamic_definition.show)
       
        if next_content.needs_title:
            next_content.title = urtext_node.title
       
        if next_content.needs_link:
            link = []
            if urtext_node.parent_project not in [self.title, self.path]:
                link.extend(['{"',this_node.parent_project,'"}'])
            else:
                link.append('>')
            link.append(str(urtext_node.id))
            next_content.link = ''.join(link)

        if next_content.needs_date:
            next_content.date = urtext_node.get_date(format_string = self.settings['timestamp_format'])

        if next_content.needs_meta:
            next_content.meta = urtext_node.consolidate_metadata(separator=':')

        if next_content.needs_contents: 
            next_content.contents = urtext_node.content_only().strip('\n').strip()

        if next_content.needs_last_accessed: 
            t = datetime.datetime.utcfromtimestamp(urtext_node.metadata.get_first_value('_last_accessed'))
            next_content.last_accessed = t.strftime(self.settings['timestamp_format'])

        for meta_key in next_content.needs_other_format_keys:
            values = urtext_node.metadata.get_values(meta_key, substitute_timestamp=True)
            replacement = ''
            if values and isinstance(values,list):
                replacement = ' | '.join(values)
            next_content.other_format_keys[meta_key] = replacement

        tree_render += "%s%s" % (pre, next_content.output())

    return tree_render

def duplicate_tree(self, original_node, leaf):

    new_root = Node(original_node.name)
    ancestors = [ancestor.name[-3:] for ancestor in leaf.ancestors]
    ancestors.extend([ancestor.name[-3:] for ancestor in original_node.ancestors])
    ancestors.append(leaf.name[-3:])
    ancestors.append(original_node.root.name[-3:])
    ancestors.append(original_node.name[-3:])

    # iterate immediate children only
    all_nodes = PreOrderIter(original_node, maxlevel=2)  

    for node in all_nodes: 
 
        if 'ALIAS' in node.name:            
            node_id = node.name[-3:] 
            if node_id not in ancestors:
                if node_id in self.nodes:
                    new_node = Node(node.name)
                    new_node.parent = new_root
                else:
                    new_node = Node('! (Missing Node) >'+node_id)
                    new_node.parent = new_root            
            else:
                new_node = Node('! RECURSION (from tree duplication) : '+ self.nodes[node_id].title + ' >'+node_id)
                new_node.parent = new_root  
            continue

        if node.parent == original_node:
            """ Recursively apply this function to children's children """
            new_node = self.duplicate_tree(node, leaf)
            new_node.parent = new_root

    return new_root

trees_functions=[
    show_tree_from, 
    _tree_node_is_excluded, 
    _set_tree_elements,
    duplicate_tree,
    has_aliases,

    ]
