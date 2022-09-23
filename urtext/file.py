# -*- coding: utf-8 -*-
"""
This file is part of Urtext.

Urtext is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Urtext is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Urtext.  If not, see <https://www.gnu.org/licenses/>.

"""
import os
import re
import concurrent.futures
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from .node import UrtextNode
    from .utils import strip_backtick_escape
else:
    from urtext.node import UrtextNode
    from urtext.utils import strip_backtick_escape

node_id_regex =         r'\b[0-9,a-z]{3}\b'
node_link_regex =       r'>[0-9,a-z]{3}\b'
node_pointer_regex =    r'>>[0-9,a-z]{3}\b'
error_messages =        '<!{1,2}.*?!{1,2}>\n?'

compiled_symbols = [re.compile(symbol) for symbol in  [
    r'(?<!\\){',  # inline node opening wrapper
    r'(?<!\\)}',  # inline node closing wrapper
    '>>', # node pointer
    r'\n', # line ending (closes compact node)
    r'%%-[A-Z]*', # push syntax 
    r'%%-[A-Z]*-END', # pop syntax
 
    ]]

# additional symbols using MULTILINE flag
compiled_symbols.extend( [re.compile(symbol, re.M) for symbol in [
    '^[^\S\n]*•',  # compact node opening wrapper
    ] ])

# number of positions to advance parsing for of each possible symbol
symbol_length = {   
    '^[^\S\n]*•': 0, # compact node opening wrapper
    r'(?<!\\){' : 1, # inline opening wrapper
    r'(?<!\\)}' : 1, # inline closing wrapper
    '>>' : 2, # node pointer
    r'\n' : 0, # compact node closing
    'EOF': 0,
}

class UrtextBuffer:

    urtext_node = UrtextNode

    def __init__(self, contents, project):
        
        self.nodes = {}
        self.root_nodes = []
        self.alias_nodes = []           
        self.parsed_items = {}
        self.anonymous_nodes = []
        self.strict = False
        self.messages = []        
        self.errors = False
        self.contents = contents
        self.filename = 'yyyyyyyyyyy'
        self.basename = 'yyyyyyyyyyy'
        self.project = project
        
        
        self.could_import = False        
        self.file_length = len(contents)        
        self.parse(self.lex(contents))
        self.obj = {}
            
    def lex(self, contents):

        self.symbols = {}

        unstripped_contents = contents
        contents = strip_backtick_escape(contents)
              
        for compiled_symbol in compiled_symbols:
            locations = compiled_symbol.finditer(contents)
            for loc in locations:
                start = loc.span()[0]
                self.symbols[start] = compiled_symbol.pattern

        self.positions = sorted([key for key in self.symbols if key != -1])
        
        ## Filter out Syntax Push and delete wrapper elements between them.
        push_syntax = 0
        escaped = False
        to_remove = []
        for p in self.positions:
            
            if self.symbols[p] == '%%-[A-Z]*' :
                to_remove.append(p)
                push_syntax += 1
                continue
            
            if self.symbols[p] == '%%-[A-Z]*-END':
                to_remove.append(p)
                push_syntax -= 1
                continue

            if push_syntax > 0:
                to_remove.append(p)

        for s in to_remove:
            del self.symbols[s]
            self.positions.remove(s)

        return unstripped_contents

    def parse(self, contents):

        nested = 0  #  depth of node nesting
        nested_levels = {} # store node nesting into layers
        last_position = 0  # most recently parsed position in file
        compact_node_open = False

        """
        Trim leading symbols that are newlines
        """

        if self.positions:
            while self.positions and self.symbols[self.positions[0]] == r'\n' :
                self.positions.pop(0)
        
        first_wrapper = 0
        while first_wrapper < len(self.positions) - 1 and self.symbols[self.positions[first_wrapper]] == '>>' :
             first_wrapper += 1
        
        if self.positions and self.symbols[self.positions[first_wrapper]] != r'\n':
            nested_levels[0] = [ [0, self.positions[first_wrapper] + symbol_length[self.symbols[self.positions[first_wrapper]]] ] ]

        self.positions.append(len(contents))
        self.symbols[len(contents)] = 'EOF'

        unstripped_contents = contents
        contents = strip_backtick_escape(contents)
        obj = {}

        for index in range(0, len(self.positions)):

            position = self.positions[index]

            # Allow node nesting arbitrarily deep
            nested_levels[nested] = [] if nested not in nested_levels else nested_levels[nested]
            
            """
            If this opens a new node
            """
                  
            if self.symbols[position] == r'(?<!\\){':

                if [last_position, position + 1] not in nested_levels[nested]:
                    nested_levels[nested].append([last_position, position + 1])

                nested += 1 
                last_position = position + 1
                continue

            """
            If this points to an outside node, find which node
            """
            if self.symbols[position] == '>>':
                
                node_pointer = contents[position:position + 5]
                
                if re.match(node_pointer_regex, node_pointer):
                    self.parsed_items[position] = node_pointer

                continue

            """
            If the symbol opens a compact node
            """
            if self.symbols[position] == '^[^\S\n]*•': 
                # TODO - FIGURE OUT WHY ADDING + 1 to these positions to correct the 
                # parsing causes exporting to skip entire regions
                if [last_position, position  ] not in nested_levels[nested] and position  > last_position:
                    nested_levels[nested].append([last_position, position ])
                nested += 1 
                last_position = position + 1
                compact_node_open = True
                continue    

            """
            Node closing symbols :  }, newline, EOF
            """
            if self.symbols[position] in [r'(?<!\\)}', r'\n', 'EOF']:  # pop
                
                compact, root = False, False

                if self.symbols[position] == r'\n':
                    if compact_node_open:
                        compact = True
                        compact_node_open = False   
                    else:
                        # newlines are irrelevant if compact node is not open
                        continue

                if self.symbols[position] == 'EOF' and compact_node_open:
                    compact = True
                    compact_node_open = False   

                
                if [last_position, position] not in nested_levels[nested]: # avoid duplicates
                    nested_levels[nested].append([last_position, position ])
                
                # file level nodes are root nodes, with multiples permitted  
                if not compact:

                    if nested == 0 or self.symbols[position] == 'EOF':
                        if self.strict and nested != 0:
                            #TODO -- if a compact node closes the file, this error will be thrown.
                            self.log_error('Missing closing wrapper', position)
                            return None

                        root = True

                success = self.add_node(
                    nested_levels[nested], 
                    unstripped_contents, 
                    position, 
                    root=root, 
                    compact=compact)

                del nested_levels[nested]

                if compact and not success and self.symbols[position] != 'EOF' :
                    nested -=1
                    nested_levels[nested].append([last_position, position])
                    last_position = position + symbol_length[self.symbols[position]]
                    continue
                    
                if self.symbols[position] == 'EOF' and compact:
                    # handle closing of both compact node and file
                    nested -=1
                    root=True
                    compact=False

                    success = self.add_node(
                        nested_levels[nested], 
                        unstripped_contents,
                        position,
                        root=root,
                        compact=compact)

                last_position = position + symbol_length[self.symbols[position]]

                # reduce the nesting level only for compact, inline nodes
                if not root:
                    nested -= 1                       

                if nested < 0:
                    message = 'Stray closing wrapper at %s' % str(position)
                    if self.strict:
                        return self.log_error(message, position)  
                    else:
                        self.messages.append(message) 

        if nested > 0:
            message = 'Un-closed node at %s' % str(position) + ' in ' + self.filename
            if self.strict:
                return self.log_error(message, position)  
            else:
                self.messages.append(message) 

        if len(self.root_nodes) == 0:
            message = 'No root nodes found'
            if self.strict: 
                return self.log_error(message, 0)
            else: 
                self.messages.append(message)

    def add_node(self, 
        ranges, 
        contents,
        position,
        root=None,
        compact=None):

        # Build the node contents and construct the node
        node_contents = ''.join([contents[r[0]:r[1]]  for r in ranges])

        new_node = self.urtext_node(
            self.filename, 
            node_contents,
            self.project,
            root=root,
            compact=compact)
        
        new_node.get_file_contents = self._get_file_contents
        new_node.set_file_contents = self._set_file_contents
        
        if new_node.id != None: # and re.match(node_id_regex, new_node.id):
            self.nodes[new_node.id] = new_node
            self.nodes[new_node.id].ranges = ranges
            if new_node.root_node:
                self.root_nodes.append(new_node.id) 
            self.parsed_items[ranges[0][0]] = new_node.id
            return True
        else:
            if root:
                self.anonymous_nodes.append(new_node) 
                self.messages.append('Warning : root Node has no ID.')
            elif compact:
                pass
            else:
                self.anonymous_nodes.append(new_node) 
                self.messages.append('Warning: Node missing ID at position '+str(position))
            return False
            
    def _get_file_contents(self):
          return self.contents 
          
    def _set_file_contents(self, contents):
          return
          
    def get_node_id_from_position(self, position):
            for node_id in self.nodes:
                for r in self.nodes[node_id].ranges:
                    if position in range(r[0],r[1]+1): # +1 in case the cursor is in the last position of the node.
                        return node_id
            return None

    def clear_errors(self, contents):
        cleared_contents = re.sub(error_messages, '', contents, flags=re.DOTALL)
        if cleared_contents != contents:
            self._set_file_contents(cleared_contents)
        self.errors = False
        return cleared_contents

    def write_errors(self, settings, messages=None):
        if not messages and not self.messages:
            return False
        if messages:
            self.messages = messages
        
        if self.nodes == {}:
            self.could_import = True
            return

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
        self.anonymous_nodes = []
        self.parsed_items = {}
        self.messages = []
        self.parse(new_contents)
        self.errors = True
        for n in self.nodes:
            self.nodes[n].errors = True

    def log_error(self, message, position):

        self.nodes = {}
        self.parsed_items = {}
        self.root_nodes = []
        self.file_length = 0
        self.messages.append(message +' at position '+ str(position))

        print(''.join([ 
                message, ' in >f', self.filename, ' at position ',
            str(position)]))
            

class UrtextFile(UrtextBuffer):
   
    def __init__(self, filename, project):
        self.basename = os.path.basename(filename)
        self.nodes = {}
        self.root_nodes = []
        self.alias_nodes = []           
        self.parsed_items = {}
        self.strict = False
        self.messages = []        
        self.errors = False
        self.project = project
        self.anonymous_nodes = []
        
        self.filename = os.path.join(project.path, os.path.basename(filename))
        contents = self._get_file_contents()
        self.could_import = False        
        self.file_length = len(contents)        
        self.clear_errors(contents)
        self.parse(self.lex(contents))
        self.write_errors(project.settings)
      
    def _get_file_contents(self):
        
        """ returns the file contents, filtering out Unicode Errors, directories, other errors """
        try:
            with open(self.filename, 'r', encoding='utf-8',) as theFile:
                full_file_contents = theFile.read()
        except IsADirectoryError:
            return None
        except UnicodeDecodeError:
            self.log_error('UnicodeDecode Error: f>' + self.filename)
            return None
        return full_file_contents.encode('utf-8').decode('utf-8')

    def _set_file_contents(self, new_contents, compare=True): 

        new_contents = "\n".join(new_contents.splitlines())
        if compare:
            existing_contents = self._get_file_contents()
            existing_contents = "\n".join(existing_contents.splitlines())
            if not existing_contents:
                return False
            if existing_contents == new_contents:
                return False
        with open(self.filename, 'w', encoding='utf-8') as theFile:
            theFile.write(new_contents)
        return True

