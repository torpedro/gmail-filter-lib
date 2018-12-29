
class t(object):
  def __init__(self, text):
    super(t, self).__init__()
    self.text = text

def simple_kv(key, value):
  if ' ' in value:
    quote = '"'
  else:
    quote = ''
  return t('%s:%s%s%s'  % (key, quote, value, quote))

def ffrom(value):
  return simple_kv('from', value)

def tto(value):
  return simple_kv('to', value)

def ssubject(value):
  return simple_kv('subject', value)

def aand(rules):
  return t("(" + " ".join([rule.text for rule in rules]) + ")")

def oor(rules):
  return t("{" + " ".join([rule.text for rule in rules]) + "}")
