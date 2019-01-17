import sublime
import sublime_plugin
import time


def insert_timestamp(edit, time):
	for s in view.sel():
		if s.empty():
			view.insert(edit, s.a, time.strftime(fmt))
		else:
			view.replace(edit, s, time.strftime(fmt))

class UrtextTimestamp(sublime_plugin.TextCommand):
	def run(self, edit):
		insert_timestamp(edit, now)