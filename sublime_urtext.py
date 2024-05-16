import sublime
import sublime_plugin
import os
import re
import html
import subprocess
import webbrowser
import Urtext.urtext.syntax as syntax
from Urtext.urtext.project_list import ProjectList
from sublime_plugin import EventListener, ViewEventListener
from Urtext.urtext.utils import match_compact_node
_UrtextProjectList = None

class UrtextTextCommand(sublime_plugin.TextCommand):

    def __init__(self, view):
        self.view = view
        self.window = view.window()

def open_file_to_position(filename, position, node_range=None):

    if sublime.active_window():
        new_view = sublime.active_window().find_open_file(filename)
        if not new_view:
            new_view = sublime.active_window().open_file(filename)

        def focus_position(focus_view, position):
            if not focus_view.is_loading():
                if focus_view.window():
                    focus_view.window().focus_view(focus_view)
                    position_node(position, view=focus_view)
                    if node_range:
                        highlight_region(focus_view, node_range)
            else:
                sublime.set_timeout(lambda: focus_position(focus_view, position), 50) 

        focus_position(new_view, position)

        return new_view

def insert_text(text):
    if sublime.active_window() and sublime.active_window().active_view():
        view = sublime.active_window().active_view()
        view.run_command("insert", {"characters": text})
        return True
    return False

def save_current():
    if sublime.active_window() and sublime.active_window().active_view():
        view = sublime.active_window().active_view()
        view.run_command('save')
        return True
    return False

def save_file(filename):
    view = sublime.active_window().find_open_file(filename)
    if view:
        view.run_command('save')
        return True
    return False

def set_clipboard(text):
    sublime.set_clipboard(text)
    show_popup(text + '\ncopied to the clipboard')

def show_popup(text):
    if sublime.active_window() and sublime.active_window().active_view():
        view = sublime.active_window().active_view()
        view.show_popup(
            text, 
            max_width=1800, 
            max_height=1000)

def set_buffer(filename, contents):
    view = sublime.active_window().find_open_file(filename)
    if view:
        view.run_command('urtext_replace', {
            'start' : 0,
            'end' :view.size(),
            'replacement_text' : contents
            })
        return True
    return False

def get_buffer(filename):
    view = None
    if filename:
        view = sublime.active_window().find_open_file(filename)
    else:
        view = sublime.active_window().active_view()
    if view:
        return view.substr(sublime.Region(0, view.size()))

def show_status(message):
    window = sublime.active_window()
    if window and window.active_view():
        window.active_view().set_status('Urtext', message)


def replace(filename='', start=0, end=0, replacement_text=''):
    target_view = None
    view = sublime.active_window().find_open_file(filename)
    if view:
        view.run_command('urtext_replace', {
            'start' : start,
            'end' :end,
            'replacement_text' : replacement_text
            })

def open_external_file(filepath):
    if _UrtextProjectList and _UrtextProjectList.current_project:
        open_in_sublime = _UrtextProjectList.current_project.get_setting('open_in_sublime')
        ext = os.path.splitext(filepath)[1]
        if ext.strip('.') in [e.strip('.') for e in open_in_sublime]:
            return open_file_in_editor(filepath)
    if sublime.platform() == "osx":
        subprocess.Popen(('open', filepath))
    elif sublime.platform() == "windows":
        os.startfile(filepath)
    elif sublime.platform() == "linux":
        subprocess.Popen(('xdg-open', filepath))

def open_file_in_editor(filepath):
    if sublime.active_window():
        sublime.active_window().open_file(filepath)

def open_http_link(link):
    #TODO : possibly refactor into Urtext library
    if link[:8] != 'https://' and link [:7] != 'http://':
        link = 'https://' + link
    success = webbrowser.get().open(link)
    if not success:
        self.log('Could not open tab using your "web_browser_path" setting')       

def close_current():
    if sublime.active_window() and sublime.active_window().active_view():
        view = sublime.active_window().active_view()
        view.close()

def close_file(filename):
    view = sublime.active_window().find_open_file(filename)
    if view:
        view.set_scratch(True)
        view.close()

def retarget_view(old_filename, new_filename):
    view = sublime.active_window().find_open_file(old_filename)
    if view:
        view.retarget(new_filename)

editor_methods = {
    'open_file_to_position' : open_file_to_position,
    'error_message' : sublime.error_message,
    'insert_text' : insert_text,
    'save_current' : save_current,
    'set_clipboard' : set_clipboard,
    'open_external_file' : open_external_file,
    'open_file_in_editor' : open_file_in_editor,
    'open_http_link' : open_http_link,
    'get_buffer' : get_buffer,
    'set_buffer' : set_buffer,
    'replace' : replace,
    'popup' : show_popup,
    'close_current': close_current,
    'write_to_console' : print,
    'status_message' : show_status,
    'close_file': close_file,
    'save_file': save_file,
    'retarget_view' : retarget_view,
}

def refresh_project_text_command(mouse=False, new_file_node_created=False):
    """ 
    Determine which project we are in based on the Sublime window.
    Used as a decorator in every command class.
    """    
    def middle(function):

        def wrapper(*args, **kwargs):
            
            view = args[0].view
            edit = args[1]
            window = sublime.active_window()
            global _UrtextProjectList
            if not _UrtextProjectList:
                _UrtextProjectList = initialize_project_list(
                    window,
                    new_file_node_created=new_file_node_created)
            if not _UrtextProjectList:
                return None

            if not _UrtextProjectList.current_project:
                folder = get_current_folder(window)
                if not _UrtextProjectList.set_current_project(folder):
                    _UrtextProjectList.add_project(folder)
                    _UrtextProjectList.set_current_project(folder)
            if _UrtextProjectList.current_project:
                args[0].edit = edit
                args[0]._UrtextProjectList = _UrtextProjectList
                if mouse:
                    return function(args[0], edit, **kwargs)
                return function(args[0])
            return None
        return wrapper
    return middle

def initialize_project_list(window, 
    add_project=True,
    reload_projects=False,
    new_file_node_created=False):

    global _UrtextProjectList

    if reload_projects:
        _UrtextProjectList = None
    if not window:
        return
    folder = get_current_folder(window)

    if _UrtextProjectList and _UrtextProjectList.current_project:
        if _UrtextProjectList.current_project.has_folder(folder):
            return _UrtextProjectList
    if _UrtextProjectList and folder:
        if not _UrtextProjectList.set_current_project(folder) and add_project:
            return _UrtextProjectList.initialize_project(folder, new_file_node_created=new_file_node_created)

    elif folder and add_project:
        _UrtextProjectList = ProjectList(
            folder,
            editor_methods=editor_methods)
    return _UrtextProjectList

def get_current_folder(window):
    view = window.active_view()
    folder = None

    if view and view.file_name():
        folder = os.path.dirname(view.file_name())

    if not folder:
        folders = window.folders()
        if folders:
            folder = folders[0]
    if not folder:
        project_data = window.project_data()
        if project_data and "folders" in project_data and project_data["folders"]:
            folder = project_data["folders"][0]["path"]
    return folder

class UrtextReplace(sublime_plugin.TextCommand):

    def run(self, edit, start=0, end=0, replacement_text=''):
        self.view.replace(edit, sublime.Region(start, end), replacement_text)

class ListProjectsCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):
        self.window = self.view.window()
        show_panel(
            self.window, 
            self._UrtextProjectList.project_titles(), 
            self.set_window_project)

    def set_window_project(self, index):
        title = self._UrtextProjectList.project_titles()[index]
        self._UrtextProjectList.set_current_project(title)

class MoveFileToAnotherProjectCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):
        project_titles = self._UrtextProjectList.project_titles()

        def move_file(selected_index):
            self._UrtextProjectList.move_file(
                self.view.file_name(), 
                self._UrtextProjectList.current_project.title(),
                project_titles[selected_index])
            self.view.window().run_command('close_file')
            
        show_panel(
            self.view.window(),
            project_titles, 
            move_file)

class UrtextEventListeners(EventListener):

    def on_activated(self, view):
        _UrtextProjectList = initialize_project_list(view.window(), add_project=False)
        if view and view.file_name() and _UrtextProjectList:
            _UrtextProjectList.visit_node(view.file_name(), get_node_id(view))
                
    def on_post_save(self, view):
        if view and view.file_name() and _UrtextProjectList:
            _UrtextProjectList.on_modified(view.file_name())

    def on_hover(self, view, point, hover_zone):
        if view.is_folded(sublime.Region(point, point)) and _UrtextProjectList:
            for r in view.folded_regions():
                if point in [r.a, r.b]:
                    contents = view.export_to_html(
                        sublime.Region(r.a,r.b))

            def unfold_region(href_region):
                points = href_region.split('-')
                region = sublime.Region(int(points[0]), int(points[1]))
                view.unfold(region)
                view.hide_popup()

            contents += '<a href="%s-%s">unfold</a>' % (r.a, r.b)

            view.show_popup(contents, 
                max_width=512, 
                max_height=512, 
                location=file_pos,
                on_navigate=unfold_region)

        if _UrtextProjectList:
            region = view.line(point)
            file_pos = region.a
            full_line_region = view.full_line(region)
            row, col_pos = view.rowcol(point)
            full_line = view.substr(full_line_region)
            link = _UrtextProjectList.parse_link(full_line, view.file_name(), col_pos=col_pos)
            if link and link.is_node and  (
                link.node_id in _UrtextProjectList.current_project.nodes ) and (
                col_pos in range(link.position_in_string, link.position_in_string + 3)
                ):
                contents = _UrtextProjectList.current_project.nodes[link.node_id].contents()
                if contents:

                    def open_node_from_this_view(node_id):
                        _UrtextProjectList.current_project.open_node(link.node_id)

                    markup = """
                        <body id="linked_node_contents">
                            <style>
                                h1 {
                                    font-size: 1.1rem;
                                    font-weight: 500;
                                    margin: 0 0 0.5em 0;
                                    font-family: system;
                                }
                                p {
                                    margin-top: 0;
                                }
                                a {
                                    font-weight: normal;
                                    font-style: italic;
                                    padding-left: 1em;
                                    font-size: 1.0rem;
                                }
                                span.nums {
                                    display: inline-block;
                                    text-align: right;
                                    color: color(var(--foreground) a(0.8))
                                }
                                span.context {
                                    padding-left: 0.5em;
                                }
                            </style>
                            <p>%s</p>
                            <a href="%s">open</a>
                        </body>
                    """ % (contents, html.escape(link.node_id))
                    view.show_popup(markup,
                        max_width=512, 
                        max_height=512, 
                        location=file_pos,
                        on_navigate=open_node_from_this_view,
                        flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY)

    def on_query_completions(self, view, prefix, locations):
        _UrtextProjectList = initialize_project_list(view.window(), add_project=False)
        if _UrtextProjectList and _UrtextProjectList.current_project:
            if _UrtextProjectList.set_current_project(os.path.dirname(view.file_name())):
                subl_completions = []
                proj_completions = _UrtextProjectList.current_project.get_all_meta_pairs()
                for c in proj_completions:
                    if '::' in c:
                        t = c.split('::')
                        if len(t) > 1:
                            subl_completions.append([t[1]+'\t'+c, c])
                    elif c[0] == '#':
                        subl_completions.append(['#'+c[1:]+'\t'+c, c])
                for t in _UrtextProjectList.current_project.title_completions():
                    subl_completions.append([t[0],t[1]])
                return (subl_completions, 
                    sublime.INHIBIT_WORD_COMPLETIONS,
                    sublime.DYNAMIC_COMPLETIONS
                    )

class UrtextViewEventListener(ViewEventListener):

    def on_deactivated(self):
        if _UrtextProjectList and _UrtextProjectList.current_project:
            if self.view and ( self.view.file_name() and self.view.is_dirty()
                and self.view.file_name() in _UrtextProjectList.current_project.files):
                    self.view.run_command('save')
                    _UrtextProjectList.on_modified(self.view.file_name())

class OpenUrtextLinkCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        line, cursor = get_line_and_cursor(self.view)
        self._UrtextProjectList.handle_link(
            line, 
            self.view.file_name(),
            col_pos=cursor)
                            
class MouseOpenUrtextLinkCommand(sublime_plugin.TextCommand):

    @refresh_project_text_command(mouse=True)
    def run(self, edit, **kwargs):
        click_position = self.view.window_to_text((kwargs['event']['x'],kwargs['event']['y']))
        region = self.view.line(click_position)
        file_pos = region.a
        full_line_region = self.view.full_line(region)
        row, col_pos = self.view.rowcol(click_position)
        full_line = self.view.substr(sublime.Region(full_line_region.a-1, full_line_region.b))
        link = self._UrtextProjectList.handle_link(
            full_line,
            self.view.file_name(),
            col_pos=col_pos)

    def want_event(self):
        return True

class NodeBrowserCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):
        if not _UrtextProjectList.current_project:
            return print('No current Urtext project')
        self.window = self.view.window()
        self.menu = NodeBrowserMenu(
            _UrtextProjectList, 
            project=_UrtextProjectList.current_project)

        self.selection_has_changed = False
        show_panel(
            self.window, 
            self.menu.display_menu, 
            self.open_the_file,
            on_highlight=self.on_highlight)

    def on_highlight(self, index):
        if self.selection_has_changed:
            preview_urtext_node(self.menu.menu[index].id)
        else:
            self.selection_has_changed = True

    def open_the_file(self, index):
        node = self.menu.menu[index]
        _UrtextProjectList.set_current_project(node.project.title())
        _UrtextProjectList.current_project.open_node(node.id)

class BacklinksBrowser(NodeBrowserCommand):

    @refresh_project_text_command()
    def run(self):
        backlinks = self._UrtextProjectList.current_project.get_links_to(
            get_node_id(self.view),
            as_nodes=True)

        if backlinks:
            self.menu = NodeBrowserMenu(
                self._UrtextProjectList, 
                project=self._UrtextProjectList.current_project,
                nodes=backlinks)

            show_panel(
                self.view.window(),
                self.menu.display_menu,
                self.open_the_file)

class ForwardlinksBrowser(NodeBrowserCommand):

    @refresh_project_text_command()
    def run(self):
        forward_links = self._UrtextProjectList.current_project.get_links_from(
            get_node_id(self.view),
            as_nodes=True)
        self.menu = NodeBrowserMenu(
            self._UrtextProjectList, 
            project=self._UrtextProjectList.current_project,
            nodes=forward_links,
            )
        show_panel(
            self.view.window(), 
            self.menu.display_menu, 
            self.open_the_file)

class AllProjectsNodeBrowser(NodeBrowserCommand):
    
    @refresh_project_text_command()
    def run(self):
        self.menu = NodeBrowserMenu(
            self._UrtextProjectList, 
            project=None
            )
        show_panel(
            self.view.window(), 
            self.menu.display_menu, 
            self.open_the_file)

class WrapSelectionCommand(sublime_plugin.TextCommand):
    
    @refresh_project_text_command()
    def run(self):
        region = self.view.sel()[0]
        selection = self.view.substr(region)
        self.view.replace(self.edit, region, ''.join(['{ ',selection, ' }']))
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(region.a+2, region.a+2))

class NodeBrowserMenu:

    def __init__(self, 
        project_list, 
        project=None, 
        nodes=None):

        # rough estimate of character width
        view = sublime.active_window().active_view()
        characters = int(view.viewport_extent()[0] / view.em_width())

        self.menu = []
        self.display_menu = []

        projects = project_list.projects
        if project:
            projects = [project]
        else:
            project = project_list.current_project
        
        if nodes != None:
            self.menu = nodes
        else:
            for single_project in projects:
                self.menu.extend(single_project.sort_for_node_browser(as_nodes=True))

        self.display_menu = [(
            node.id[:characters],
            node.display_detail) for node in self.menu]

def show_panel(window, menu, main_callback, on_highlight=None):
    """ shows a quick panel with an option to cancel if -1 """
    def on_selected(index):
        if index == -1:
            return
        main_callback(index)
    if window:
        window.show_quick_panel(menu, 
            on_selected, 
            selected_index=-1, # doesn't work; Sublime Text Bug
            on_highlight=on_highlight)
    else:
        print('(debugging) no window (Sublime)')

class LinkToNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self.menu = NodeBrowserMenu(self._UrtextProjectList, project=None)
        show_panel(
            self.view.window(), 
            self.menu.display_menu,
            self.link_to_the_node)

    def link_to_the_node(self, selected_option):
        self._UrtextProjectList.editor_insert_link_to_node(
            self.menu.menu[selected_option],
            project_title=self.menu.menu[selected_option].project.title()
            )

class CopyLinkToHereCommand(UrtextTextCommand):
    """
    Copy a link to the node containing the cursor to the clipboard.
    Does not include project title.
    """
    @refresh_project_text_command()
    def run(self):
        self._UrtextProjectList.editor_copy_link_to_node(
            self.view.sel()[0].a,
            self.view.file_name())

class CopyLinkToHereWithProjectCommand(CopyLinkToHereCommand):

    @refresh_project_text_command()
    def run(self):
        self._UrtextProjectList.editor_copy_link_to_node(
            self.view.sel()[0].a,
            self.view.file_name(),
            include_project=True)

class NewFileNodeCommand(UrtextTextCommand):

    @refresh_project_text_command(new_file_node_created=True)
    def run(self):
        path = None
        if self.view and self.view.file_name():
            path = os.path.dirname(self.view.file_name())
        if not path:
            path = self.view.window().folders()[0]
        if not path:
            return
        self._UrtextProjectList.set_current_project(path)
        self._UrtextProjectList.current_project.new_file_node(path=path)

class InsertLinkToNewNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        new_node = self._UrtextProjectList.current_project.new_file_node(
            path=os.path.dirname(self.view.file_name()),
            open_file=False)
        self.view.run_command("insert", {"characters":'| ' + new_node['id'] + ' >'})
        self.view.run_command('save')  # TODO insert notification

class DeleteThisNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        if self.view.file_name():
            self._UrtextProjectList.delete_file(self.view.file_name())

class InsertTimestampCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self._UrtextProjectList.current_project.editor_insert_timestamp()

class GoToDynamicDefinitionCommand(UrtextTextCommand):
    @refresh_project_text_command()
    def run(self):
        target_id = get_node_id(self.view)
        self._UrtextProjectList.current_project.go_to_dynamic_definition(target_id)

class UrtextReloadProjectCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        if initialize_project_list(self.window, reload_projects=True) == None:
            print('No Urtext Project')
            return None

class CompactNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        region = self.view.sel()[0]
        line_region = self.view.line(region) # full line region
        line_contents = self.view.substr(line_region)

        if match_compact_node(line_contents):
            contents = self._UrtextProjectList.current_project.add_compact_node()
            next_line_down = line_region.b
            self.view.sel().clear()
            self.view.sel().add(next_line_down) 
            self.view.run_command("insert_snippet",{"contents": '\n'+contents})
        else:
            contents = line_contents.strip()
            indent = ''
            pos = 0
            if len(line_contents):
                while line_contents[pos].isspace() and pos < len(line_contents) - 1:
                    indent = ''.join([indent, line_contents[pos]])
                    pos = pos + 1
            contents = self._UrtextProjectList.current_project.add_compact_node(
                contents=contents)
            region = self.view.sel()[0]
            self.view.erase(self.edit, line_region)
            self.view.run_command("insert_snippet",{"contents": indent + contents})         

class RandomNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self._UrtextProjectList.current_project.random_node()

class ToNextNodeCommand(UrtextTextCommand):
    @refresh_project_text_command()
    def run(self):
        next_wrapper = self.view.find(r'|'.join([
                syntax.opening_wrapper,
                syntax.bullet,
                syntax.node_pointer
            ]),
            self.view.sel()[0].a + 1)
        if next_wrapper:
            self.view.sel().clear()
            self.view.sel().add(next_wrapper.a) 
            position_node(next_wrapper.a)

class ToPreviousNodeCommand(UrtextTextCommand):
    @refresh_project_text_command()
    def run(self):
        all_previous_opening_wrappers = [r.a for r in self.view.find_all(
            '|'.join([
                syntax.opening_wrapper,
                syntax.bullet,
                syntax.node_pointer
            ])) if r.a < self.view.sel()[0].a]
        if all_previous_opening_wrappers:
            self.view.sel().clear()
            self.view.sel().add(all_previous_opening_wrappers[-1])
            position_node(all_previous_opening_wrappers[-1])

class FileOutlineDropdown(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        if self._UrtextProjectList.current_project and (
            self.view.file_name() in self._UrtextProjectList.current_project.files):
            ordered_file_nodes = self._UrtextProjectList.current_project.files[
                self.view.file_name()].get_ordered_nodes()

            self.menu = NodeBrowserMenu(
                self._UrtextProjectList,
                project=self._UrtextProjectList.current_project,
                nodes=ordered_file_nodes)

            self.menu.display_menu = ['  ' * n.nested + n.id for n in ordered_file_nodes]
            self.selection_has_changed = False
            show_panel(
                self.view.window(), 
                self.menu.display_menu, 
                self.open_the_node,
                on_highlight=self.on_highlight)

    def open_the_node(self, index):
        node = self.menu.menu[index]
        self._UrtextProjectList.current_project.open_node(node.id) 

    def on_highlight(self, index):
        if self.selection_has_changed:
            preview_urtext_node(self.menu.menu[index].id)
        else:
            self.selection_has_changed = True  

"""
Utility functions
"""

def preview_urtext_node(node_id):
    window = sublime.active_window()
    if _UrtextProjectList.current_project:
        filename, node_position = _UrtextProjectList.current_project.get_file_and_position(node_id)
        if filename:
            window.open_file(filename, flags=sublime.TRANSIENT)
            preview = window.active_sheet().view()

            def focus_position(focus_view, position):
                if not focus_view.is_loading():
                    if focus_view.window():
                        position_node(position, focus=False, view=focus_view)
                else:
                    sublime.set_timeout(lambda: focus_position(focus_view, position), 50) 
            
            focus_position(preview, node_position)

def highlight_region(view, node_range):
    view.add_regions(
        'highlight',
        [sublime.Region(node_range[0], node_range[1])],
        scope="region.yellowish")
    sublime.set_timeout(
        lambda: view.erase_regions('highlight'), 
        200)
            
def position_node(position, focus=True, view=None): 
    if not view:
        window = sublime.active_window()
        if window: view = window.active_view()
    if view:
        if focus:
            view.sel().clear()
            view.sel().add(sublime.Region(position, position))
        r = view.text_to_layout(position)
        view.show_at_center(position, animate=True)

def get_line_and_cursor(view):
    file_pos = view.sel()[0].a
    col_pos = view.rowcol(file_pos)[1]
    full_line_region = view.line(view.sel()[0])
    full_line = view.substr(full_line_region)
    return full_line, col_pos

def get_node_id(view):
    global _UrtextProjectList
    if not len(view.sel()):
        return
    if _UrtextProjectList and _UrtextProjectList.current_project and view.file_name():
        position = view.sel()[0].a
        filename = view.file_name()
        return _UrtextProjectList.current_project.get_node_id_from_position(filename, position)
