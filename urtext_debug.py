import sublime
import sublime_plugin

from .sublime_urtext import refresh_project_text_command

class DebugCommand(sublime_plugin.TextCommand):

    @refresh_project_text_command()
    def run(self):
        node_id = self._UrtextProjectList.current_project.get_node_id_from_position(
            self.view.file_name(), 
            self.view.sel()[0].a)

        if not node_id:
            return print('No Node found here')
        print('UNTITLED: %s' %
            self._UrtextProjectList.current_project.nodes[node_id].untitled)
        print('DYNAMIC: %s' %
            self._UrtextProjectList.current_project.nodes[node_id].dynamic)
        print('NODE ID: %s' % node_id)
        print('First line title: %s' %
            self._UrtextProjectList.current_project.nodes[node_id].first_line_title)
        print('NESTED: %s' %
            str(self._UrtextProjectList.current_project.nodes[node_id].nested))
        print('RANGES: ')
        print(self._UrtextProjectList.current_project.nodes[node_id].ranges)
        print('ROOT: %s' %
            self._UrtextProjectList.current_project.nodes[node_id].root_node)
        print('Compact: %s' %
            self._UrtextProjectList.current_project.nodes[node_id].compact)
        print('IS META: %s' %
            self._UrtextProjectList.current_project.nodes[node_id].is_meta)
        print('NODE PARENT: %s' %
            self._UrtextProjectList.current_project.nodes[node_id].parent)
        print('TREE PARENT: %s' %
            self._UrtextProjectList.current_project.nodes[node_id].tree_node.parent)
        print('LINKS: ')
        print(self._UrtextProjectList.current_project.nodes[node_id].links)
        print('LINKS IDS: ')
        print(self._UrtextProjectList.current_project.nodes[node_id].links_ids())
        print('METADATA: ')
        print(self._UrtextProjectList.current_project.nodes[node_id].metadata.log())
        print('EXPORTS:')
        print(self._UrtextProjectList.current_project.nodes[node_id].export_points)
        print('TREE CHILDREN:')
        print(self._UrtextProjectList.current_project.nodes[node_id].tree_node.children)
        print('DESCENDANTS:')
        for n in self._UrtextProjectList.current_project.nodes[node_id].descendants():
            print(n.id)
        print('EMBEDDED SYNTAXES')
        print( self._UrtextProjectList.current_project.nodes[node_id].ranges_with_embedded_syntaxes())
        print('------------------------')

class NoAsync(sublime_plugin.TextCommand):

    @refresh_project_text_command()
    def run(self):
        self._UrtextProjectList.current_project.is_async = False