# Gmail Filter Generator Library

Small library to allow generating complex Gmail Filter rules from code.

See `examples/` to see how to use the library.

The scripts will generate an XML file that can be uploaded in the Gmail UI in the settings for filters.

## Example

```python
import Gmail, Expr

gmail = Gmail.create()

travel = Expr.oor([ Expr.ffrom("booking.com"), Expr.ffrom("trivago.com") ])

shopping = Expr.oor([ Expr.ffrom("amazon.com"), Expr.ffrom("ebay.com") ])

receipt = Expr.aand([ Expr.tto("me"), Expr.ffrom("paypal.com"), Expr.ssubject("receipt") ])

gmail.add_label("Travel", travel)
gmail.add_label("Shopping", shopping)
gmail.add_label("Receipt", receipt)
gmail.print_xml()
```

.. and the generated xml:

```xml
<?xml version="1.0" ?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:apps="http://schemas.google.com/apps/2006">
  <entry>
    <category term="filter"/>
    <apps:property name="label" value="Travel"/>
    <apps:property name="hasTheWord" value="{from:booking.com from:trivago.com}"/>
  </entry>
  <entry>
    <category term="filter"/>
    <apps:property name="label" value="Shopping"/>
    <apps:property name="hasTheWord" value="{from:amazon.com from:ebay.com}"/>
  </entry>
  <entry>
    <category term="filter"/>
    <apps:property name="label" value="Receipt"/>
    <apps:property name="hasTheWord" value="(to:me from:paypal.com subject:receipt)"/>
  </entry>
</feed>
```
