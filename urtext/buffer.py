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

    def __init__(self, contents, project):
        
        self.nodes = {}
        self.root_nodes = []
        self.alias_nodes = []           
        self.parsed_items = {}
        self.messages = []        
        self.errors = False
        self.contents = contents
        self.filename = 'yyyyyyyyyyy'
        self.basename = 'yyyyyyyyyyy'
        self.project = project
        self.file_length = len(contents)
        symbols = self.lex(contents)
        self.parse(contents, symbols)
            
    def lex(self, contents, start_position=0):
       
        symbols = {}

        contents = strip_backtick_escape(contents)
        for symbol, symbol_type in syntax.compiled_symbols.items():
            for match in symbol.finditer(contents):
                symbols[match.span()[0] + start_position] = {}
                symbols[match.span()[0] + start_position]['type'] = symbol_type
                symbols[match.span()[0] + start_position]['length'] = len(match.group())                

                if symbol_type  == 'pointer':
                    symbols[match.span()[0] + start_position]['contents'] = match.group(2)
                if symbol_type  == 'compact_node':
                    symbols[match.span()[0] + start_position]['full_match'] = match.group()
                    symbols[match.span()[0] + start_position]['node_contents'] = match.group(2)
        
        ## Filter out Syntax Push and delete wrapper elements between them.
        push_syntax = 0
        to_remove = []
        for p in sorted(symbols.keys()):

            if symbols[p]['type'] == 'push_syntax' :
                to_remove.append(p)
                push_syntax += 1
                continue
            
            if symbols[p]['type'] == 'pop_syntax':
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
        start_position=0,
        from_compact=False):
 
        nested_levels = {}  # store node nesting into layers
        nested = 0          # node nesting depth
        unstripped_contents = strip_backtick_escape(contents)
        last_position = start_position

        for position in sorted(symbols.keys()):

            if position <  last_position: 
                # avoid processing wrapped nodes twice if inside compact
                continue

            # Allow node nesting arbitrarily deep
            nested_levels[nested] = [] if nested not in nested_levels else nested_levels[nested]

            if symbols[position]['type'] == 'pointer':
                self.parsed_items[position] = symbols[position]['contents'] +' >>'
                continue

            if symbols[position]['type'] == 'opening_wrapper':                
                nested_levels[nested].append([last_position, position])
                nested += 1

            if not from_compact and symbols[position]['type'] == 'compact_node':
                nested_levels[nested].append([last_position, position])
                
                compact_symbols = self.lex(
                    symbols[position]['full_match'], start_position=position)
                self.parse(symbols[position]['node_contents'], 
                    compact_symbols,
                    start_position=position,
                    from_compact=True)

                last_position = position + len(symbols[position]['full_match'])
                continue
 
            if symbols[position]['type'] == 'closing_wrapper':
                nested_levels[nested].append([last_position + 1, position])
    
                if nested == 0:
                    self.log_error('Missing closing wrapper', position)
                    return None

                if nested < 0:
                    message = 'Stray closing wrapper at %s' % str(position)
                    self.messages.append(message) 

                self.add_node(
                    nested_levels[nested], 
                    unstripped_contents,
                    position,
                    start_position=start_position)

                del nested_levels[nested]
                nested -= 1

            if symbols[position]['type'] == 'EOB':
                # handle closing of file
                nested_levels[nested].append([last_position, position])
                self.add_node(
                    nested_levels[nested], 
                    unstripped_contents,
                    position,
                    root=True if not from_compact else False,
                    compact=from_compact,
                    start_position=start_position)
                continue

            last_position = position
        
        if nested > 0:
            message = 'Un-closed node at %s' % str(position) + ' in ' + self.filename
            self.messages.append(message) 

        if not from_compact and len(self.root_nodes) == 0:
            message = 'No root nodes found'
            self.messages.append(message)

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
            self.filename, 
            node_contents,
            self.project,
            root=root,
            compact=compact)
        
        new_node.get_file_contents = self._get_file_contents
        new_node.set_file_contents = self._set_file_contents

        self.nodes[new_node.id] = new_node   
        self.nodes[new_node.id].ranges = ranges
        if new_node.root_node:
            self.root_nodes.append(new_node.id) 
        self.parsed_items[ranges[0][0]] = new_node.id

    def _get_file_contents(self):
          return self.contents
          
    def _set_file_contents(self, contents):
          return

    def clear_errors(self, contents):
        cleared_contents = syntax.error_messages_c.sub('', contents)
        if cleared_contents != contents:
            self._set_file_contents(cleared_contents)
        self.errors = False
        return cleared_contents

    def write_errors(self, settings, messages=None):
        if not messages and not self.messages:
            return False
        if messages:
            self.messages = messages

        contents = self._get_file_contents()

        messages = ''.join([ 
            '<!!\n',
            '\n'.join(self.messages),
            '\n!!>\n',
            ])

        message_length = len(messages)
        
        for n in re.finditer('position \d{1,10}', messages):
            old_n = int(n.group().strip('position '))
            new_n = old_n + message_length
            messages = messages.replace(str(old_n), str(new_n))

        if len(messages) != message_length:
            pass
             
        new_contents = ''.join([
            messages,
            contents,
            ])

        self._set_file_contents(new_contents, compare=False)
        self.nodes = {}
        self.root_nodes = []
        self.parsed_items = {}
        self.messages = []
        symbols = self.lex(new_contents)
        self.parse(new_contents, symbols)
        self.errors = True
        for n in self.nodes:
            self.nodes[n].errors = True

    def get_ordered_nodes(self):
        return sorted( 
            list(self.nodes.keys()),
            key=lambda node_id :  self.nodes[node_id].start_position())

    def log_error(self, message, position):

        self.nodes = {}
        self.parsed_items = {}
        self.root_nodes = []
        self.file_length = 0
        self.messages.append(message +' at position '+ str(position))

        print(''.join([ 
                message, ' in >f', self.filename, ' at position ',
            str(position)]))