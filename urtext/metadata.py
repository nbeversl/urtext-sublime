import re
import datetime

class MetadataEntry: # container for a single metadata entry 
  def __init__(self, tag, value, dtstamp):
    self.tag_name = tag.strip()
    self.value = value
    self.dtstamp = dtstamp

  def log(self):
    print('tag: %s' % self.tag_name)
    print('value: %s' % self.value)
    print('datetimestamp: %s' % self.dtstamp)

class NodeMetadata: 
  def __init__(self, full_contents):
    self.entries = []
    meta = re.compile(r'\/-.+?-\/', re.DOTALL) # the problem is this regex.
    
    raw_meta_data = ''
    for section in re.findall(meta, full_contents):
      meta_block = section.replace('-/','')
      meta_block = meta_block.replace('/-','')
      raw_meta_data += meta_block + '\n'
    title_set = False
    if '------------' in full_contents: # remove later
      raw_meta_data += full_contents.split('------------')[-1] # add bottom of file metadata
    meta_lines = re.split(';|\n',raw_meta_data)
    date_regex = '<(Sat|Sun|Mon|Tue|Wed|Thu|Fri)., (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec). \d{2}, \d{4},\s+\d{2}:\d{2} (AM|PM)>'
    for line in meta_lines: 
      if line.strip() == '':
        continue
      date_match = re.search(date_regex,line)
      if date_match:
        datestamp_string = date_match.group(0)
        line = line.replace(datestamp_string, '').strip()
        date_stamp = datetime.datetime.strptime(datestamp_string, '<%a., %b. %d, %Y, %I:%M %p>')
      else:
        date_stamp = None
      if ':' in line:
        key = line.split(":")[0].strip()
        value = ''.join(line.split(":")[1:]).strip()
        if '|' in value:
          items = value.split('|')
          value = []
          for item in items:
             value.append(item.strip())
      else:
        key = '(no_key)'
        value = line.strip('-/')
      if key == 'title':
        title_set = True
        title = value
      self.entries.append(MetadataEntry(key, value, date_stamp))

    if title_set == False: # title is the the first many lines if not set
      full_contents = full_contents.strip()
      first_line = full_contents.split('\n')[0][:100].strip('{{')
      first_line = re.sub('\/-.+?-\/','',first_line)
      first_line = first_line.split('------------')[0]
      title = first_line.split('->')[0] # don't include links in the title, for traversing files clearly.
      self.entries.append(MetadataEntry('title', title, None)) # title defaults to first line. possibly refactor this.

  def get_tag(self, tagname):
    """ returns an array of values for the given tagname """ 
    values = []
    for entry in self.entries:
      if entry.tag_name.lower() == tagname.lower():
        values.append(entry.value) # allows for multiple tags of the same name
    return values

  def log(self):
    for entry in self.entries:
      entry.log()

  def groups(self): # not used?
    groups_list = []
    for entry in self.entries:
      if entry.tag_name[0] == '_':
        groups_list.append(entry.tag_name)
    return groups_list
