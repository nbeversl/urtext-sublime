import os
import re

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from .node import UrtextNode
    from .utils import strip_backtick_escape, get_id_from_link
    import Urtext.urtext.syntax as syntax
else:
    from urtext.node import UrtextNode
    from urtext.utils import strip_backtick_escape, get_id_from_link
    import urtext.syntax as syntax

USER_DELETE_STRING = 'This message can be deleted.'

class UrtextBuffer:

    urtext_node = UrtextNode
    user_delete_string = USER_DELETE_STRING

    def __init__(self, project):
        
        self.nodes = []
        self.root_node = None
        self.alias_nodes = [] #todo should be in tree extension
        self.messages = []
        self.project = project
        self.meta_to_node = []

    def lex_and_parse(self, contents):
        self.contents = contents
        symbols = self.lex(contents)
        self.parse(contents, symbols)
        self.file_length = len(contents)
        self.propagate_timestamps(self.root_node)

    def lex(self, contents, start_position=0):
       
        symbols = {}
        embedded_syntaxes = []
        contents = strip_backtick_escape(contents)

        for match in syntax.embedded_syntax_c.finditer(contents):
            embedded_syntaxes.append([match.start(), match.end()])
        for symbol, symbol_type in syntax.compiled_symbols.items():
            for match in symbol.finditer(contents):
                is_embedded = False
                for r in embedded_syntaxes:
                    if match.start() in range(r[0], r[1]):
                        is_embedded = True
                        break
                if is_embedded:
                    continue
                if symbol_type == 'meta_to_node':
                    self.meta_to_node.append(match)
                    continue
                symbols[match.span()[0] + start_position] = {}
                symbols[match.span()[0] + start_position]['type'] = symbol_type

                if symbol_type == 'pointer':
                    symbols[match.span()[0] + start_position]['contents'] = get_id_from_link(match.group())
                if symbol_type == 'compact_node':
                    symbols[match.span()[0] + start_position]['full_match'] = match.group()
                    symbols[match.span()[0] + start_position]['contents'] = match.group(2)
        
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
        if from_compact:
            unstripped_contents = re.sub(
                syntax.bullet, 
                '', 
                unstripped_contents)

        for position in sorted(symbols.keys()):

            if position < last_position: 
                # avoid processing wrapped nodes twice if inside compact
                continue

            # Allow node nesting arbitrarily deep
            nested_levels[nested] = [] if nested not in nested_levels else nested_levels[nested]
            pointers[nested] = [] if nested not in pointers else pointers[nested]

            if symbols[position]['type'] == 'pointer':
                pointers[nested].append({ 
                    'id' : symbols[position]['contents'],
                    'position' : position
                    })
                continue

            if symbols[position]['type'] == 'opening_wrapper':
                nested_levels[nested].append([last_position, position])
                nested += 1

            if not from_compact and symbols[position]['type'] == 'compact_node':
                nested_levels[nested].append([last_position, position])
                
                compact_symbols = self.lex(
                    symbols[position]['contents'], 
                    start_position=position)

                nested_levels, child_group, nested = self.parse(
                    symbols[position]['full_match'], 
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
                    self.messages.append(
                        'Removed stray closing wrapper at %s. ' % str(position))
                    contents = contents[:position] + contents[position + 1:]
                    self._set_file_contents(contents)
                    return self.lex_and_parse(contents)

                node = self.add_node(
                    nested_levels[nested],
                    nested, 
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
                if nested in nested_levels:
                    del nested_levels[nested]
                nested -= 1

            if symbols[position]['type'] == 'EOB':
                # handle closing of buffer
                nested_levels[nested].append([last_position, position])
                root_node = self.add_node(
                    nested_levels[nested],
                    nested,
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
        
        if not from_compact and nested >= 0:
            self.messages.append(
                'Appended closing bracket to close opening bracket at %s. %s'  % 
                ( str(position), self.user_delete_string) )
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
        nested,
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
            compact=compact,
            nested=nested)
        
        new_node.get_file_contents = self._get_file_contents
        new_node.set_file_contents = self._set_file_contents
        new_node.ranges = ranges
        self.nodes.append(new_node)
        if new_node.root_node:
            self.root_node = new_node
        return new_node

    def _get_file_contents(self):
          return self.contents
          
    def _set_file_contents(self, contents):
          return

    def get_ordered_nodes(self):
        return sorted( 
            list(self.nodes),
            key=lambda node :  node.start_position())

    def propagate_timestamps(self, start_node):
        oldest_timestamp = start_node.metadata.get_oldest_timestamp()
        if oldest_timestamp:
            for child in start_node.children:
                child_oldest_timestamp = child.metadata.get_oldest_timestamp()
                if not child_oldest_timestamp:
                    child.metadata.add_entry(
                        'inline_timestamp', 
                        oldest_timestamp.wrapped_string,
                        from_node=start_node.title)
                    child.metadata.add_system_keys()
                self.propagate_timestamps(child)

    def update_node_contents(self, node_id, replacement_text):
        node = None
        for node in self.nodes:
            if node.id == node_id:
                break
        if node:
            self.project.run_editor_method(
                'replace',
                filename=self.project.nodes[node_id].filename,
                start=node.start_position(),
                end=node.end_position(),
                replacement_text=replacement_text
                )

    def log_error(self, message, position):

        self.nodes = {}
        self.root_node = None
        self.file_length = 0
        self.messages.append(message +' at position '+ str(position))

        print(''.join([ 
                message, ' in >f', self.filename, ' at position ',
            str(position)]))