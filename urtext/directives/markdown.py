import re
from Urtext.urtext.directives.export import UrtextExport

escaped_text = r'\`.*?\`';

class MarkdownExport(UrtextExport):

    name = ["MARKDOWN"]

    def replace_link(self, contents, title):
        link = '#' + title.lower().replace(' ','-');
        link = link.replace(')','')
        link = link.replace('(','')
        #title = title.replace('`',' ')
        contents = contents.replace(link, '['+title+']('+link+')') 
        # TODO - make quote wrapper optional
        return contents

    def before_replace_node_links(self, range_contents):
        return strip_leading_space(range_contents)

    def after_replace_node_links(self, range_contents):
        escaped_regions = re.finditer(escaped_text, range_contents)
        range_contents = self.replace_file_links(range_contents, escaped_regions)
        return range_contents
        
    def wrap_title(self,node_id, nested):
        title = self.project.nodes[node_id].get_title()      
        return '\n\n' + '#' * nested + ' ' + title.strip()

def strip_leading_space(text):
    result = []
    for line in text.split('\n'):
        if '├' not in line and '└' and '─' not in line:
            line = line.lstrip()
        result.append(line)
    return '\n'.join(result)