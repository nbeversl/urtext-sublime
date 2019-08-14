import editor
import re
import os
import time
import sys
import dialogs
import datetime
import dropbox
import contextlib
parent_dir = os.path.dirname(__file__)
sys.path.append(parent_dir)

from urtext.project import UrtextProject
from urtext.node import UrtextNode

from watchdog.events import FileSystemEventHandler
import watchdog
from watchdog.observers import Observer

command = sys.argv[1]
node_id_regex = r'\b[0-9,a-z]{3}\b'


class UrtextWatcher(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.project = _UrtextProject = UrtextProject(urtext_project_path)

    def on_created(self, event):
        if event.is_directory:
            return None

        filename = os.path.basename(event.src_path)
        if self.project.parse_file(filename) == None:
            self.project.log.info(filename + ' not added.')
            return
        self.project.log.info(filename +
                              ' modified. Updating the project object')
        #self.project.update()

    def on_modified(self, event):
        if event.is_directory:
            return None
        filename = os.path.basename(event.src_path)
        if self.filter(filename) == None:
            return
        do_not_update = [
            self.project.nodes['zzz'].filename,
            self.project.nodes['zzy'].filename,
            self.project.settings['logfile'], '00000.txt'
        ]
        if filename in do_not_update or '.git' in filename:
            return

        self.project.log.info('MODIFIED ' + filename +
                              ' - Updating the project object')
        self.project.parse_file(filename)
        self.project.update()

    def on_deleted(self, event):
        filename = os.path.basename(event.src_path)
        self.project.log.info(filename + ' DELETED')
        if filename in self.project.files:
            self.project.remove_file(filename)

    def on_moved(self, event):
        if self.filter(event.src_path) == None:
            return
        old_filename = os.path.basename(event.src_path)
        new_filename = os.path.basename(event.dest_path)
        if old_filename in self.project.files:
            self.project.log.info('RENAMED' + old_filename + ' to ' +
                                  new_filename)
            self.project.handle_renamed(old_filename, new_filename)

    def filter(self, filename):
        for fragment in ['urtext_log', '.git', '.icloud']:
            if fragment in filename:
                return None
        return filename


def save_and_compile():
    current_file = editor.get_path()
    editor.open_file(current_file)  # this triggers a save of the current file
    event_handler.project.parse_file(
        current_file)  # parse and update explicitly
    event_handler.project.update()


def watch():
    global event_handler
    event_handler = UrtextWatcher()
    observer = Observer()
    observer.schedule(event_handler, path=urtext_project_path, recursive=False)
    observer.start()


def open_node(node_id):
    filename = event_handler.project.get_file_name(node_id)
    position = event_handler.project.nodes[node_id].position
    editor.open_file(os.path.join(urtext_project_path, filename))
    time.sleep(1)
    editor.set_selection(position, position + 20)


if 'event_handler' not in vars() or event_handler == None:
    watch()

if command == 'timestamp':
    now = datetime.datetime.now()
    datestamp = event_handler.project.timestamp(now)
    position = editor.get_selection()
    editor.replace_text(position[0], position[0], datestamp)

if command == 'tag':  ##?
    tag = sys.argv[1]
    contents = "/-- tags: " + tag + " --/"
    location = editor.get_selection()
    editor.replace_text(location[0], location[1], contents)

if command == 'open_link':
    save_and_compile()
    text = editor.get_text()
    line = editor.get_line_selection()
    selected_text = text[line[0]:line[1]]
    link = event_handler.project.get_link(selected_text)

    if link != None:
        del event_handler.project.navigation[event_handler.project.nav_index +
                                             1:]
        event_handler.project.navigation.append(link[1])

        # increment the index to match
        event_handler.project.nav_index += 1

        if link[0] == 'NODE':
            open_node(link[1])
        # HTTP links not yet handled in Pythonista

if command == "new_node":
    filename = event_handler.project.new_file_node(datetime.datetime.now())
    time.sleep(.5)
    editor.open_file(os.path.join(urtext_project_path, filename))
    time.sleep(.5)
    editor.set_selection(0)

if command == "home":
    save_and_compile()
    time.sleep(.75)
    node_id = event_handler.project.settings['home']
    filename = event_handler.project.nodes[node_id].filename
    editor.open_file(os.path.join(urtext_project_path, filename))

if command == "tag_from_other":
    text = editor.get_text()
    line = editor.get_line_selection()
    selected_text = text[line[0]:line[1]]
    node_id = re.search('>' + node_id_regex, selected_text).group(0)[1:]
    filename = event_handler.project.nodes[node_id].filename
    event_handler.project.tag_node(node_id, '/-- tags: done --/')
    event_handler.project.update()
    this_file = editor.get_path()
    editor.open_file(this_file)
    # then reload current file

if command == "search":
    string = dialogs.text_dialog()
    results = event_handler.project.search(string)
    editor.make_new_file('search_results', results)

if command == "node_list":
    save_and_compile()
    filename = event_handler.project.nodes['zzz'].filename
    editor.open_file(filename)

if command == "metadata_list":
    save_and_compile()
    filename = event_handler.project.nodes['zzy'].filename
    editor.open_file(filename)

if command == "back":

    # return if there are no saved locations
    if len(event_handler.project.navigation) == 0:
        print('There is no nav history')

    # return if the index is already at the beginning
    elif event_handler.project.nav_index == 0:
        print('index is already at the beginning.')

    else:
        # otherwise, move backwards one
        event_handler.project.nav_index -= 1

        # and open this node
        last_node = event_handler.project.navigation[
            event_handler.project.nav_index]
        position = event_handler.project.nodes[last_node].ranges[0][0]

        open_node(last_node)

if command == "forward":

    # return if there are no saved locations
    if len(event_handler.project.navigation) == 0:
        print('There is no more nav history')

    # return if the index is already at the end
    elif event_handler.project.nav_index == len(
            event_handler.project.navigation) - 1:
        print('index is already at the end.')

    else:
        # otherwise move it forward by one
        event_handler.project.nav_index += 1

        # and open this node
        last_node = event_handler.project.navigation[
            event_handler.project.nav_index]
        position = event_handler.project.nodes[last_node].ranges[0][0]
        open_node(last_node)

if command == "last":

    # return only if there are no saved locations
    if len(event_handler.project.navigation) == 0:
        print('There is no more nav history')

    else:

        # and open this node
        last_node = event_handler.project.navigation[
            event_handler.project.nav_index]
        position = event_handler.project.nodes[last_node].ranges[0][0]
        open_node(last_node)
