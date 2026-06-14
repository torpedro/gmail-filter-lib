#!/usr/bin/env python3
import sys
sys.path.append('../lib')
sys.path.append('./lib')

import gmail

filters = gmail.create()
travel = gmail.expr.ffrom("booking.com")

filters.add_label("Travel", travel)
filters.print_xml()
