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

    def _write_file_contents(self, new_contents, run_on_modified=False, run_hook=False):
        self.contents = new_contents
        self.write_contents_to_file(run_on_modified=run_on_modified, run_hook=run_hook)

    def write_contents_to_file(self, run_on_modified=True, run_hook=False):
        if run_hook: # for last modification only
            self.project._run_hook('on_write_file_contents', self)
        existing_contents = self._read_contents()
        if existing_contents == self.contents:
            return False

        buffer_updated = self.project.run_editor_method(
            'set_buffer',
            self.filename,
            self.contents)

        # not sure we should ever do this.
        # if buffer_updated and run_on_modified and not self.has_errors:
        #     if self.project.run_editor_method(
        #         'save_file', # expected to call on_modified()
        #         self.filename):
        #             return True

        utils.write_file_contents(self.filename, self.contents)
        self.project._parse_buffer(self)
        if run_on_modified and not self.has_errors:
            self.project._on_modified(self.filename)
        return True
