import os
import re

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from .buffer import UrtextBuffer
    import Urtext.urtext.syntax as syntax 
else:
    from urtext.buffer import UrtextBuffer
    import urtext.syntax as syntax

class UrtextFile(UrtextBuffer):
   
    def __init__(self, filename, project):
        super().__init__(project)
        self.filename = filename
        self.project = project
        self.file_contents = self._read_file_contents()
        if self.file_contents:
            cleared_contents = self.clear_messages(self._get_file_contents())
            if cleared_contents != self.file_contents:
                self._set_file_contents(cleared_contents)
                self.file_contents = cleared_contents
            self.lex_and_parse(self.file_contents)
            self.write_messages()
            for node in self.nodes:
                node.filename = filename
                node.file = self

    def _get_file_contents(self):
        return self.file_contents

    def _read_file_contents(self):
        """ returns the file contents, filtering out Unicode Errors, directories, other errors """
        try:
            with open(self.filename, 'r', encoding='utf-8') as theFile:
                full_file_contents = theFile.read()
        except IsADirectoryError:
            return None
        except UnicodeDecodeError:
            self.log_error(''.join([
                'UnicodeDecode Error: ',
                syntax.file_link_opening_wrapper,
                self.filename,
                syntax.file_link_closing_wrapper]), 0)
            return None
        return full_file_contents

    def _insert_contents(self, inserted_contents, position):
        self._set_file_contents(''.join([
            self.file_contents[:position],
            inserted_contents,
            self.file_contents[position:],
            ]))

    def _replace_contents(self, inserted_contents, range):
        self._set_file_contents(''.join([
            self.file_contents[:range[0]],
            inserted_contents,
            self.file_contents[range[1]:],
            ]))

    def _set_file_contents(self, new_contents, compare=True): 
        new_contents = "\n".join(new_contents.splitlines())
        if compare:
            existing_contents = self._get_file_contents()
            if existing_contents == new_contents:
                return False
        with open(self.filename, 'w', encoding='utf-8') as theFile:
            theFile.write(new_contents)
        self.file_contents = new_contents
        return True

    def write_messages(self, messages=None):
        if not messages and not self.messages: return False
        if messages: self.messages = messages
        new_contents = self.clear_messages(self._get_file_contents())

        if messages:
            timestamp = self.project.timestamp(as_string=True)
            messages = ''.join([ 
                syntax.urtext_message_opening_wrapper,
                '\n',
                timestamp,
                '\n',
                '\n'.join(messages),
                '\n',
                syntax.urtext_message_closing_wrapper,
                '\n'
                ])

            message_length = len(messages)
            
            for n in re.finditer('position \d{1,10}', messages):
                old_n = int(n.group().strip('position '))
                new_n = old_n + message_length
                messages = messages.replace(str(old_n), str(new_n))
                 
            new_contents = ''.join([
                messages,
                new_contents,
                ])

        self._set_file_contents(new_contents, compare=False)
        # TODO: make DRY
        self.nodes = []
        self.root_node = None
        self.lex_and_parse(new_contents)
        for node in self.nodes:
            node.filename =self.filename
            node.file = self

    def clear_messages(self, contents):
        for match in syntax.urtext_messages_c.finditer(contents):
            if self.user_delete_string not in contents:
                contents = contents.replace(match.group(),'')
        return contents