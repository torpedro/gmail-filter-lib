#!/usr/bin/python2.7
import sys
sys.path.append('../lib')
sys.path.append('./lib')

import Gmail

gmail = Gmail.create()
travel = Gmail.Expr.ffrom("booking.com")

gmail.add_label("Travel", travel)
gmail.print_xml()
