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
        self._parse_flags(argument_string)
        self._parse_keys(argument_string)

        for param in [r.strip() for r in syntax.metadata_arg_delimiter_c.split(argument_string)]:
            key, value, operator = key_value(
                param,
                syntax.metadata_ops)
            if value:
                for v in value:
                    self.params.append((key,v,operator))
                        
        for param in self.params:
            self.params_dict[param[0]] = param[1:]
    
    def _parse_flags(self, argument_string):
        for f in syntax.dd_flag_c.finditer(argument_string):
            self.flags.append(f.group().strip())

    def _parse_keys(self, argument_string):
        for f in syntax.dd_key_c.finditer(argument_string):
            self.keys.append(f.group().strip())

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

def key_value(param, operators):
    operator = operators.search(param)
    if operator:
        operator = operator.group()
        key, value = param.split(operator)
        key = key.lower().strip()
        value = [v.strip() for v in syntax.metadata_ops_or_c.split(value)]
        return key, value, operator
    return None, None, None