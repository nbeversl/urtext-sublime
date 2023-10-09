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
        values,
        node,
        is_node=False,
        start_position=None,
        end_position=None, 
        tag_self=False,
        tag_children=False,
        tag_descendants=False,
        from_node=None):

        self.node = node
        self.keyname = keyname
        self.meta_values = []
        self.tag_children = tag_children
        self.tag_descendants = tag_descendants
        self.from_node = from_node
        self.start_position = start_position
        self.end_position = end_position
        self.is_node = is_node
        if is_node:
            self.meta_values = values
        else:
            if not isinstance(values, list):
                values = [values]
            self.meta_values = values
   
    def ints(self):
        parts = self.value.split[' ']
        ints = []
        for b in parts:
            try:
                ints.append(int(b))
            except:
                continue
        return ints

    def text_values(self):
        if self.is_node:
            return ''.join([
                syntax.link_opening_wrapper,
                self.value.title,
                syntax.link_closing_wrapper ])
        return [v.text for v in self.meta_values if v.text]

    def get_timestamps(self):
        return sorted([
            v.timestamp for v in self.meta_values if v.timestamp],
            key=lambda t: t.datetime)

    def log(self):
        print('from_node: %s' % self.from_node)
        print('key: %s' % self.keyname)
        print(self.start_position, self.end_position)
        print('tag descendats: %s' % self.tag_descendants)
        print('is node', self.is_node)
        for value in self.meta_values:
            value.log()
        print('-------------------------')

