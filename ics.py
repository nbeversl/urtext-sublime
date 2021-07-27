from .sublime_urtext import get_node_id, show_panel, UrtextTextCommand,refresh_project_text_command, NodeBrowserMenu, open_urtext_node


class ToIcs(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        file_pos = self.view.sel()[0].a + 1
        self._UrtextProjectList.current_project.run_action(
            "ICS",
            self.view.substr(self.view.line(self.view.sel()[0])),
            self.view.file_name(),
            file_pos = file_pos,
            col_pos = self.view.rowcol(file_pos)[1]
            )