import os

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from .timestamp import UrtextTimestamp
    import Urtext.urtext.syntax as syntax
else:
    from urtext.timestamp import UrtextTimestamp
    import urtext.syntax as syntax

class MetadataEntry:  # container for a single metadata entry

    def __init__(self, 
        keyname, 
        contents, 
        is_node=False,
        as_int=False,
        position=None,
        recursive=False,
        end_position=None, 
        from_node=None):

        self.keyname = keyname
        self.string_contents = contents
        self.value = ''
        self.recursive=recursive
        self.timestamps = []
        self.from_node = from_node
        self.position = position
        self.end_position = end_position
        self.is_node = is_node
        if is_node:
            self.value = contents
        else:
            self._parse_values(contents)
        
    def _parse_values(self, contents):
        for ts in syntax.timestamp_c.finditer(contents):
            dt_string = ts.group(0).strip()
            contents = contents.replace(dt_string, '').strip()
            t = UrtextTimestamp(dt_string[1:-1])
            if t.datetime:
                self.timestamps.append(t)        
        self.value = contents
   
    def ints(self):
        parts = self.value.split[' ']
        ints = []
        for b in parts:
            try:
                ints.append(int(b))
            except:
                continue
        return ints

    def as_int(self):
        try:
            return int(self.value)
        except:
            return None

    def value_as_string(self):
        if self.is_node:
            return ''.join([
                syntax.link_opening_wrapper,
                self.value.title,
                syntax.link_closing_wrapper ])
        return self.value

    def log(self):
        print('key: %s' % self.keyname)
        print(self.value)
        print('from_node: %s' % self.from_node)
        print('recursive: %s' % self.recursive)
        print(self.timestamps)
        print('is node', self.is_node)
        print('-------------------------')