"""
Phases:
100s: Queries, building and sorting list of nodes included/excluded
200s: convert selected nodes to text output
300s: Transforming text (multiples permitted)
400s: unused currently
500s: Adding header/footer
600s: do some customized action outside of this order
700s: custom output, bypasses 300
"""

import re
import os

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    import Urtext.urtext.syntax as syntax
    from .utils import force_list

else:
    import urtext.syntax as syntax
    from urtext.utils import force_list

class UrtextDirective():

    name = ["EXTENSION"]
    phase = 0
    def __init__(self, project):
        
        self.keys = []
        self.flags = []
        self.params = []
        self.params_dict = {}
        self.project = project
        self.argument_string = None
        self.dynamic_definitions = None

    """ command """

    def execute(self):
        return

    """ hooks """
    def on_node_modified(self, node):
        return

    def on_node_visited(self, node):
        return

    def on_file_modified(self, file_name):
        return

    def on_any_file_modified(self, file_name):
        return

    def on_file_removed(self, file_name):
        return

    def on_project_init(self):
        return

    def on_file_visited(self, file_name):
        return

    """ dynamic output """
    def dynamic_output(self, input_contents):
        # return string, or False leaves existing content unmodified
        return ''
    
    def set_dynamic_definition(self, dynamic_definition):
        self.dynamic_definition = dynamic_definition

    def parse_argument_string(self, argument_string):
        self.argument_string = argument_string
        argument_string_no_keys = self._parse_flags(argument_string)
        self._parse_keys(argument_string_no_keys)

        if argument_string:
            for param in separate(argument_string):
                key, value, delimiter = key_value(
                    param, 
                    ['before','after','=','?','~', '!='])
                if value:
                    for v in value:
                        self.params.append((key,v,delimiter))
                        
        for param in self.params:
            self.params_dict[param[0]] = param[1:]
    
    def _parse_flags(self, argument_string):
        for f in syntax.flag_c.finditer(argument_string):
            self.flags.append(f.group().strip())
            argument_string = argument_string.replace(f.group(),' ')
        return argument_string

    def _parse_keys(self, argument_string):
        if argument_string:
            for word in argument_string.split(' '):
                if word and word[0] != '-':
                    self.keys.append(word)

    def have_flags(self, flags):
        for f in force_list(flags):
            if f in self.flags:
                return True
        return False

    def have_keys(self, keys):
        for f in force_list(keys):
            if f in self.keys:
                return True
        return False

def separate(string, delimiter=';'):
    return [r.strip() for r in re.split(delimiter+'|\n', string)]

def key_value(param, delimiters=[':']):
    if isinstance(delimiters, str):
        delimiters = [delimiters]
    for delimiter in delimiters:
        if delimiter in param:
            key,value = param.split(delimiter,1)
            key = key.lower().strip()
            value = [v.strip() for v in value.split('|')]
            return key, value, delimiter
    return None, None, None