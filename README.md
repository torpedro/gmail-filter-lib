# Gmail Filter Generator Library [![Build Status](https://travis-ci.org/torpedro/gmail-filter-lib.svg?branch=master)](https://travis-ci.org/torpedro/gmail-filter-lib)

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

## YAML format

Gmail imports and exports filters as XML, but this project also supports a
more readable YAML format:

```yaml
version: 1
filters:
- label: Travel
  match:
    or:
    - from: booking.com
    - from: trivago.com
- label: Receipt
  match:
    and:
    - to: me
    - from: paypal.com
    - subject: Receipt for your payment
- match:
    raw: list:alerts.example.com older_than:7d -subject:"keep"
  actions:
    label: Ops
    archive: true
    mark_read: true
```

`match` supports nested boolean blocks:

- `and`: Gmail `(...)` grouping
- `or`: Gmail `{...}` OR grouping
- `not`: Gmail `-...` negation
- field terms such as `from`, `to`, `cc`, `bcc`, `subject`, `label`,
  `category`, `has`, `list`, `filename`, `in`, `is`, `delivered_to`, `size`,
  `larger`, `smaller`, and date operators
- `raw`: an escape hatch for Gmail search syntax that should be preserved as-is

Supported actions include `label`, `archive`, `mark_read`, `star`, `trash`,
`never_spam`, `mark_important`, `never_important`, `category`, and
`forward_to`.

Unknown or less common Gmail XML properties can be preserved under
`properties`.

Convert between formats with:

```sh
uv run gmail-filter convert filters.xml filters.yaml
uv run gmail-filter convert filters.json filters.yaml
uv run gmail-filter convert filters.yaml filters.xml
```

If the output path is omitted, the converted result is printed to stdout:

```sh
uv run gmail-filter convert filters.yaml
uv run gmail-filter convert filters.xml
uv run gmail-filter convert filters.json
```

`filters.json` is the raw response from `api filters list`. It is converted into the
same YAML DSL, preserving Gmail API filter IDs and label IDs:

```yaml
version: 1
filters:
- id: filter-query
  match:
    or:
    - from: booking.com
    - from: trivago.com
  actions:
    add_label_ids:
    - Label_123
```

## Gmail API

The CLI can call Gmail's filter API and prints the raw JSON response to stdout.
Pass an OAuth access token with `--token`, or set `GMAIL_FILTER_TOKEN` or
`GOOGLE_ACCESS_TOKEN`. If neither is set, the CLI tries to read a local
`oauth_token` file.

```sh
uv run gmail-filter api filters list --token "$TOKEN"
uv run gmail-filter api filters get FILTER_ID --token "$TOKEN"
uv run gmail-filter api filters delete FILTER_ID --token "$TOKEN"
uv run gmail-filter api filters create filter.json --token "$TOKEN"
uv run gmail-filter api labels list --token "$TOKEN"
uv run gmail-filter api labels get LABEL_ID --token "$TOKEN"
uv run gmail-filter api labels create label.json --token "$TOKEN"
uv run gmail-filter api labels patch LABEL_ID label.json --token "$TOKEN"
uv run gmail-filter api labels update LABEL_ID label.json --token "$TOKEN"
uv run gmail-filter api labels delete LABEL_ID --token "$TOKEN"
```

Use `--user` to target a specific Gmail user; it defaults to `me`.

Launch the local editor with:

```sh
uv run gmail-filter editor
```

The editor serves a local web page and loads filters and labels through the
same server-side API calls, using the configured OAuth token. The token is
shown in the editor header and can be updated for the current server session
without restarting. It resolves label
IDs in filter actions to label names. Filters can be created, deleted, and
edited in Basic mode or JSON mode. Basic mode edits the criteria as the YAML
match DSL with nested `and`/`or` blocks, plus one applied label and skip-inbox
independently, then reconstructs the Gmail API JSON. JSON mode edits the raw
Gmail API filter object directly. Gmail does
not expose a filter update method, so saving an existing filter creates the
revised filter first and then deletes the old filter. User-created labels can
be created, patched, and deleted. Gmail system labels are shown but should be
treated as read-only. Gmail filter JSON does not include creation timestamps;
the editor records local timestamps for filters created through the editor and
shows those first. Other filters are sorted by filter ID descending as a
convenience fallback, but Gmail does not document filter IDs as creation
timestamps.

### Getting an access token

The quickest manual way to get an access token is OAuth Playground:

1. Open <https://developers.google.com/oauthplayground/>.
2. Click the gear icon.
3. Optionally enable "Use your own OAuth credentials" if you created a Google
   Cloud OAuth client.
4. Enter these scopes:

```text
https://www.googleapis.com/auth/gmail.settings.basic
https://www.googleapis.com/auth/gmail.labels
```

`gmail.settings.basic` is required to create filters. `gmail.labels` is enough
to list, create, patch, update, and delete labels. If you only need to read
labels outside the editor, Gmail also accepts broader or read-only scopes such
as `gmail.readonly`, `gmail.metadata`, `gmail.modify`, or `https://mail.google.com/`.

5. Click "Authorize APIs".
6. Exchange the authorization code for tokens.
7. Copy the access token.
8. Export it for the CLI:

```sh
export GMAIL_FILTER_TOKEN="ya29..."
uv run gmail-filter api filters list
```

Alternatively, save it in a local `oauth_token` file:

```sh
printf '%s\n' "ya29..." > oauth_token
uv run gmail-filter api filters list
```

Access tokens are short-lived, usually about an hour. For long-term use, create
a Google Cloud OAuth Desktop app client and use a refresh-token flow.

`api filters create` expects Gmail API filter JSON, not XML:

```json
{
  "criteria": {
    "query": "from:booking.com"
  },
  "action": {
    "addLabelIds": ["Label_123"]
  }
}
```

## Tests

This project uses expect-style tests for generated filter XML. Test scenarios
and their expected output are inlined in `tests/test_filter_outputs.py`.

Run the tests with:

```sh
uv run pytest
```

If the generated XML changes, the test failure prints a unified diff between
the checked-in expected output and the new output.

When a change is intentional, rewrite the inline expected output with:

```sh
uv run pytest --accept
```
