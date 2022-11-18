import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.urtext.directives.export import UrtextExport
else:
    from urtext.directives.export import UrtextExport

class HTMLExport(UrtextExport):

    name = ["HTML"]
    phase = 600

    def replace_link(self, link, contents, title):

        filename = self.project.nodes[node_id].filename

        if node_id in self.project.files[filename].nodes:
            link = '#'+node_id

        else: 
            base_filename = self.project.nodes[node_id].filename
            this_root_node = self.project.files[base_filename].root_nodes[0]
            link = this_root_node+'.html#'+ node_id
    
        contents = contents.replace(match, '<a href="'+link+'">'+title+'</a>')
        return contents

    def wrap_title(self, node_id, nested):
        return '<h'+str(nested)+'>' + title + '</h'+str(nested)+'>\n'

    def opening_wrapper(self, node_id, nested):
        return '<div class="urtext_nested_'+str(nested)+'"><a name="'+ node_id + '"></a>'

    def closing_wrapper(self):
        return '</div>'

    def replace_range(self, range_contents, range_number, nested):

        if range_number != 0:
    
            heading_tag = 'h'+str(nested)
            range_contents = range_contents.replace(  
                title,
                '<'+heading_tag+'>'+title+'</'+heading_tag+'>',
                1)

        lines = [line.strip() for line in range_contents.split('\n') if line.strip() != '']
        index = 0
        while index < len(lines):
            line = lines[index]

            if line[0] == '-':
                range_contents += '<ul class="urtext-list">'
                while index < len(lines) - 1:
                    range_contents += '<li>'+line[1:]+'</li>'
                    index += 1
                    line = lines[index]
                    if line[0] != '-':
                        break
                range_contents += '</ul>'

            """
            non-list items
            """
            range_contents += '<div class="urtext_line">' + line.strip()
            if range_contents == ranges[-1] and line == lines[-1] and not strip_urtext_syntax:
                range_contents += '<span class="urtext-close-brackets">&#125;&#125;</span>'                
            range_contents += '</div>\n'     
            index += 1  

        if self.have_flags(['-clean_whitespace']):
            range_contents = range_contents.strip()
            if range_contents:
                range_contents = range_contents + '\n'

        return range_contents  