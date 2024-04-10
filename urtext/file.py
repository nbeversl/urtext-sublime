import os 
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from .buffer import UrtextBuffer
    import Urtext.urtext.utils as utils
    import Urtext.urtext.syntax as syntax 
else:
    from urtext.buffer import UrtextBuffer
    import urtext.syntax as syntax
    import urtext.utils as utils

class UrtextFile(UrtextBuffer):
   
    def __init__(self, filename, project):
        self.filename = filename
        self.contents = None
        super().__init__(project, filename, self._get_contents())
        self.clear_messages_and_parse()
        # self._write_contents(run_on_modified=False)
        for node in self.nodes:
            node.filename = filename
            node.file = self

    def _get_contents(self):
        if not self.contents:
            self.contents = self._read_contents()
        return self.contents

    def _read_contents(self):
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
        except TimeoutError:
            return print('Timed out reading %s' % self.filename)
        except FileNotFoundError:
            return print('Cannot read file from storage %s' % self.filename)
        return full_file_contents

    def _insert_contents(self, inserted_contents, position):
        self._set_contents(''.join([
            self.contents[:position],
            inserted_contents,
            self.contents[position:],
            ]))

    def _replace_contents(self, inserted_contents, range):
        self._set_contents(''.join([
            self.contents[:range[0]],
            inserted_contents,
            self.contents[range[1]:],
            ]))

    def clear_messages_and_parse(self):
        contents = self._get_contents()
        if contents:
            cleared_contents = self.clear_messages(contents)
            self._set_contents(cleared_contents, run_on_modified=False)
            self.lex_and_parse()
            self.write_messages()

    def _set_contents(self, new_contents, run_on_modified=True):
        print('RUN ON MODIFIED is', run_on_modified)
        self.contents = new_contents
        self.project._run_hook('on_set_file_contents', self)
        existing_contents = self._read_contents()
        if existing_contents == self.contents:
            return False

        buffer_updated = self.project.run_editor_method(
            'set_buffer',
            self.filename,
            self.contents)

        if buffer_updated and run_on_modified and not self.has_errors:
            if self.project.run_editor_method(
                'save_file', # expected to call on_modified()
                self.filename):
                    return True

        utils.write_file_contents(self.filename, self.contents)
        if run_on_modified and not self.has_errors:
            self.project._on_modified(self.filename)
        return True
