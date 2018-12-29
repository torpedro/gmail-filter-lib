#!/usr/bin/python2.7
import sys
sys.path.append('../lib')
sys.path.append('./lib')

import Gmail, Expr

gmail = Gmail.create()

travel = Expr.oor([ Expr.ffrom("booking.com"), Expr.ffrom("trivago.com") ])

shopping = Expr.oor([ Expr.ffrom("amazon.com"), Expr.ffrom("ebay.com") ])

receipt = Expr.aand([ Expr.tto("me"), Expr.ffrom("paypal.com"), Expr.ssubject("receipt") ])

gmail.add_label("Travel", travel)
gmail.add_label("Shopping", shopping)
gmail.add_label("Receipt", receipt)
gmail.print_xml()
