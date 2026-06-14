#!/usr/bin/env python3
import sys
sys.path.append('../lib')
sys.path.append('./lib')

import expr
import gmail

filters = gmail.create()

travel = expr.oor([ expr.ffrom("booking.com"), expr.ffrom("trivago.com") ])

shopping = expr.oor([ expr.ffrom("amazon.com"), expr.ffrom("ebay.com") ])

receipt = expr.aand([ expr.tto("me"), expr.ffrom("paypal.com"), expr.ssubject("receipt") ])

filters.add_label("Travel", travel)
filters.add_label("Shopping", shopping)
filters.add_label("Receipt", receipt)
filters.print_xml()
