import xml.etree.ElementTree as ET
import Expr

xmlns = "http://www.w3.org/2005/Atom"
xmlns_apps = "http://schemas.google.com/apps/2006" 

class Gmail(object):
  def __init__(self):
    super(Gmail, self).__init__()

    feed_kwargs = {
      "xmlns": xmlns,
      "xmlns:apps": xmlns_apps
    }

    self.root = ET.Element("feed", **feed_kwargs)


  def print_xml(self):
    def prettify(elem):
      from xml.dom import minidom
      rough_string = ET.tostring(elem, 'utf-8')
      reparsed = minidom.parseString(rough_string)
      return reparsed.toprettyxml(indent="  ")

    tree = ET.ElementTree(self.root)
    print prettify(self.root)

  def add_label(self, label, rule):
    entry = ET.SubElement(self.root, "entry")
    ET.SubElement(entry, "category", term="filter")
    ET.SubElement(entry, "apps:property", **{ "name":"label", "value": label })
    ET.SubElement(entry, "apps:property", **{ "name":"hasTheWord", "value": rule.text })


def create():
  return Gmail()

