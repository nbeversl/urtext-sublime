import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
	from Urtext.urtext.extension import UrtextExtension
else:
	from urtext.extension import UrtextExtension

class UrtextNavigation(UrtextExtension):

	name = ["NAVIGATION"]

	def __init__(self, project):
		self.project_list = project.project_list
		if 'NAVIGATION' not in project.project_list.extensions:
			project.project_list.extensions['NAVIGATION'] = self
			self.project_list_instance = project.project_list.extensions['NAVIGATION']
			self.project_list_instance.navigation = []
			self.project_list_instance.nav_index = -1
			self.project_list_instance.triggered_node_visit = False
		self.project_list_instance = project.project_list.extensions['NAVIGATION']

	def forward(self):

		if self.project_list_instance:
			
			if self.project_list_instance.nav_index == -1:
				self.project_list_instance.nav_index = 1
			else: 
				self.project_list_instance.nav_index += 1

			if self.project_list_instance.nav_index == len(
				self.project_list_instance.navigation):
					self.project_list_instance.nav_index -= 1			
					return print('index is already at the end')

			project, next_node = self.project_list_instance.navigation[
				self.project_list_instance.nav_index]
			self.project_list.set_current_project(project)
			self.project_list_instance.triggered_node_visit = True
			self.project_list.current_project.open_node(next_node)

	def reverse(self):
		if not self.project_list_instance.navigation:
			return print('no nav history')
		if self.project_list_instance.nav_index > -1:
			self.project_list_instance.nav_index -= 1
		if self.project_list_instance.nav_index == -1:
			return print('index is already at the beginning.')
		project, previous_node = self.project_list_instance.navigation[
			self.project_list_instance.nav_index]
		self.project_list.set_current_project(project)
		self.project_list_instance.triggered_node_visit = True
		self.project_list.current_project.open_node(previous_node)

	def on_node_visited(self, node_id):
		if self.project_list_instance.triggered_node_visit:
			self.project_list_instance.triggered_node_visit = False
			return
	
		if node_id in self.project_list.current_project.nodes:
			if self.project_list_instance.navigation:
				project, last_id = self.project_list_instance.navigation[
					self.project_list_instance.nav_index]
			else:
				project = self.project_list.current_project
				last_id = None

			# don't re-remember consecutive duplicate links
			if (-1 < self.project_list_instance.nav_index < len(
				self.project_list_instance.navigation) and 
				node_id == last_id): 
				return
			# add the newly opened file as the new "HEAD"
			self.project_list_instance.nav_index += 1
			del self.project_list_instance.navigation[
				self.project_list_instance.nav_index:]
			self.project_list_instance.navigation.append((
				self.project_list.current_project.settings['project_title'],
				node_id))

	def on_file_deleted(self, filename):
		return self.reverse()

	def on_node_id_changed(self, old_id, new_id):
		for index, item in enumerate(
			self.project_list_instance.navigation):
			project = item[0]
			node_id = item[1]
			if project == self.project_list.current_project.settings[
				'project_title'] and ( 
				node_id == old_id):
					self.project_list_instance.navigation[
						index] = (project, new_id)
