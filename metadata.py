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
        # TODO refactor from below
        if selected_option == -1:
            return
        path = get_path(self.view)
        new_view = self.view.window().open_file(
            os.path.join(
                path,
                self.menu.get_selection_from_index(selected_option).filename))
        if len(selected_option) > 3 and selected_option[3] != None:
            self.locate_node(selected_option[3], new_view)

