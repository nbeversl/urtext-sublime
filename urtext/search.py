# -*- coding: utf-8 -*-
"""
This file is part of Urtext.

Urtext is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Urtext is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Urtext.  If not, see <https://www.gnu.org/licenses/>.

"""
import re
from .dynamic_output import DynamicOutput

def search_term(self, term):
	return UrtextSearch(self, term)

class UrtextSearch:

	def __init__(self, 
		project, 
		term, 
		amount=None,
		format_string=None):
		
		self.project = project
		self.term = term
		self.complete = False
		self.result = []
		self.amount = 20
		if not format_string:
			self.format_string = '$contents $link';
		else:
			self.format_string = format_string
	
	def initiate_search(self):
		return self._search_for(self.term)
		
	def _search_for(self, term):
		term = term.lower()
		term_length = len(term)
		for node_id in self.project.nodes:
			if self.project.nodes[node_id].dynamic:
				continue
			matches = []
			contents = self.project.nodes[node_id].content_only()
			lower_contents = contents.lower()			

			if term in lower_contents:

				this_result = DynamicOutput(self.format_string)

				if this_result.needs_title:
					this_result.title = self.project.nodes[node_id].title

				if this_result.needs_link:
					this_result.link = '>'+node_id

				if this_result.needs_contents:
					for match in re.finditer(term, lower_contents):
						start = match.start() - self.amount
						if start < 0 :
							start = 0
						end = match.end() + self.amount
						if end > len(contents):
							end = len(contents)
						excerpt = contents[start:end].replace('\n',' ')
					this_result.contents = excerpt

				if this_result.needs_meta:
					this_result.meta = self.project.nodes[node_id].consolidate_metadata()

				if this_result.needs_date:
					this_result.date = self.project.nodes[node_id].date

				self.result.append(this_result.output())				

		self.complete = True
		return self.result

search_functions  = [ search_term ]