import os
import re

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from .node import UrtextNode
    from .utils import strip_backtick_escape
    import Urtext.urtext.syntax as syntax
else:
    from urtext.node import UrtextNode
    from urtext.utils import strip_backtick_escape
    import urtext.syntax as syntax

class UrtextBuffer:

    urtext_node = UrtextNode

    def __init__(self, project):
        
        self.nodes = {}
        self.node_tree = {}
        self.root_node = None
        self.alias_nodes = []
        self.parsed_items = {}
        self.messages = []     
        self.project = project
        self.meta_to_node = []

    def lex_and_parse(self, contents):
        self.contents = contents
        symbols = self.lex(contents)
        self.parse(contents, symbols)
        self.file_length = len(contents)
        self.propagate_timestamps(self.nodes[self.root_node])

    def lex(self, contents, start_position=0):
       
        symbols = {}

        contents = strip_backtick_escape(contents)
        for symbol, symbol_type in syntax.compiled_symbols.items():
            for match in symbol.finditer(contents):
                if symbol_type == 'meta_to_node':
                    self.meta_to_node.append(match)
                    continue
                symbols[match.span()[0] + start_position] = {}
                symbols[match.span()[0] + start_position]['type'] = symbol_type
                symbols[match.span()[0] + start_position]['length'] = len(match.group())                

                if symbol_type == 'pointer':
                    symbols[match.span()[0] + start_position]['contents'] = match.group(2)
                if symbol_type == 'compact_node':
                    symbols[match.span()[0] + start_position]['full_match'] = match.group()
                    symbols[match.span()[0] + start_position]['node_contents'] = match.group(2)

        ## Filter out Syntax Push and delete wrapper elements between them.
        push_syntax = 0
        to_remove = []

        for p in sorted(symbols.keys()):

            if symbols[p]['type'] == 'embedded_syntax_open' :
                to_remove.append(p)
                push_syntax += 1
                continue
            
            if symbols[p]['type'] == 'embedded_syntax_close':
                to_remove.append(p)
                push_syntax -= 1
                continue
            
            if push_syntax > 0:
                to_remove.append(p)

        for s in to_remove:
            del symbols[s]

        symbols[len(contents) + start_position] = { 'type': 'EOB' }
        return symbols

    def parse(self, 
        contents,
        symbols,
        nested_levels={},
        nested=0,
        child_group={},
        start_position=0,
        from_compact=False):
 
        unstripped_contents = strip_backtick_escape(contents)
        last_position = start_position
        pointers = {}

        for position in sorted(symbols.keys()):

            if position < last_position: 
                # avoid processing wrapped nodes twice if inside compact
                continue

            # Allow node nesting arbitrarily deep
            nested_levels[nested] = [] if nested not in nested_levels else nested_levels[nested]
            pointers[nested] = [] if nested not in pointers else pointers[nested]

            if symbols[position]['type'] == 'pointer':
                pointers[nested].append(symbols[position]['contents'])
                continue

            if symbols[position]['type'] == 'opening_wrapper':
                nested_levels[nested].append([last_position, position])
                nested += 1

            if not from_compact and symbols[position]['type'] == 'compact_node':
                nested_levels[nested].append([last_position, position])
                
                compact_symbols = self.lex(
                    symbols[position]['full_match'], 
                    start_position=position)

                nested_levels, child_group, nested = self.parse(
                    symbols[position]['node_contents'], 
                    compact_symbols,
                    nested_levels=nested_levels,
                    nested=nested + 1,
                    child_group=child_group,
                    start_position=position,
                    from_compact=True)

                last_position = position + len(symbols[position]['full_match'])
                continue
 
            if symbols[position]['type'] == 'closing_wrapper':
                nested_levels[nested].append([last_position , position])
    
                if nested <= 0:
                    self.messages.append('\n'.join([
                        'Removed stray closing wrapper at %s' % str(position),
                        'This message can be deleted.']))
                    contents = contents[:position] + contents[position + 1:]
                    self._set_file_contents(contents)
                    return self.lex_and_parse(contents)

                node = self.add_node(
                    nested_levels[nested], 
                    unstripped_contents,
                    position,
                    start_position=start_position)

                if nested + 1 in child_group:
                    for child in child_group[nested+1]:
                        child.parent = node
                    node.children = child_group[nested+1]
                    del child_group[nested+1]

                if nested in pointers:
                    node.pointers = pointers[nested]
                    del pointers[nested]
                
                child_group.setdefault(nested,[])
                child_group[nested].append(node)
                del nested_levels[nested]
                nested -= 1

            if symbols[position]['type'] == 'EOB':
                # handle closing of buffer
                nested_levels[nested].append([last_position, position])
                root_node = self.add_node(
                    nested_levels[nested], 
                    unstripped_contents,
                    position,
                    root=True if not from_compact else False,
                    compact=from_compact,
                    start_position=start_position)

                #TODO refactor
                if nested + 1 in child_group:
                    for child in child_group[nested+1]:
                        child.parent = root_node
                    root_node.children = child_group[nested+1]
                    del child_group[nested + 1]

                if nested in pointers:
                    root_node.pointers = pointers[nested]
                    del pointers[nested]

                child_group.setdefault(nested,[])
                child_group[nested].append(root_node)
                del nested_levels[nested]
                nested -= 1
                continue

            last_position = position
        
        if not from_compact and nested > 0:
            message = '\n'.join([
                'Appended closing bracket to close opening bracket at %s' % str(position),
                'This message can be deleted.'])
            self.messages.append(message)
            contents = ''.join([contents[:position],
                 ' ',
                 syntax.node_closing_wrapper,
                 ' ',
                 contents[position:]])
            self._set_file_contents(contents)
            return self.lex_and_parse(contents)

        return nested_levels, child_group, nested

    def add_node(self, 
        ranges, 
        contents,
        position,
        root=None,
        compact=False,
        start_position=0):

        # Build the node contents and construct the node
        node_contents = ''.join([
            contents[
                r[0] - start_position
                :
                r[1] - start_position ]
            for r in ranges])
        
        new_node = self.urtext_node(
            node_contents,
            self.project,
            root=root,
            compact=compact)
        
        new_node.get_file_contents = self._get_file_contents
        new_node.set_file_contents = self._set_file_contents

        self.nodes[new_node.id] = new_node   
        self.nodes[new_node.id].ranges = ranges
        if new_node.root_node:
            self.root_node = new_node.id
        self.parsed_items[ranges[0][0]] = new_node.id
        return new_node

    def _get_file_contents(self):
          return self.contents
          
    def _set_file_contents(self, contents):
          return

    def get_ordered_nodes(self):
        return sorted( 
            list(self.nodes.keys()),
            key=lambda node_id :  self.nodes[node_id].start_position())

    def propagate_timestamps(self, start_node):
        oldest_timestamp = start_node.metadata.get_oldest_timestamp()
        if oldest_timestamp:
            for child in start_node.children:
                child_oldest_timestamp = child.metadata.get_oldest_timestamp()
                if not child_oldest_timestamp:
                    child.metadata.add_entry('inline_timestamp', ''.join([
                        syntax.timestamp_opening_wrapper,
                        oldest_timestamp.string,
                        syntax.timestamp_closing_wrapper
                        ]),
                    from_node=start_node.title)
                    child.metadata.add_system_keys()
                self.propagate_timestamps(child)

    def log_error(self, message, position):

        self.nodes = {}
        self.parsed_items = {}
        self.root_node = None
        self.file_length = 0
        self.messages.append(message +' at position '+ str(position))

        print(''.join([ 
                message, ' in >f', self.filename, ' at position ',
            str(position)]))