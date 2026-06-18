# Gmail Filter Editor

A local web UI for viewing and editing Gmail filters and labels.

The app runs a FastAPI server on your machine, serves the editor in your
browser, and makes Gmail API calls using your OAuth access token. It is built
for inspecting existing filters, editing them safely, and working with a more
readable YAML criteria format instead of raw Gmail filter JSON.

## Setup

Create the Python environment with `uv`:

```sh
uv venv
uv sync
```

Launch the editor:

```sh
uv run gmail-filter editor
```

By default the editor listens on `http://127.0.0.1:8080/`.

Optional flags:

```sh
uv run gmail-filter editor --host 127.0.0.1 --port 8090 --user me
```

## Authentication

The editor needs a Gmail OAuth access token. It reads the token from, in order:

1. `--token`
2. `GMAIL_FILTER_TOKEN`
3. `GOOGLE_ACCESS_TOKEN`
4. a local `oauth_token` file

The token is shown in the editor header. If you update it in the UI, the new
token is written back to `oauth_token` so it survives editor restarts.

The quickest manual way to get a token is Google OAuth Playground:

1. Open <https://developers.google.com/oauthplayground/>.
2. Click the gear icon.
3. Optionally enable "Use your own OAuth credentials" if you created a Google
   Cloud OAuth client.
4. Enter these scopes:

```text
https://www.googleapis.com/auth/gmail.settings.basic
https://www.googleapis.com/auth/gmail.labels
```

5. Click "Authorize APIs".
6. Exchange the authorization code for tokens.
7. Copy the access token into the editor header or save it locally:

```sh
printf '%s\n' "ya29..." > oauth_token
```

Access tokens are short-lived, usually about an hour. For long-term use, create
a Google Cloud OAuth Desktop app client and use a refresh-token flow.

## Editing Filters

The Filters view loads your Gmail filters and shows their criteria, applied
labels, and other actions. Filters are sorted by ID descending by default,
because Gmail does not expose filter creation timestamps.

The editor supports two filter edit modes:

- **Basic**: edit criteria as YAML, choose labels from a dropdown, and toggle
  skip-inbox independently.
- **JSON**: edit the raw Gmail API filter object directly.

Basic criteria use nested `and` / `or` blocks:

```yaml
and:
- from: paypal.com
- or:
  - subject: Receipt
  - subject: Invoice
```

The editor validates the criteria, shows the rendered Gmail query, reconstructs
the Gmail API JSON, and disables Save when there are no changes or the filter is
invalid.

Gmail does not expose a filter update method. When you save changes to an
existing filter, the editor creates the revised filter first and then deletes
the old filter. Delete and replace operations require confirmation. The editor
also keeps a small local undo stack for recreating deleted or replaced filters.

## Editing Labels

The Labels view lists Gmail labels and lets you create, patch, or delete
user-created labels. Gmail system labels are shown for reference but should be
treated as read-only.

The filter label dropdown only shows user labels, not Gmail system labels such
as inbox, categories, starred, or sent. Label IDs are available on hover where
the UI hides them from the main display.

## Tests

Run the test suite with:

```sh
uv run pytest
```

Some tests are expect-style and keep their expected output inline in
`tests/test_filter_outputs.py`. When an output change is intentional, update the
inline expectations with:

```sh
uv run pytest --accept
```
