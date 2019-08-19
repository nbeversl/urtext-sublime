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
import datetime

# this is only showing nodes with timestamps. shouldn't it also read them from the Node IDs?


def timeline(project, nodes):
    """ given an Urtext Project and nodes, generates a timeline """
    found_stuff = []
    for node in nodes:
        full_contents = project.nodes[node.id].content_only()

        timestamp_regex = '<((?:Sat|Sun|Mon|Tue|Wed|Thu|Fri)\., (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\. \d{2}, \d{4},\s+\d{2}:\d{2} (?:AM|PM))>'
        timestamps = re.findall(timestamp_regex, full_contents)
        id_date = node.date
        contents = full_contents
        found_thing = {}
        found_thing['filename'] = node.id
        found_thing['kind'] = 'from Node ID'
        found_thing['date'] = id_date
        found_thing['contents'] = contents[:150]
        found_stuff.append(found_thing)

        for timestamp in timestamps:
            contents = full_contents
            found_thing = {}
            try:
                datetime_obj = datetime.datetime.strptime(
                    timestamp, '%a., %b. %d, %Y, %I:%M %p')
            except:
                datetime_obj = datetime.datetime.strptime(
                    timestamp, '%A, %B %d, %Y, %I:%M %p')
            position = contents.find(timestamp)
            lines = contents.split('\n')
            for num, line in enumerate(lines, 1):
                if timestamp in line:
                    line_number = num
            if len(contents) < 150:
                relevant_text = contents
            elif position < 150:
                relevant_text = contents[:position + 150]
            elif len(contents) < 300:
                relevant_text = contents[position - 150:]
            else:
                relevant_text = contents[position - 150:position +
                                         150]  # pull the nearby text
            relevant_text = relevant_text.replace('<' + timestamp + '>',
                                                  '[ ...STAMP... ]')

            found_thing['filename'] = node.id + ':' + str(line_number)
            found_thing['kind'] = 'as inline timestamp '
            found_thing['date'] = datetime_obj
            found_thing['contents'] = relevant_text
            found_stuff.append(found_thing)

    sorted_stuff = sorted(found_stuff, key=lambda x: x['date'], reverse=True)
    start_date = sorted_stuff[0]['contents']
    timeline = ''
    for index in range(0, len(sorted_stuff) - 1):
        entry_date = sorted_stuff[index]['date'].strftime(
            '%a., %b. %d, %Y, %I:%M%p')
        contents = sorted_stuff[index]['contents'].strip()
        while '\n\n' in contents:
            contents = contents.replace('\n\n', '\n')
        contents = '      ...' + contents.replace(
            '\n', '\n                   |      ') + '...   '
        timeline += '                   |<----' + entry_date + ' ' + sorted_stuff[
            index]['kind']
        timeline += ' >' + sorted_stuff[index][
            'filename'] + '\n                   |\n                   |'
        timeline += contents + '\n                   |\n'
        num_days = sorted_stuff[index]['date'].day - sorted_stuff[
            index + 1]['date'].day
        next_day = sorted_stuff[index]['date'] + datetime.timedelta(days=-1)
        for empty_day in range(0, num_days):
            timeline += next_day.strftime('%a. %b. %d, %Y') + ' |\n'
            next_day += datetime.timedelta(days=-1)

    return timeline
