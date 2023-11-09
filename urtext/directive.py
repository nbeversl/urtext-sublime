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
    name = []

    def __init__(self, project):
        self.keys_with_flags = []
        self.flags = []
        self.links = []
        self.params = []
        self.arguments = []
        self.params_dict = {}
        self.project = project
        self.argument_string = None
        self.dynamic_definition = None
        self.folder = None

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
        arguments = self.syntax.metadata_arg_delimiter_c.split(argument_string)     
        for arg in arguments:
            arg = arg.strip()

            key_op_value = syntax.dd_key_op_value_c.match(arg)          
            if key_op_value:
                key = key_op_value.group(1)
                op = key_op_value.group(2)
                value = key_op_value.group(3)
                self.params.append((key,value,op))
                continue

            key_with_opt_flags = syntax.dd_key_with_opt_flags.match(arg)
            if key_with_opt_flags:
                key = key_with_opt_flags.group(1).strip()
                flags = []
                #TODO works, could be improved:
                if len(key_with_opt_flags.groups()) > 1:
                    flags = key_with_opt_flags.group().replace(key,'',1).split(' ')
                    flags = [f.strip() for f in flags if f]
                self.keys_with_flags.append((key, flags))
                continue

            flags = syntax.dd_flags_c.match(arg)
            if flags:
                flags = flags.group().split(' ')
                flags = [f.strip() for f in flags if f]
                self.flags.extend(flags)
                continue
            
            hash_value = syntax.dd_hash_meta_c.match(arg)
            if hash_value:
                hash_value = hash_value.group()[1:]
                self.params.append((
                    self.project.settings['hash_key'],
                    hash_value,
                    '='))
                continue

            self.arguments.append(arg.strip())

        for param in self.params:
            self.params_dict.setdefault(param[0], [])
            self.params_dict[param[0]].extend(param[1:])
        
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
            if f in [k[0] for k in self.params_dict.keys()]:
                return True
        return False