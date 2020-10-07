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
# dependencies:
# googleapiclient
# httplib2
# uritemplate

# https://google-auth.readthedocs.io/en/latest/user-guide.html

# batch requests:
# http://googleapis.github.io/google-api-python-client/docs/epy/index.html

from googleapiclient.discovery import build
import datetime
import pytz
from google_auth_oauthlib.flow import InstalledAppFlow

def authenticate(project):  # originally from https://developers.google.com/calendar/quickstart/php
    
    # If modifying these scopes, delete the file token.json.
    SCOPES = 'https://www.googleapis.com/auth/calendar'

    flow = InstalledAppFlow.from_client_secrets_file(
                project.get_google_credentials(), SCOPES)

    creds = flow.run_local_server(port=0)

    service = build('calendar', 'v3', credentials=creds, cache_discovery=False)

    return service

def sync_project_to_calendar(project, calendar_id):

    service = authenticate(project)
    default_timezone = pytz.timezone(project.settings['default_timezone'])
    for node_id in project.nodes:
        node = project.nodes[node_id]

        date = node.date
        if date.tzinfo == None:
            date = default_timezone.localize(date)

        google_calendar_event = {
            'summary': node_id + ': ' + node.get_title(),
            'description': node.contents(),
            'start': {'dateTime': date.isoformat()},
            'end': {'dateTime': date.isoformat()}, }

        content = project.nodes[node_id].contents()
        event = service.events().insert(calendarId=calendar_id, body=google_calendar_event).execute()
        print ('Event created: %s' % (event.get('htmlLink')))

"""
not currently used
"""
"""
def get_google_auth_token(self):
    return os.path.join(self.path, self.settings['google_auth_token'])

def get_google_credentials(self):
    return os.path.join(self.path, 'credentials.json')

def get_service_account_private_key(self):
    return os.path.join(self.path, self.settings['google_service_account_private_key'])
def sync_to_google_calendar(self):
    google_calendar_id = self.settings['google_calendar_id']
    if not google_calendar_id:
        return
    sync_project_to_calendar(self, google_calendar_id)
"""