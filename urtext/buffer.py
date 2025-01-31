import re
from urtext.node import UrtextNode
from urtext.utils import strip_backtick_escape, get_id_from_link
import urtext.syntax as syntax

class UrtextBuffer:

    urtext_node = UrtextNode

    def __init__(self, project, filename, contents):
        self.contents = contents
        self.messages = []
        self.project = project
        self.identifier = None
        self.meta_to_node = []
        self.has_errors = False
        self.filename = filename
        self.nodes = []
        self.allocated_ids = []
        self.root_node = None
        self.__clear_messages()
        self._lex_and_parse()
        if not self.root_node:
            self._log_error('No root node', 0)
    
    def _lex_and_parse(self):
        self.nodes = []
        self.root_node = None
        self.has_errors = False
        self.messages = []
        self.meta_to_node = []
        symbols = self._lex(self._get_contents())
        self._parse(self._get_contents(), symbols)
        for node in self.nodes:
            node.buffer = self
            node.filename = self.filename
        self._assign_parents(self.root_node)
        self.allocated_ids = []
        self._resolve_untitled_nodes()
        self._resolve_duplicate_ids()

    def _lex(self, contents, start_position=0):
        symbols = {}
        embedded_syntaxes = []
        ranges, contents = strip_backtick_escape(contents)

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

                if symbol_type == 'pointer':
                    symbols[match.start() + start_position] = {}
                    symbols[match.start() + start_position]['contents'] = get_id_from_link(match.group())
                    symbols[match.start() + start_position]['type'] = symbol_type
                elif symbol_type == 'compact_node':
                    symbols[match.start() + start_position + len(match.group(1))] = {}
                    symbols[match.start() + start_position + len(match.group(1))]['type'] = symbol_type
                    symbols[match.start() + start_position + len(match.group(1))]['contents'] = match.group(3)
                else:
                    symbols[match.start() + start_position] = {}
                    symbols[match.start() + start_position]['type'] = symbol_type

        symbols[len(contents) + start_position] = { 'type': 'EOB' }
        return symbols

    def _parse(self, 
        contents,
        symbols,
        nested_levels={},
        nested=0,
        child_group={},
        start_position=0,
        from_compact=False):
 
        ranges, unstripped_contents = strip_backtick_escape(contents)
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
                pointers[nested].append({ 
                    'id' : symbols[position]['contents'],
                    'position' : position
                    })
                continue

            elif symbols[position]['type'] == 'opening_wrapper':
                if from_compact:
                    nested_levels[nested].append([last_position-1, position-1])
                else:
                    if position == 0:
                        nested_levels[nested].append([0, 0])
                        nested_levels[nested] = []
                    else:
                        if position == last_position:
                            nested += 1
                            last_position += 1
                            #consecutive bracket nodes, i.e. }{
                            continue
                        nested_levels[nested].append([last_position, position])
                position += 1 #wrappers exist outside range
                nested += 1

            elif not from_compact and symbols[position]['type'] == 'compact_node':
                if position > 0:
                    nested_levels[nested].append([last_position, position-1])
                else:
                    nested_levels[nested].append([0, 0])

                compact_symbols = self._lex(
                    symbols[position]['contents'], 
                    start_position=position+1)

                nested_levels, child_group, nested = self._parse(
                    symbols[position]['contents'],
                    compact_symbols,
                    nested_levels=nested_levels,
                    nested=nested+1,
                    child_group=child_group,
                    start_position=position+1,
                    from_compact=True)
               
                r = position + len(symbols[position]['contents'])
                if r in symbols and symbols[r]['type'] == 'EOB':
                    nested_levels[nested].append([r,r])
                    last_position = r
                    continue
                last_position = position + 1 + len(symbols[position]['contents'])
                continue
 
            elif symbols[position]['type'] == 'closing_wrapper':
                if from_compact:
                    nested_levels[nested].append([last_position-1, position-1])
                else:
                    nested_levels[nested].append([last_position, position])
                if nested <= 0:
                    contents = contents[:position] + contents[position + 1:]
                    return self.set_buffer_contents(contents, clear_messages=False)

                position += 1 #wrappers exist outside range
                node = self.add_node(
                    nested_levels[nested],
                    nested,
                    contents,
                    start_position=start_position)

                if nested + 1 in child_group:
                    for child in child_group[nested+1]:
                        child.parent = node
                    node.children = child_group[nested+1]
                    del child_group[nested+1]

                if nested in pointers:
                    node.pointers = pointers[nested]
                    del pointers[nested]
                
                child_group[nested] = child_group.get(nested, [])
                child_group[nested].append(node)
                if nested in nested_levels:
                    del nested_levels[nested]
                nested -= 1

            elif symbols[position]['type'] == 'EOB':
                # handle closing of buffer
                nested_levels[nested].append([last_position, position])
                root_node = self.add_node(
                    nested_levels[nested],
                    nested,
                    unstripped_contents,
                    root=True if not from_compact else False,
                    compact=from_compact,
                    start_position=start_position)

                #TODO refactor?
                if nested + 1 in child_group:
                    for child in child_group[nested+1]:
                        child.parent = root_node
                    root_node.children = child_group[nested+1]
                    del child_group[nested + 1]

                if nested in pointers:
                    root_node.pointers = pointers[nested]
                    del pointers[nested]

                child_group[nested] = child_group.get(nested, [])
                child_group[nested].append(root_node)
                if nested in nested_levels:
                    del nested_levels[nested]
                nested -= 1
                continue

            last_position = position
        
        if not from_compact and nested >= 0:
            contents = ''.join([contents[:position],
                ' ',
                syntax.node_closing_wrapper,
                ' ',
                contents[position:]])
            return self.set_buffer_contents(contents)

        for node in self.nodes:
            node.filename = self.filename
            node.file = self

        for match in self.meta_to_node:
            # TODO optimize
            for node in self.nodes:
                for r in node.ranges:
                    if match.span()[1] in r:
                        node.is_meta = True
                        node.meta_key = match.group()[:-3]

        return nested_levels, child_group, nested

    def add_node(self, 
        ranges, 
        nested,
        contents,
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
        
        new_node.ranges = ranges
        new_node.start_position = ranges[0][0]
        new_node.end_position = ranges[-1][1]

        self.nodes.append(new_node)
        if new_node.root_node:
            self.root_node = new_node
        return new_node

    def _get_contents(self):
        return self.contents

    def set_buffer_contents(self, 
        new_contents,
        clear_messages=True):

        self.contents = new_contents
        if clear_messages:
            self.__clear_messages()
        self._lex_and_parse()

    def write_buffer_contents(self, run_hook=None):
        self.project.run_editor_method(
            'set_buffer',
            self.filename,
            self.contents,
            identifier=self.identifier)

    def write_buffer_messages(self, messages=None):
        if not messages and not self.messages:
            return False
        if messages:
            self.messages = messages
        timestamp = self.project.timestamp(as_string=True)
        
        top_message = ''.join([
            syntax.urtext_message_opening_wrapper,
            ' ',
            '\n'.join([m['top_message'] for m in self.messages]),
            ' ', timestamp, ' ',
            syntax.urtext_message_closing_wrapper,
            '\n'
            ])

        current_messages = self.__get_messages()
        messaged_contents = self._get_contents()
        for m in current_messages:
            messaged_contents = messaged_contents.replace(m.group(), 
                ''.join([
                    m.group()[:2],
                    'X',
                    m.group()[3:],                   
                    ]))

        sorted_messages = sorted(self.messages, key=lambda m: m['position'])
        insert_index = 0
        for m in sorted_messages:
            
            insert_position = m['position'] + insert_index
            messaged_contents = ''.join([
                messaged_contents[:insert_position],
                syntax.urtext_message_opening_wrapper,
                ' ',
                m['position_message'],
                ' ',
                syntax.urtext_message_closing_wrapper,
                messaged_contents[insert_position:],
                ])
            insert_index += len(m['position_message']) + 6
        
        for match in syntax.invalidated_messages_c.finditer(messaged_contents):
            messaged_contents = messaged_contents.replace(match.group(), '')
        new_contents = ''.join([
            top_message,
            messaged_contents,
            ])
        self.messages = []
        self.set_buffer_contents(new_contents, clear_messages=False)
        self.write_buffer_contents()

    def _resolve_untitled_nodes(self):        
        for node in list([n for n in self.nodes if n.title == '(untitled)']):
            resolution = node.resolve_id(allocated_ids=self.allocated_ids)
            if not resolution['resolved_id']:
                message = {
                    'top_message': ''.join([
                                'Dropping (untitled) ID at position ',
                                str(node.start_position),
                                '. ',
                                resolution['reason'],
                                ' ',
                            ]),
                    'position_message': 'Dropped (untitled), ' + resolution['reason'] ,
                    'position' : node.start_position
                    }
                node.has_errors = True
                self.project.log_item(self.filename, message)
                self.messages.append(message)
                self.nodes = [n for n in self.nodes if n.title != node.title]
            else:
                node.id = resolution['resolved_id']
                self.allocated_ids.append(node.id)
        if self.messages:
            self.has_errors = True
        
    def _resolve_duplicate_ids(self):
        own_node_ids = [n.id for n in self.nodes]
        nodes_to_resolve = [n for n in self.nodes if own_node_ids.count(n.id) > 1]
        for n in nodes_to_resolve:
            resolution = n.resolve_id(allocated_ids=self.allocated_ids)
            if not resolution['resolved_id']:
                message = {
                    'top_message' :''.join([
                                'Dropping duplicate node"',
                                n.id,
                                '"',
                                ' at position ',
                                str(n.start_position),
                                '; ',
                                resolution['reason']
                            ]),
                    'position_message': resolution['reason'],
                    'position': n.start_position
                    }
                self.project.log_item(self.filename, message)
                self.messages.append(message)
                n.has_errors = True
                self.nodes = [node for node in self.nodes if node.title != n.title]
            else:
                n.id = resolution['resolved_id']
                self.allocated_ids.append(n.id)
       
    def __get_messages(self):
        return [m for m in syntax.urtext_messages_c.finditer(self._get_contents())]

    def __clear_messages(self):
        messages = self.__get_messages()
        if messages:
            original_contents = self._get_contents()
            cleared_contents = original_contents
            for match in messages:
                cleared_contents = cleared_contents.replace(match.group(),'')
            if cleared_contents != original_contents:
                self.set_buffer_contents(cleared_contents, clear_messages=False)

    def get_ordered_nodes(self):
        return sorted( 
            list(self.nodes),
            key=lambda node : node.start_position)

    def _assign_parents(self, start_node):
        for child in start_node.children:
            child.parent = start_node
            self._assign_parents(child)

    def get_node_from_position(self, position):
        for node in self.nodes:
            for r in node.ranges:       
                if position in range(r[0],r[1]+1): # +1 in case the cursor is in the last position of the node.
                    return node

    def node_ids(self):
        return [n.id for n in self.nodes]

    def get_node(self, node_id):
        for n in self.nodes:
            if n.id == node_id:
                return n

    def _log_error(self, message, position):
        self.nodes = {}
        self.root_node = None
        message = message +' at position '+ str(position)
        if message not in self.messages:
            self.messages.append()

        