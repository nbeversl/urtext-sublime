from .sublime_urtext import refresh_project_event_listener, refresh_project_text_command
from .sublime_urtext import size_to_groups, size_to_thirds
from .sublime_urtext import UrtextTextCommand
from sublime_plugin import EventListener
from urtext_sublime.urtext.project import node_id_regex
import sublime
from .sublime_urtext import refresh_project_text_command, refresh_project_event_listener
import re
import os

class ToggleTraverse(UrtextTextCommand):

	@refresh_project_text_command()
	def run(self):

		# determine whether then view already has traverse settings attached
		# if already on, turn it off
		if self.view.settings().has('traverse'):
			if self.view.settings().get('traverse') == 'true':
				self.view.settings().set('traverse', 'false')
				self.view.set_status('traverse', 'Traverse: Off')
				groups = self.view.window().num_groups()
				groups -= 1
				if groups == 0:
					groups = 1
				size_to_groups(groups, self.view)
				self.view.settings().set("word_wrap", True)
				return

		# otherwise, if 'traverse' is not in settings or it's 'false',
		# turn it on.
		self.view.settings().set('traverse', 'true')
		self.view.set_status('traverse', 'Traverse: On')

		#
		# Add another group to the left if needed
		#
		groups = self.view.window().num_groups() # 1-indexed
		active_group = self.view.window().active_group()  # 0-indexed
		if active_group + 1 == groups:
			groups += 1
		#size_to_groups(groups, self.view)
		size_to_thirds(groups,self.view)
		self.view.settings().set("word_wrap", False)

		#
		# move any other open tabs to rightmost pane.
		#

		views = self.view.window().views_in_group(active_group)
		index = 0
		for view in views:
			if view != self.view:
				self.view.window().set_view_index(
					view,
					groups - 1,  # 0-indexed from 1-indexed value
					index)
				index += 1

		self.view.window().focus_group(active_group)


class TraverseFileTree(EventListener):

	@refresh_project_event_listener
	def on_selection_modified(self, view):
		
		if not self._UrtextProjectList or not self._UrtextProjectList.current_project:
			return

		# give this view a name since we have so many to keep track of
		called_from_view = view 
		if called_from_view.name() == 'urtext_history':
			return
		#
		# TODO:
		# Add a failsafe in case the user has closed the next group to the left
		# but traverse is still on.
		#
		if called_from_view.window() == None:
			return
		if called_from_view.settings().get('traverse') == 'false':
			return

		# 1-indexed number of current groups ("group" = window division)
		self.groups = called_from_view.window().num_groups()        

		# 0-indexed number of the group with the tree view
		# Tree group is always made to be the view this was called from.
		self.tree_group = called_from_view.window().active_group() 
		if called_from_view.window().active_group() + 1 == self.groups:
			# if the called_from_group is rightmost, return
			# OR what if checking to see if the filenames are the same?
			return

		# 0-indexed number of the group with the content 
		# (may not yet exist)
		self.content_group = self.tree_group + 1        
		
		# TAB of the content (right) view. ("sheet" = tab)        
		self.content_tab = called_from_view.window().active_sheet_in_group(self.tree_group)
	  
		# the contents of the content tab. 
		contents = view.substr(sublime.Region(0, view.size()))

		""" 
		Scroll to a given position of the content 
		and then return focus to the tree view.
		"""
		def move_to_location(moved_view, 
			position, 
			tree_view):
			
			if not moved_view.is_loading():

				# focus on the window division with the content
				moved_view.window().focus_group(self.content_group)

				# show the content tab with the given position as top=				
				self.content_tab.view.sel().clear()
				self.content_tab.view.sel().add(sublime.Region(position, position))
				r = self.content_tab.view.text_to_layout(position)
				self.content_tab.view.set_viewport_position(r)

				# Make this the selected spot and set word wrap
				moved_view.sel().clear()
				moved_view.sel().add(position)
				moved_view.settings().set("word_wrap", "auto")

				# refocus the tree (left) view
				self.return_to_left(moved_view, tree_view)

			else:
				sublime.set_timeout(lambda: move_to_location(moved_view, position), 10)

		""" Only if Traverse is on for this group (window division) """

		if called_from_view.settings().get('traverse') == 'true':

			# the tree view is always the view that was modified.
			# assign it a name, get its filename and window

			this_file = called_from_view.file_name()
			
			if not this_file:
				return

			tree_view = called_from_view
			window = called_from_view.window()

			# Get the current line and find links
			full_line = view.substr(view.line(view.sel()[0]))
			links = re.findall('>' + node_id_regex, full_line)

			# if there are no links on this line:
			if len(links) == 0:  
				return

			# get all the filenames corresponding to the links
			filenames = []
			for link in links:
				filename = self._UrtextProjectList.current_project.get_file_name(link[1:])
				if filename:
					filenames.append(filename)

			if len(filenames) > 0 and link[1:] in self._UrtextProjectList.current_project.nodes:
				filename = filenames[0]
				position = self._UrtextProjectList.current_project.nodes[link[1:]].ranges[0][0]
				
				""" If the tree is linking to another part of its own file """
				if filename == os.path.basename(this_file):
					
					instances = self.find_filename_in_window(
						os.path.join(self._UrtextProjectList.current_project.path, filename), window)

					# Only allow two total instances of this file; 
					# one to navigate, one to edit
					if len(instances) < 2:
						window.run_command("clone_file")
						duplicate_file_view = self.find_filename_in_window(
							os.path.join(self._UrtextProjectList.current_project.path, filename),
							window)[1]

					if len(instances) >= 2:
						duplicate_file_view = instances[1]
					
					""" If the duplicate view is in the content group """
					if duplicate_file_view in window.views_in_group(self.content_group):
						window.focus_view(duplicate_file_view)
						
						duplicate_file_view.sel().clear()
						duplicate_file_view.sel().add(sublime.Region(position, position))
						r = duplicate_file_view.text_to_layout(position)
						duplicate_file_view.set_viewport_position(r)
						
						self.return_to_left(duplicate_file_view, tree_view)
						duplicate_file_view.settings().set('traverse', 'false')
						return

					""" If the duplicate view is in the tree group """
					if duplicate_file_view in window.views_in_group(self.tree_group):
						window.focus_group(self.tree_group)
						duplicate_file_view.settings().set('traverse', 'false')  # this is for the cloned view
						window.set_view_index(duplicate_file_view, self.content_group, 0)

						duplicate_file_view.sel().clear()
						duplicate_file_view.sel().add(sublime.Region(position, position))
						r = duplicate_file_view.text_to_layout(position)
						duplicate_file_view.set_viewport_position(r)

						window.focus_view(tree_view)
						window.focus_group(self.tree_group)
						self.restore_traverse(view, tree_view)
						return

				else:
					""" The tree is linking to another file """
					path = self._UrtextProjectList.current_project.path
					window.focus_group(self.content_group)
					file_view = window.open_file(os.path.join(path, filename),
												 sublime.TRANSIENT)

					file_view.sel().clear()
					file_view.sel().add(sublime.Region(position, position))
					r = file_view.text_to_layout(position)
					file_view.set_viewport_position(r)

					file_view.sel().add(position)
					window.focus_group(self.tree_group)
					self.return_to_left(file_view, tree_view)

	def find_filename_in_window(self, filename, window):
		instances = []
		for view in window.views():
			if view.file_name() == filename:
				instances.append(view)
		return instances

	def restore_traverse(self, wait_view, traverse_view):
		if not wait_view.is_loading():
			traverse_view.settings().set('traverse', 'true')
		else:
			sublime.set_timeout(
				lambda: self.return_to_left(wait_view, traverse_view), 10)
			return

	""" 
	Return to the left (tree) view,
	after waiting for another view to finish loading.
	"""

	def return_to_left(self, 
		wait_view, 
		return_view):
		
		if not wait_view.window():
			return

		if not wait_view.is_loading():
			wait_view.window().focus_view(return_view)
			wait_view.window().focus_group(self.tree_group)
		
		else:
			sublime.set_timeout(lambda: self.return_to_left(wait_view, return_view), 10)