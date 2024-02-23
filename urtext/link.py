from .url import url_match
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    import Urtext.urtext.syntax as syntax
else:
    import urtext.syntax as syntax

class UrtextLink:

	def __init__(self, string):
		self.string = string.strip()
        self.project = None
        self.project_link = None
        self.is_http = False
        self.is_node = False
		self.node_id = None
        self.is_file = False
        self.filename = None
        self.is_missing = False
        self.dest_node_position = 0
        self.url = None
        self._parse_string()

    def _parse_string(self):
        project = syntax.project_link_c.search(self.string)
        if project:
            self.project_name = project.group(2)
            self.project_link = project.group()
            string = self.string.replace(project_link, '')
        in_project_link = syntax.any_link_or_pointer_c.search(string)
        if in_project_link:
            print(in_project_link.groups())
            node_id = in_project_link.group(9)
            self.node_id = node_id

        urtext_link = None
        full_match = None
        link_start = None
        link_end = None

        http_link_present = False
        http_link = url_match(string)
        if http_link:
            if col_pos <= http_link.end():
                http_link_present = True
                link_start = http_link.start()
                link_end = http_link.end()
                http_link = full_match = http_link.group().strip()

        for match in syntax.any_link_or_pointer_c.finditer(string):
            if col_pos <= match.end():
                if http_link_present and (
                    link_end < match.end()) and (
                    link_end < match.start()):
                    break
                urtext_link = match.group()
                link_start = match.start()
                link_end = match.end()
                full_match = match.group()
                break

        if http_link and not urtext_link:
            self.http = True
            self.url = http_link
            return True

        if urtext_link:
            if urtext_link[1] in syntax.link_modifiers.values():
                for kind in syntax.link_modifiers:
                    if urtext_link[1] == syntax.link_modifiers[kind]:
                        kind = kind.upper()
                        break
            else:
                self.is_node = True
                print('IT IS A NODE')
                print(match.groups())
                self.node_id = utils.get_id_from_link(full_match)
                if match.group(11):
                    self.dest_node_position = int(match.group(11)[1:])
                return True

            if kind == 'FILE':
                self.is_file = True
                path = urtext_link[2:-2].strip()
                if path[0] == '~':
                    path = os.path.expanduser(path)
                self.filename = path     
                return True
        return False     

