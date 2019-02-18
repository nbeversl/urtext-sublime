# Urtext - Main

import sublime
import sublime_plugin
import os
import re
from datetime import datetime
import Urtext.datestimes
import Urtext.meta
import copy
import sys
sys.path.append(os.path.join(os.path.dirname(__file__)))
from anytree import Node, RenderTree

settings = sublime.load_settings('urtext-default.sublime-settings')
path = settings.get('urtext_folder')
meta_separator = settings.get('meta_separator')

class MyListener(sublime_plugin.ViewEventListener):
    def is_applicable(settings):     
      settings.set('file_view','True')
      if settings.get('file_view') == 'True':
        return True
      return False

    def on_selection_modified_async(self):

      s = Urtext.meta.NodeMetadata(self.view.file_name())
      tags = s.get_tag('tags')
      try:
        if 'file_tree' in tags[0]:
        # TODO : fix that tags has to be indexed
          full_line = self.view.substr(self.view.line(self.view.sel()[0]))
          link = re.findall('->\s+([\w\.\/]+)',full_line)
          path = get_path(self.view)
          try:
            window = self.view.window()
            window.set_layout({"cols":[0,0.5,1], "rows": [0,1], "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]})
            window.focus_group(1)
            window.open_file(link[0])
            window.focus_group(0)
          except: 
            pass
      except:
        pass
  
def get_path(view):
  if view.window().project_data():
    path = view.window().project_data()['urtext_path'] # ? 
  else:
    path = '.'
  return path

class CopyPathCoolerCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    filename = self.view.window().extract_variables()['file_name']
    self.view.show_popup('`'+filename + '` copied to the clipboard')
    sublime.set_clipboard(filename)

class GenerateTimelineCommand(sublime_plugin.TextCommand):
    """ List snippets of files in a timeline """
    def run(self,edit):
        found_stuff = []
        view = self.view
        self.window = view.window()
        path = get_path(view)
        files = os.listdir(path)
        for file in files:
          file=file.split('/')[-1] # need to fix all this path nonsense.
          try:
            with open(path + '/' + file, 'r', encoding='utf-8') as theFile:
              full_contents = theFile.read()
              timestamp_regex = '\<(.*?)\>'
              timestamps = re.findall(timestamp_regex, full_contents)
              for timestamp in timestamps:
                contents = full_contents # reset the contents
                found_thing = {}
                try:
                  try:
                    datetime_obj = datetime.strptime(timestamp,'%a., %b. %d, %Y, %I:%M %p')
                  except:
                    datetime_obj = datetime.strptime(timestamp,'%A, %B %d, %Y, %I:%M %p')
                  position = contents.find(timestamp)
                  # TWO KINDS of timestamps: meta and inline 
                  # inline:
                  global meta_separator
                  if meta_separator in contents[0:position]:
                    # this is a meta timestamp
                    contents = contents.split(meta_separator)[0]
                    relevant_text = contents[:100]  # pull the beginning of the file
                    found_thing['filename'] = file
                    found_thing['kind'] = 'meta'
                  else:
                    # this is an inline timestamp
                    contents = contents.split(meta_separator)[0]
                    theFile.seek(0)
                    for num, line in enumerate(theFile, 1):
                      if timestamp in line: 
                        line_number = num
                    if len(contents) < 150:
                       relevant_text = contents
                    elif position < 150:
                       relevant_text = contents[:position+150]
                    elif len(contents) < 300:
                       relevant_text = contents[position-150:]
                    else:
                       relevant_text = contents[position-150:position+150] # pull the nearby text
                    relevant_text = relevant_text.replace('<'+timestamp+'>','[ ...STAMP... ]')
                    found_thing['filename'] = file+':'+str(line_number)
                    found_thing['kind'] = 'inline'
                  found_thing['date'] = datetime_obj
                  found_thing['contents'] = relevant_text
                  found_stuff.append(found_thing)
                except:
                  pass
          except:
            pass
        sorted_stuff = sorted(found_stuff, key=lambda x: x['date'], reverse=True)
        new_view = self.window.new_file()
        new_view.set_name('Timeline')
        sublime.set_timeout(lambda: self.show_stuff(new_view, sorted_stuff), 10)

    def build_timeline(self,view, sorted_stuff):
        view.run_command("append", {"characters": '|\n|'})
        for entry in sorted_stuff:
          entry_date = entry['date'].strftime('%a., %b. %d, %Y, %I:%M%p')
          contents = entry['contents'].strip()
          while '\n\n' in contents:
            contents = contents.replace('\n\n','\n')          
          contents = '      ...'+contents.replace('\n','\n|      ')+'...   '
          view.run_command("append", {"characters": '\n|<----'+entry_date+' found as '+entry['kind']})
          view.run_command("append", {"characters": ' in file -> '+entry['filename']+'\n|\n|'})
          view.run_command("append", {"characters": contents+'\n|'})

    def show_stuff(self, view, sorted_stuff):
          if not view.is_loading(): 
            self.build_timeline(view, sorted_stuff)
          else:
            sublime.set_timeout(lambda: self.show_stuff(view,sorted_stuff), 10)
          #https://forum.sublimetext.com/t/how-to-print-text-on-the-output-panel/35226/2

class ShowFilesWithPreview(sublime_plugin.WindowCommand):
    def run(self):
        path = get_path(self.window.active_view())
        files = os.listdir(path)
        print(path)
        print(files)
        menu = []
        for filename in files:
          print(filename)
          print(os.path.join(path, filename))
          item = []       
          try: 
            metadata = Urtext.meta.NodeMetadata(os.path.join(path, filename))
            item.append(metadata.get_tag('title')[0])  # should title be a list or a string?            
            item.append(Urtext.datestimes.date_from_reverse_date(filename[:13]))
            item.append(metadata.filename)
            menu.append(item)
          except:
            pass # probably not a .txt file
        self.sorted_menu = sorted(menu,key=lambda item: item[1], reverse=True )
        self.display_menu = []
        for item in self.sorted_menu: # there is probably a better way to copy this list.
          new_item = [item[0], item[1].strftime('<%a., %b. %d, %Y, %I:%M %p>')]
          self.display_menu.append(new_item)
        def open_the_file(index):
          if index != -1:
            new_view = self.window.open_file(self.sorted_menu[index][2])
        self.window.show_quick_panel(self.display_menu, open_the_file)

class LinkToNodeCommand(sublime_plugin.WindowCommand): # almost the same code as show files. Refactor.
    def run(self):
        path = get_path(self.window.active_view())
        files = os.listdir(path)
        menu = []
        for filename in files:
          item = []       
          try:
            metadata = Urtext.meta.NodeMetadata(path+'/'+filename)
            item.append(metadata.get_tag('title')[0])  # should title be a list or a string?            
            item.append(Urtext.datestimes.date_from_reverse_date(filename[:13]))
            item.append(metadata.filename)
            menu.append(item)
          except:
            pass # probably not a .txt file
        self.sorted_menu = sorted(menu,key=lambda item: item[1], reverse=True )
        self.display_menu = []
        for item in self.sorted_menu: # there is probably a better way to copy this list.
          new_item = [item[0], item[1].strftime('<%a., %b. %d, %Y, %I:%M %p>')]
          self.display_menu.append(new_item)
        def link_to_the_file(index):
          view = self.window.active_view()
          file = self.sorted_menu[index][2].split('/')[-1]
          title = self.sorted_menu[index][0]
          view.run_command("insert", {"characters": title + ' -> '+ file + ' | '})
        self.window.show_quick_panel(self.display_menu, link_to_the_file)


class ShowTags(sublime_plugin.WindowCommand):
    def run(self):
        def clear_white_space(text):
          text = text.strip()
          text = " ".join(text.split()) #https://stackoverflow.com/questions/8270092/remove-all-whitespace-in-a-string-in-python
          return text
        path = get_path(view)
        files = os.listdir(path)
        tags = []
        for filename in files:
          try:
            with open(path+'/'+filename,'r',encoding='utf-8') as this_file:
              contents = this_file.read()
              metadata = Urtext.meta.get_meta(contents)
              for entry in metadata:
                if 'tags' in entry:
                  for tag in entry['tags']:
                    tags.append(tag)              
            menu.append(item)
          except:
            pass
        self.sorted_menu = sorted(menu,key=lambda item: item[1] )
        def open_the_file(index):
          if index != -1:
            self.window.open_file(path+"/"+self.sorted_menu[index][1])
        self.window.show_quick_panel(self.sorted_menu, open_the_file)


def get_contents(view):
  contents = view.substr(sublime.Region(0, self.view.size()))
  return contents
