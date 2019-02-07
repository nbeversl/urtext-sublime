# Module to handle reverse dating of filenames

# Meta -> /Users/nathanielbeversluis/Library/Application Support/Sublime Text 3/Packages/Urtext/meta.py:7

import sublime
import sublime_plugin
import datetime
import Urtext.meta
import Urtext.urtext
import os

timestamp_format = '<%a., %b. %d, %Y, %I:%M %p>'
alt_timestamp_formats = [
    '< >', ]
settings = sublime.load_settings('urtext-default.sublime-settings')
# path = settings.get('urtext_folder') # not needed in this module <Thu., Feb. 07, 2019, 02:25 PM>
# = 12 dashes in a row starting a line, followed by a newline
meta_separator = settings.get('meta_separator')


class ShowReverseDateFilenameCommand(sublime_plugin.TextCommand):
    """
    Takes the timestamp-formatted date highlighted and converts it into a reverse-dated
    filename which is copied to the clipboard. For file naming.
    """

    def run(self, edit):
        for region in self.view.sel():
            text = self.view.substr(region)
            try:
                print(text)
                date = datetime.datetime.strptime(text, timestamp_format)
                sublime.set_clipboard(make_reverse_date_filename(date))
                self.view.show_popup(
                    'Reverse-dated filename copied to clipboard.')
            except:
                self.view.show_popup('Error.')


# copies the file to a new node with a backreference.
class UpdateFileCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        contents = self.view.substr(sublime.Region(0, self.view.size()))
        self.contents = Urtext.meta.clear_meta(contents)
        old_filename = self.view.file_name()
        self.old_filename = old_filename.split('/')[-1]
        now = datetime.datetime.now()
        new_filename = make_reverse_date_filename(now)
        self.view.insert(edit, self.view.size(), '\npulled to: -> '+new_filename +
                         '  | (editorial://open/'+new_filename+'?root=dropbox) ' + now.strftime(timestamp_format))
        self.view.run_command('save')
        window = self.view.window()
        new_view = window.open_file(new_filename)
        sublime.set_timeout(lambda: self.add_content(new_view), 10)

    # https://forum.sublimetext.com/t/wait-until-is-loading-finnish/12062/5
    def add_content(self, view):
        if not view.is_loading():
            view.run_command("insert_snippet", {"contents": self.contents})
            now = datetime.datetime.now()
            Urtext.meta.add_created_timestamp(view, now)
            view.run_command("move_to", {"to": "eof"})
            view.run_command("insert_snippet", {
                             "contents": "pulled from: -> "+self.old_filename + " | (editorial://open/"+self.old_filename+"?root=dropbox)"})
            view.run_command("move_to", {"to": "bof"})
            view.run_command('save')
        else:
            sublime.set_timeout(lambda: self.add_content(view), 10)


class NewUndatifiedFileCommand(sublime_plugin.WindowCommand):
    """
    Creates a new file with reverse-dated filename and initial metadata
    """

    def run(self):
        if self.window.project_data():
            # always save in the current project path if there is one
            path = self.window.project_data()['folders'][0]['path']
        else:
            path = '.'
        now = datetime.datetime.now()
        new_view = self.window.open_file(
            path+'/'+make_reverse_date_filename(now))
        sublime.set_timeout(lambda: self.add_meta(new_view, now), 10)

    def add_meta(self, view, now):
        if not view.is_loading():
            Urtext.meta.add_created_timestamp(view, now)
            Urtext.meta.add_original_filename(view)
            view.run_command("insert_snippet", {
                             "contents": "\n\n\n"})  # (whitespace)
            view.run_command("move_to", {"to": "bof"})
        else:
            sublime.set_timeout(lambda: self.add_meta(view, now), 10)


class ReFile(sublime_plugin.TextCommand):
    def run(self, edit):
        now = datetime.datetime.now()


def make_reverse_date_filename(date):
    unyear = 10000 - int(date.strftime('%Y'))
    unmonth = 12 - int(date.strftime('%m'))
    unday = 31 - int(date.strftime('%d'))
    unhour = 23 - int(date.strftime('%H'))
    unminute = 59 - int(date.strftime('%M'))
    unsecond = 59 - int(date.strftime('%S'))
    undatetime = "{:04d}{:02d}{:02d}{:02d}{:02d}{:02d}.txt".format(
        unyear, unmonth, unday, unhour, unminute, unsecond)
    return undatetime


def date_from_reverse_date(undate):
    """
    This gets a datetime object back from reverse-dated filenames
    """
    year = 10000 - int(undate[0:4])
    month = 12 - int(undate[4:6])
    day = 31 - int(undate[6:8])
    hour = 23 - int(undate[8:10])
    minute = 59 - int(undate[10:12])
    second = 59 - int(undate[12:14])
    date = datetime.datetime(year, month, day, hour, minute, second)
    return date
