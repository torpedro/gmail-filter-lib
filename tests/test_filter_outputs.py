import Expr
import Gmail

from expect import assert_matches_expected


def test_simple_single_rule_output(request):
  gmail = Gmail.create()
  gmail.add_label("Travel", Expr.ffrom("booking.com"))

  assert_matches_expected(
    request,
    "simple-single-rule",
    """
    <?xml version="1.0" ?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:apps="http://schemas.google.com/apps/2006">
      <entry>
        <category term="filter"/>
        <apps:property name="label" value="Travel"/>
        <apps:property name="hasTheWord" value="from:booking.com"/>
      </entry>
    </feed>
    """,
    gmail.get_xml(),
  )


def test_complex_rules_output(request):
  gmail = Gmail.create()

  travel = Expr.oor([
    Expr.ffrom("booking.com"),
    Expr.ffrom("trivago.com"),
  ])
  shopping = Expr.oor([
    Expr.ffrom("amazon.com"),
    Expr.ffrom("ebay.com"),
  ])
  receipt = Expr.aand([
    Expr.tto("me"),
    Expr.ffrom("paypal.com"),
    Expr.ssubject("receipt"),
  ])

  gmail.add_label("Travel", travel)
  gmail.add_label("Shopping", shopping)
  gmail.add_label("Receipt", receipt)

  assert_matches_expected(
    request,
    "complex-rules",
    """
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
    """,
    gmail.get_xml(),
  )


def test_quoted_terms_output(request):
  gmail = Gmail.create()

  gmail.add_label(
    "Receipts",
    Expr.aand([
      Expr.ffrom("paypal.com"),
      Expr.ssubject("Receipt for your payment"),
    ]),
  )

  assert_matches_expected(
    request,
    "quoted-terms",
    """
    <?xml version="1.0" ?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:apps="http://schemas.google.com/apps/2006">
      <entry>
        <category term="filter"/>
        <apps:property name="label" value="Receipts"/>
        <apps:property name="hasTheWord" value="(from:paypal.com subject:&quot;Receipt for your payment&quot;)"/>
      </entry>
    </feed>
    """,
    gmail.get_xml(),
  )
