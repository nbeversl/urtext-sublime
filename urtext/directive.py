import re
import os

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from .syntax import flag_regx
    from .utils import force_list

else:
    from urtext.syntax import flag_regx
    from urtext.utils import force_list

class UrtextDirective():

    name = ["EXTENSION"]
    phase = 0
    def __init__(self, project):
    
        self.project = project
        self.argument_string = None

    """ command """

    def execute(self):
        return

    """ hook """

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
        # returning False leaves existing content unmodified
        return ''
    
    def set_dynamic_definition(self, dynamic_definition):
        self.dynamic_definition = dynamic_definition

    def parse_argument_string(self, argument_string):
        self.argument_string = argument_string
        return

class UrtextDirectiveWithKeysFlags(UrtextDirective):
    
    name = ["EXT_WITH_KEYS_FLAGS"]
    phase = 0

    def __init__(self, projects):
        super().__init__(projects)
        self.keys = []
        self.flags = []

    def parse_argument_string(self, argument_string):
        no_keys = self._parse_flags(argument_string)
        self._parse_keys(no_keys)
        
    def _parse_keys(self, argument_string):
        if argument_string:
            for word in argument_string.split(' '):
                if word and word[0] != '-':
                    self.keys.append(word)

    def _parse_flags(self, argument_string):

        flag_regx = re.compile(r'(^|\s)-[\w|_]+(?=\s|$)')
        for f in flag_regx.finditer(argument_string):
            self.flags.append(f.group().strip())
            argument_string = argument_string.replace(f.group(),' ')
        return argument_string

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


class UrtextDirectiveWithParamsFlags(UrtextDirective):

    name = ["EXT_WITH_PARAMS_FLAGS"]
    phase = 0
    
    def __init__(self, projects):
        super().__init__(projects)
        self.keys = []
        self.flags = []
        self.params = []
        self.params_dict = {}

    def parse_argument_string(self, argument_string):

        no_flags = self._parse_flags(argument_string)
        params = []
        params_dict = {}
        
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

        if argument_string:
            for param in separate(argument_string):
                key, value, delimiter = key_value(param, ['before','after','=','?','~', '!='])
                if value:
                    for v in value:
                        params.append((key,v,delimiter))
                        
        for param in params:
            params_dict[param[0]] = param[1:]
        self.params = params
        self.params_dict = params_dict

    def _parse_flags(self, argument_string):
        flags = []
        for f in flag_regx.finditer(argument_string):
            flags.append(f.group().strip())
            argument_string = argument_string.replace(f.group(),' ')
        self.flags = flags
        return argument_string
        
    def have_flags(self, flags):
        for f in force_list(flags):
            if f in self.flags:
                return True
        return False

class UrtextDirectiveWithInteger(UrtextDirective):

    name = ["EXT_WITH_INT"]
    phase = 0

    def __init__(self, projects):
        super().__init__(projects)
        self.number = None
        
    def parse_argument_string(self, argument_string):
        try:
            self.number = int(argument_string)
        except:
            self.number = None        
