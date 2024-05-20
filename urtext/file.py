import os 
from urtext.buffer import UrtextBuffer
import urtext.syntax as syntax
import urtext.utils as utils

class UrtextFile(UrtextBuffer):
   
    def __init__(self, filename, project):
        self.filename = filename
        super().__init__(project, filename, self._read_contents())

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
            self._log_error(''.join([
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

    def write_contents_to_file(self, run_hook=False):
        if run_hook: # for last modification only
            pre_hook_contents = str(self.contents)
            self.project.run_hook('on_write_file_contents', self)
            post_hook_contents = str(self.contents)
        
        existing_contents = self._read_contents()
        if existing_contents == self.contents:
            return False
        self.project.run_editor_method(
            'set_buffer',
            self.filename,
            self.contents)
        utils.write_file_contents(self.filename, self.contents)
        self.project._parse_buffer(self)
        return True

    def write_file_contents(self, new_contents, run_hook=False):
        self.contents = new_contents
        self.write_contents_to_file(run_hook=run_hook)

