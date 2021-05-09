from .sublime_urtext import show_panel,UrtextTextCommand,refresh_project_text_command, NodeBrowserMenu, open_urtext_node


class ToIcs(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        node_id = get_node_id(self.view)
        _UrtextProjectList.current_project.export_to_ics(node_id)
