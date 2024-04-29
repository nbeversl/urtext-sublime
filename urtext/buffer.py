import re
from urtext.node import UrtextNode
from urtext.utils import strip_backtick_escape, get_id_from_link
import urtext.syntax as syntax
from urtext.metadata import MetadataValue

USER_DELETE_STRING = 'This message can be deleted.'

class UrtextBuffer:

    urtext_node = UrtextNode
    user_delete_string = USER_DELETE_STRING

    def __init__(self, project, filename, contents):
        self.contents = contents
        self.messages = []
        self.project = project
        self.meta_to_node = []
        self.has_errors = False
        self.filename = filename
        self.nodes = []
        self.root_node = None
        self._clear_messages()
        self._lex_and_parse()
        if not self.root_node:
            print('LOGGING NO ROOT NODE (DEBUGGING, buffer)')
            self._log_error('No root node', 0)
    
    def _lex_and_parse(self):
        self.nodes = []
        self.root_node = None
        symbols = self._lex(self._get_contents())
        self._parse(self._get_contents(), symbols)
        self.propagate_timestamps(self.root_node)
        for node in self.nodes:
            node.buffer = self
            node.filename = self.filename
        self._assign_parents(self.root_node)

    def _lex(self, contents, start_position=0):
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
                        nested += 1 
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
                    self._set_buffer_contents(contents)
                    return self._lex_and_parse()

                position += 1 #wrappers exist outside range
                node = self.add_node(
                    nested_levels[nested],
                    nested,
                    unstripped_contents,
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
            self._set_buffer_contents(contents)
            return self._lex_and_parse()

        for node in self.nodes:
            node.filename =self.filename
            node.file = self

        for match in self.meta_to_node:
            # TODO optimize
            for node in self.nodes:
                for r in node.ranges:
                    if match.span()[1] in r:
                        node.is_meta = True

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

    def _set_buffer_contents(self, 
        new_contents,
        re_parse=True,
        run_hook=False,
        update_buffer=False):

        self.contents = new_contents
        if re_parse:
            self._clear_messages()
            self._lex_and_parse()
            self.project._parse_buffer(self)
            # self.write_buffer_messages()
        if update_buffer:
            self.__update_buffer_contents_from_buffer_obj()

    def __update_buffer_contents_from_buffer_obj(self):
        self.project.run_editor_method(
            'set_buffer',
            self.filename,
            self.contents)

    def write_buffer_messages(self, messages=None):
        if not messages and not self.messages:
            return False
        if messages:
            self.messages = messages
        self._clear_messages()
        new_contents = self._get_contents()
        timestamp = self.project.timestamp(as_string=True)
        messages = ''.join([ 
            syntax.urtext_message_opening_wrapper,
            ' ',
            '\n'.join(self.messages),
            timestamp,
            ' ',
            syntax.urtext_message_closing_wrapper,
            '\n'
            ])

        message_length = len(messages)
        
        for n in re.finditer('position \d{1,10}', messages):
            old_n = int(n.group().replace('position ',''))
            new_n = old_n + message_length
            messages = messages.replace(str(old_n), str(new_n))
            
        new_contents = ''.join([
            messages,
            new_contents,
            ])

        self._set_buffer_contents(new_contents, re_parse=False, update_buffer=True)
        
    def _clear_messages(self):
        original_contents = self._get_contents()
        if original_contents:
            cleared_contents = original_contents
            for match in syntax.urtext_messages_c.finditer(cleared_contents):
                if self.user_delete_string not in cleared_contents:
                    cleared_contents = cleared_contents.replace(match.group(),'')
            if cleared_contents != original_contents:
                self._set_buffer_contents(cleared_contents, re_parse=False)
                return True
        return False

    def get_ordered_nodes(self):
        return sorted( 
            list(self.nodes),
            key=lambda node : node.start_position)

    def _insert_contents(self, inserted_contents, position):
        self._set_buffer_contents(''.join([
            self.contents[:position],
            inserted_contents,
            self.contents[position:],
            ]))

    def _replace_contents(self, inserted_contents, range):
        self._set_buffer_contents(''.join([
            self.contents[:range[0]],
            inserted_contents,
            self.contents[range[1]:],
            ]))

    def propagate_timestamps(self, start_node):
        oldest_timestamp = start_node.metadata.get_oldest_timestamp()
        if oldest_timestamp:
            for child in start_node.children:
                child_oldest_timestamp = child.metadata.get_oldest_timestamp()
                if not child_oldest_timestamp:
                    child.metadata.add_entry(
                        'inline_timestamp',
                        [MetadataValue(oldest_timestamp.wrapped_string)],
                        child,
                        from_node=start_node.id,
                        )
                    child.metadata.add_system_keys()
                self.propagate_timestamps(child)

    def _assign_parents(self, start_node):
        for child in start_node.children:
            child.parent = start_node
            self._assign_parents(child)

    def get_node_id_from_position(self, position):
        for node in self.nodes:
            for r in node.ranges:           
                if position in range(r[0],r[1]+1): # +1 in case the cursor is in the last position of the node.
                    return node.id


    def _log_error(self, message, position):
        self.nodes = {}
        self.root_node = None
        message = message +' at position '+ str(position)
        if message not in messages:
            self.messages.append()

        # print(''.join([ 
        #         message, ' in >f', self.filename, ' at position ',
        #     str(position)]))