import os
from .sublime_urtext import show_panel, UrtextTextCommand, refresh_project_text_command, NodeBrowserMenu

class FindByMetaCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self.tagnames = self._UrtextProjectList.current_project.get_all_keys()
        self.view.window().show_quick_panel(self.tagnames, self.list_values)

    def list_values(self, index):
        self.selected_tag = self.tagnames[index]
        self.values = self._UrtextProjectList.current_project.get_all_values_for_key(self.selected_tag)        
        self.values.insert(0, '< all >')
        self.view.window().show_quick_panel(self.values, self.display_files)

    def display_files(self, index):

        self.selected_value = self.values[index]
        if self.selected_value == '< all >':
            pass  # fix this
        self.menu = NodeBrowserMenu(
            self._UrtextProjectList,
            nodes = self._UrtextProjectList.current_project.get_by_meta(self.selected_tag, self.selected_value, '='))
        show_panel(self.view.window(), self.menu.display_menu,
                   self.open_the_node)

    def open_the_node(self, selected_option):
        if selected_option == -1: return
        node_id = self.menu.menu[selected_option].id
        self._UrtextProjectList.current_project.open_node(node_id)