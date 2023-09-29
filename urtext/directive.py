import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    import Urtext.urtext.syntax as syntax
    from .utils import force_list, get_id_from_link
    from Urtext.urtext.dynamic_output import DynamicOutput
else:
    import urtext.syntax as syntax
    from urtext.utils import force_list, get_id_from_link
    from urtext.dynamic_output import DynamicOutput

class UrtextDirective:

    phase = 0
    syntax = syntax
    DynamicOutput = DynamicOutput

    def __init__(self, project):
        self.keys = []
        self.flags = []
        self.links = []
        self.params = []
        self.arguments = []
        self.params_dict = {}
        self.project = project
        self.argument_string = None
        self.dynamic_definition = None

    def execute(self):
        return

    def should_continue(self):
        return True

    """ hooks """
    def on_node_modified(self, node):
        return

    def on_node_visited(self, node):
        return

    def on_file_modified(self, file_name):
        return

    def on_any_file_modified(self, file_name):
        return

    def on_file_dropped(self, file_name):
        return

    def on_project_init(self):
        return

    def on_file_visited(self, file_name):
        return

    """ dynamic output """
    def dynamic_output(self, input_contents):
        # return string, or False leaves existing content unmodified
        return ''

    def _dynamic_output(self, input_contents):
        if self.should_continue():
            return self.dynamic_output(input_contents)
        return False
    
    def set_dynamic_definition(self, dynamic_definition):
        self.dynamic_definition = dynamic_definition

    def parse_argument_string(self, argument_string):
        self.argument_string = argument_string.strip()
        argument_string = self._parse_links(argument_string)
        argument_string = self._parse_flags(argument_string)

        for argument in self.syntax.metadata_arg_delimiter_c.split(
                argument_string):
            key, value, operator = self.key_value(
                argument,
                self.syntax.metadata_ops)
            if value:
                for v in value:
                    self.params.append((key,v,operator))
            else:
                self.arguments.append(argument.strip())

        argument_string = self._parse_keys(argument_string)
        for param in self.params:
            self.params_dict.setdefault(param[0], [])
            self.params_dict[param[0]].extend(param[1:])
        
    def _parse_flags(self, argument_string):
        for f in self.syntax.dd_flag_c.finditer(argument_string):
            flag = f.group().strip()
            self.flags.append(flag)
            argument_string = argument_string.replace(flag, '')
        return argument_string

    def _parse_links(self, argument_string):
        for l in self.syntax.any_link_or_pointer_c.finditer(argument_string):
            link = l.group().strip()
            self.links.append(get_id_from_link(link))
            argument_string = argument_string.replace(link, '')
        return argument_string

    def have_flags(self, flags):
        for f in force_list(flags):
            if f in self.flags:
                return True
        return False

    def have_keys(self, keys):
        #TODO disambiguate "keys" from params dict keys
        #(terminology)
        keys = force_list(keys)
        for f in keys:
            if f in list(self.params_dict.keys()):
                return True
        return False

    def _parse_keys(self, argument_string):
        for k in self.syntax.dd_key_c.finditer(argument_string):
            key = k.group().strip()
            self.keys.append(key)
            argument_string = argument_string.replace(key, '', 1)
        return argument_string

    def key_value(self, param, operators):
        operator = operators.search(param)
        if operator:
            operator = operator.group()
            key, value = param.split(operator)
            key = key.lower().strip()
            value = [v.strip() for v in self.syntax.metadata_ops_or_c.split(value)]
            return key, value, operator
        return None, None, None