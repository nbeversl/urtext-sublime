import re
from .context import CONTEXT
if CONTEXT == 'Sublime Text':
    import Urtext.urtext.syntax as syntax
else:
    import urtext.syntax as syntax

def strip_backtick_escape(contents):
    for e in syntax.preformat_c.findall(contents):
        contents = contents.replace(e,' '*len(e))
    return contents

def force_list(thing):
	if not isinstance(thing, list):
		thing = [thing]
	return thing

def get_id_from_link(target):
    match = syntax.any_link_or_pointer_c.search(target)
    if match: return match.group(6).strip()
    return target
