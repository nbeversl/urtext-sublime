import sublime
import sublime_plugin
import os
import Urtext.urtext as Urtext
import re
import datetime

class GenerateTimelineCommand(sublime_plugin.TextCommand):
    """ List snippets of files in a timeline """
    def run(self,edit):
        found_stuff = []
        files = Urtext.get_all_files(self.view.window())
        path = Urtext.get_path(self.view.window())
        for file in files:
          with open(os.path.join(path, file),'r',encoding='utf-8') as theFile:
            full_contents = theFile.read()
            timestamp_regex = '<((?:Sat|Sun|Mon|Tue|Wed|Thu|Fri)\., (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\. \d{2}, \d{4},\s+\d{2}:\d{2} (?:AM|PM))>'
            timestamps = re.findall(timestamp_regex, full_contents)
            for timestamp in timestamps:
              contents = full_contents # reset the contents
              found_thing = {}
              try:
                datetime_obj = datetime.datetime.strptime(timestamp,'%a., %b. %d, %Y, %I:%M %p')
              except:
                datetime_obj = datetime.datetime.strptime(timestamp,'%A, %B %d, %Y, %I:%M %p')
              position = contents.find(timestamp)
              meta_separator = '------------'
              if meta_separator in contents[0:position]:# this is a meta timestamp      
                contents = contents.split(meta_separator)[0]
                relevant_text = contents[:100]  # pull the beginning of the file
                found_thing['filename'] = file
                found_thing['kind'] = 'meta'     
              else: # this is an inline timestamp          
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
        sorted_stuff = sorted(found_stuff, key=lambda x: x['date'], reverse=True)
        new_view = self.view.window().new_file()
        new_view.set_name('Timeline')
        new_view.set_scratch(True)
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
