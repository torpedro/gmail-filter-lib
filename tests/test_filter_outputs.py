import cli
import filter_config
from fastapi.testclient import TestClient

from expect import assert_matches_expected


class FakeApiResponse(object):
  def __init__(self, body):
    self.body = body

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    return False

  def read(self):
    return self.body.encode("utf-8")


class FakeUrlopen(object):
  def __init__(self, body):
    self.body = body
    self.requests = []

  def __call__(self, request):
    self.requests.append(request)
    return FakeApiResponse(self.body)


def test_yaml_config_output(request):
  config = {
    "version": 1,
    "filters": [
      {
        "label": "Travel",
        "match": {
          "or": [
            {"from": "booking.com"},
            {"from": "trivago.com"},
          ],
        },
      },
      {
        "label": "Receipt",
        "match": {
          "and": [
            {"to": "me"},
            {"from": "paypal.com"},
            {"subject": "Receipt for your payment"},
          ],
        },
      },
      {
        "actions": {
          "label": "Ops",
          "archive": True,
          "mark_read": True,
        },
        "match": {
          "raw": 'list:alerts.example.com older_than:7d -subject:"keep"',
        },
      },
    ],
  }

  assert_matches_expected(
    request,
    "yaml-config",
    """
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
    """,
    filter_config.config_to_yaml_text(config),
  )


def test_yaml_to_xml_output(request):
  yaml_text = """
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
  """

  assert_matches_expected(
    request,
    "yaml-to-xml",
    """
    <?xml version="1.0" ?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:apps="http://schemas.google.com/apps/2006">
      <entry>
        <category term="filter"/>
        <apps:property name="hasTheWord" value="{from:booking.com from:trivago.com}"/>
        <apps:property name="label" value="Travel"/>
      </entry>
      <entry>
        <category term="filter"/>
        <apps:property name="hasTheWord" value="(to:me from:paypal.com subject:&quot;Receipt for your payment&quot;)"/>
        <apps:property name="label" value="Receipt"/>
      </entry>
      <entry>
        <category term="filter"/>
        <apps:property name="hasTheWord" value="list:alerts.example.com older_than:7d -subject:&quot;keep&quot;"/>
        <apps:property name="label" value="Ops"/>
        <apps:property name="shouldArchive" value="true"/>
        <apps:property name="shouldMarkAsRead" value="true"/>
      </entry>
    </feed>
    """,
    filter_config.yaml_to_xml_text(yaml_text),
  )


def test_legacy_boolean_yaml_keys_still_convert(request):
  yaml_text = """
  version: 1
  filters:
    - label: Legacy
      match:
        any:
          - from: booking.com
          - all:
            - to: me
            - subject: Receipt
    - label: Uppercase
      match:
        OR:
          - from: alerts.example.com
          - AND:
            - to: me
            - subject: Alert
  """

  assert_matches_expected(
    request,
    "legacy-boolean-yaml-keys",
    """
    <?xml version="1.0" ?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:apps="http://schemas.google.com/apps/2006">
      <entry>
        <category term="filter"/>
        <apps:property name="hasTheWord" value="{from:booking.com (to:me subject:Receipt)}"/>
        <apps:property name="label" value="Legacy"/>
      </entry>
      <entry>
        <category term="filter"/>
        <apps:property name="hasTheWord" value="{from:alerts.example.com (to:me subject:Alert)}"/>
        <apps:property name="label" value="Uppercase"/>
      </entry>
    </feed>
    """,
    filter_config.yaml_to_xml_text(yaml_text),
  )


def test_xml_to_yaml_output(request):
  xml_text = """
  <?xml version="1.0" ?>
  <feed xmlns="http://www.w3.org/2005/Atom" xmlns:apps="http://schemas.google.com/apps/2006">
    <entry>
      <category term="filter"/>
      <apps:property name="label" value="Travel"/>
      <apps:property name="hasTheWord" value="{from:booking.com from:trivago.com}"/>
    </entry>
    <entry>
      <category term="filter"/>
      <apps:property name="hasTheWord" value="list:alerts.example.com older_than:7d -subject:&quot;keep&quot;"/>
      <apps:property name="label" value="Ops"/>
      <apps:property name="shouldArchive" value="true"/>
      <apps:property name="shouldMarkAsRead" value="true"/>
    </entry>
  </feed>
  """

  assert_matches_expected(
    request,
    "xml-to-yaml",
    """
    version: 1
    filters:
    - label: Travel
      match:
        or:
        - from: booking.com
        - from: trivago.com
    - label: Ops
      match:
        raw: list:alerts.example.com older_than:7d -subject:"keep"
      actions:
        archive: true
        mark_read: true
    """,
    filter_config.xml_to_yaml_text(xml_text),
  )


def test_xml_to_yaml_parses_nested_brace_groups(request):
  xml_text = """
  <?xml version="1.0" ?>
  <feed xmlns="http://www.w3.org/2005/Atom" xmlns:apps="http://schemas.google.com/apps/2006">
    <entry>
      <category term="filter"/>
      <apps:property name="hasTheWord" value="{{from:splitwise.com from:billsup.com} subject:&quot;Receipt for your Payment&quot; subject:&quot;You have authorized a payment&quot;}"/>
      <apps:property name="label" value="Payments"/>
    </entry>
  </feed>
  """

  assert_matches_expected(
    request,
    "xml-to-yaml-nested-braces",
    """
    version: 1
    filters:
    - label: Payments
      match:
        or:
        - from: splitwise.com
        - from: billsup.com
        - subject: Receipt for your Payment
        - subject: You have authorized a payment
    """,
    filter_config.xml_to_yaml_text(xml_text),
  )


def test_api_list_json_to_yaml_output(request):
  json_text = """
  {
    "filter": [
      {
        "id": "filter-query",
        "criteria": {
          "query": "{{from:splitwise.com from:billsup.com} subject:\\"Receipt for your Payment\\"}"
        },
        "action": {
          "addLabelIds": ["Label_37"]
        }
      },
      {
        "id": "filter-from",
        "criteria": {
          "from": "dexters.co.uk"
        },
        "action": {
          "addLabelIds": ["Label_8104476255522847601"],
          "removeLabelIds": ["INBOX"],
          "forward": "person@example.com"
        }
      }
    ]
  }
  """

  assert_matches_expected(
    request,
    "api-list-json-to-yaml",
    """
    version: 1
    filters:
    - id: filter-query
      match:
        or:
        - from: splitwise.com
        - from: billsup.com
        - subject: Receipt for your Payment
      actions:
        add_label_ids:
        - Label_37
    - id: filter-from
      match:
        from: dexters.co.uk
      actions:
        add_label_ids:
        - Label_8104476255522847601
        remove_label_ids:
        - INBOX
        forward_to: person@example.com
    """,
    filter_config.api_json_to_yaml_text(json_text),
  )


def test_api_list_json_file_converts_to_yaml_by_extension(request, tmp_path, capsys):
  json_path = tmp_path / "filters.json"
  json_path.write_text(
    """{
  "filter": [
    {
      "id": "filter-query",
      "criteria": {
        "query": "{from:booking.com from:trivago.com}"
      },
      "action": {
        "addLabelIds": ["Label_123"]
      }
    }
  ]
}
"""
  )

  cli.main(["convert", str(json_path)])

  assert_matches_expected(
    request,
    "api-list-json-file-to-yaml",
    """
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
    """,
    capsys.readouterr().out,
  )


def test_cli_infers_formats_from_file_extensions(request, tmp_path):
  yaml_path = tmp_path / "filters.yaml"
  xml_path = tmp_path / "filters.xml"
  roundtrip_yaml_path = tmp_path / "roundtrip.yml"

  yaml_path.write_text(
    """version: 1
filters:
- label: Travel
  match:
    from: booking.com
"""
  )

  cli.main(["convert", str(yaml_path), str(xml_path)])
  cli.main(["convert", str(xml_path), str(roundtrip_yaml_path)])

  assert_matches_expected(
    request,
    "cli-inferred-yaml-to-xml",
    """
    <?xml version="1.0" ?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:apps="http://schemas.google.com/apps/2006">
      <entry>
        <category term="filter"/>
        <apps:property name="hasTheWord" value="from:booking.com"/>
        <apps:property name="label" value="Travel"/>
      </entry>
    </feed>
    """,
    xml_path.read_text(),
  )

  assert_matches_expected(
    request,
    "cli-inferred-xml-to-yaml",
    """
    version: 1
    filters:
    - label: Travel
      match:
        from: booking.com
    """,
    roundtrip_yaml_path.read_text(),
  )


def test_cli_prints_to_stdout_when_output_is_omitted(request, tmp_path, capsys):
  yaml_path = tmp_path / "filters.yaml"

  yaml_path.write_text(
    """version: 1
filters:
- label: Travel
  match:
    from: booking.com
"""
  )

  cli.main(["convert", str(yaml_path)])

  assert_matches_expected(
    request,
    "cli-stdout-yaml-to-xml",
    """
    <?xml version="1.0" ?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:apps="http://schemas.google.com/apps/2006">
      <entry>
        <category term="filter"/>
        <apps:property name="hasTheWord" value="from:booking.com"/>
        <apps:property name="label" value="Travel"/>
      </entry>
    </feed>
    """,
    capsys.readouterr().out,
  )


def test_api_list_prints_response_to_stdout(request, monkeypatch, capsys):
  fake_urlopen = FakeUrlopen('{"filter":[{"id":"filter-1"}]}')
  monkeypatch.setattr(filter_config.urllib.request, "urlopen", fake_urlopen)

  cli.main(["api", "filters", "list", "--token", "access-token"])

  api_request = fake_urlopen.requests[0]
  assert api_request.get_method() == "GET"
  assert api_request.full_url == "https://gmail.googleapis.com/gmail/v1/users/me/settings/filters"
  assert api_request.headers["Authorization"] == "Bearer access-token"

  assert_matches_expected(
    request,
    "api-list-stdout",
    """
    {"filter":[{"id":"filter-1"}]}
    """,
    capsys.readouterr().out,
  )


def test_api_list_reads_token_from_local_oauth_token_file(tmp_path, monkeypatch, capsys):
  fake_urlopen = FakeUrlopen('{"filter":[]}')
  monkeypatch.setattr(filter_config.urllib.request, "urlopen", fake_urlopen)
  monkeypatch.delenv("GMAIL_FILTER_TOKEN", raising=False)
  monkeypatch.delenv("GOOGLE_ACCESS_TOKEN", raising=False)
  monkeypatch.chdir(tmp_path)
  (tmp_path / "oauth_token").write_text("file-token\n")

  cli.main(["api", "filters", "list"])

  api_request = fake_urlopen.requests[0]
  assert api_request.headers["Authorization"] == "Bearer file-token"
  assert capsys.readouterr().out == '{"filter":[]}\n'


def test_api_token_argument_takes_precedence_over_local_oauth_token_file(tmp_path, monkeypatch):
  fake_urlopen = FakeUrlopen('{"filter":[]}')
  monkeypatch.setattr(filter_config.urllib.request, "urlopen", fake_urlopen)
  monkeypatch.chdir(tmp_path)
  (tmp_path / "oauth_token").write_text("file-token\n")

  cli.main(["api", "filters", "list", "--token", "argument-token"])

  api_request = fake_urlopen.requests[0]
  assert api_request.headers["Authorization"] == "Bearer argument-token"


def test_api_get_prints_response_to_stdout(request, monkeypatch, capsys):
  fake_urlopen = FakeUrlopen('{"id":"filter-1","criteria":{"from":"booking.com"}}')
  monkeypatch.setattr(filter_config.urllib.request, "urlopen", fake_urlopen)

  cli.main(["api", "filters", "get", "filter-1", "--token", "access-token"])

  api_request = fake_urlopen.requests[0]
  assert api_request.get_method() == "GET"
  assert api_request.full_url == "https://gmail.googleapis.com/gmail/v1/users/me/settings/filters/filter-1"

  assert_matches_expected(
    request,
    "api-get-stdout",
    """
    {"id":"filter-1","criteria":{"from":"booking.com"}}
    """,
    capsys.readouterr().out,
  )


def test_api_delete_prints_response_to_stdout(request, monkeypatch, capsys):
  fake_urlopen = FakeUrlopen("{}")
  monkeypatch.setattr(filter_config.urllib.request, "urlopen", fake_urlopen)

  cli.main(["api", "filters", "delete", "filter-1", "--token", "access-token"])

  api_request = fake_urlopen.requests[0]
  assert api_request.get_method() == "DELETE"
  assert api_request.full_url == "https://gmail.googleapis.com/gmail/v1/users/me/settings/filters/filter-1"

  assert_matches_expected(
    request,
    "api-delete-stdout",
    """
    {}
    """,
    capsys.readouterr().out,
  )


def test_api_create_posts_json_and_prints_response(request, tmp_path, monkeypatch, capsys):
  json_path = tmp_path / "filter.json"
  json_path.write_text(
    """{
  "criteria": {
    "query": "from:booking.com"
  },
  "action": {
    "addLabelIds": ["Label_123"]
  }
}
"""
  )

  fake_urlopen = FakeUrlopen('{"id":"filter-1"}')
  monkeypatch.setattr(filter_config.urllib.request, "urlopen", fake_urlopen)

  cli.main(["api", "filters", "create", str(json_path), "--user", "person@example.com", "--token", "access-token"])

  api_request = fake_urlopen.requests[0]
  assert api_request.get_method() == "POST"
  assert api_request.full_url == "https://gmail.googleapis.com/gmail/v1/users/person%40example.com/settings/filters"
  assert api_request.headers["Authorization"] == "Bearer access-token"
  assert api_request.headers["Content-type"] == "application/json"

  assert_matches_expected(
    request,
    "api-create-request-body",
    """
    {"criteria": {"query": "from:booking.com"}, "action": {"addLabelIds": ["Label_123"]}}
    """,
    api_request.data.decode("utf-8"),
  )

  assert_matches_expected(
    request,
    "api-create-stdout",
    """
    {"id":"filter-1"}
    """,
    capsys.readouterr().out,
  )


def test_api_labels_list_prints_response_to_stdout(request, monkeypatch, capsys):
  fake_urlopen = FakeUrlopen('{"labels":[{"id":"Label_123","name":"Travel"}]}')
  monkeypatch.setattr(filter_config.urllib.request, "urlopen", fake_urlopen)

  cli.main(["api", "labels", "list", "--token", "access-token"])

  api_request = fake_urlopen.requests[0]
  assert api_request.get_method() == "GET"
  assert api_request.full_url == "https://gmail.googleapis.com/gmail/v1/users/me/labels"
  assert api_request.headers["Authorization"] == "Bearer access-token"

  assert_matches_expected(
    request,
    "api-labels-list-stdout",
    """
    {"labels":[{"id":"Label_123","name":"Travel"}]}
    """,
    capsys.readouterr().out,
  )


def test_api_labels_patch_posts_json_and_prints_response(request, tmp_path, monkeypatch, capsys):
  json_path = tmp_path / "label.json"
  json_path.write_text(
    """{
  "name": "Trips",
  "labelListVisibility": "labelShow"
}
"""
  )

  fake_urlopen = FakeUrlopen('{"id":"Label_123","name":"Trips"}')
  monkeypatch.setattr(filter_config.urllib.request, "urlopen", fake_urlopen)

  cli.main(["api", "labels", "patch", "Label_123", str(json_path), "--token", "access-token"])

  api_request = fake_urlopen.requests[0]
  assert api_request.get_method() == "PATCH"
  assert api_request.full_url == "https://gmail.googleapis.com/gmail/v1/users/me/labels/Label_123"
  assert api_request.headers["Content-type"] == "application/json"

  assert_matches_expected(
    request,
    "api-labels-patch-request-body",
    """
    {"name": "Trips", "labelListVisibility": "labelShow"}
    """,
    api_request.data.decode("utf-8"),
  )

  assert_matches_expected(
    request,
    "api-labels-patch-stdout",
    """
    {"id":"Label_123","name":"Trips"}
    """,
    capsys.readouterr().out,
  )


def test_editor_serves_static_page(request):
  app = filter_config.create_editor_app("me", "access-token")
  client = TestClient(app)

  response = client.get("/")

  assert response.status_code == 200
  assert_matches_expected(
    request,
    "editor-index-html-markers",
    """
    True
    True
    True
    True
    True
    True
    True
    True
    True
    """,
    "\n".join([
      str("Gmail filters" in response.text),
      str('/static/style.css' in response.text),
      str('/static/app.js' in response.text),
      str('id="auth-token" type="text"' in response.text),
      str('id="labels-tab"' in response.text),
      str('id="filter-json"' in response.text),
      str('id="basic-filter-editor"' in response.text),
      str('placeholder="and:' in response.text),
      str('id="busy-overlay"' in response.text),
    ]),
  )


def test_editor_static_javascript_is_loaded(request):
  app = filter_config.create_editor_app("me", "access-token")
  client = TestClient(app)

  response = client.get("/static/app.js")

  assert response.status_code == 200
  assert_matches_expected(
    request,
    "editor-static-js-markers",
    """
    True
    True
    True
    True
    True
    True
    True
    True
    True
    True
    True
    True
    """,
    "\n".join([
      str('fetch("/api/auth/token"' in response.text),
      str('fetch("/api/auth/token", {' in response.text),
      str('fetch("/api/filters"' in response.text),
      str('fetch("/api/labels"' in response.text),
      str('fetch("/api/match/parse"' in response.text),
      str('fetch("/api/match/render"' in response.text),
      str('fetch(selected && selected.id ? `/api/filters/${encodeURIComponent(selected.id)}` : "/api/filters"' in response.text),
      str("function structuredFilterPayload()" in response.text),
      str("function sortedFilters()" in response.text),
      str('String(right.filter.id || "").localeCompare(String(left.filter.id || ""))' in response.text),
      str("async function withBusy" in response.text),
      str("function render()" in response.text),
    ]),
  )


def test_editor_api_filters_uses_gmail_list(request, monkeypatch):
  fake_urlopen = FakeUrlopen('{"filter":[{"id":"filter-1"}]}')
  monkeypatch.setattr(filter_config.urllib.request, "urlopen", fake_urlopen)
  app = filter_config.create_editor_app("me", "access-token")
  client = TestClient(app)

  response = client.get("/api/filters")

  assert response.status_code == 200
  assert response.json() == {"filter": [{"id": "filter-1"}]}
  api_request = fake_urlopen.requests[0]
  assert api_request.get_method() == "GET"
  assert api_request.full_url == "https://gmail.googleapis.com/gmail/v1/users/me/settings/filters"
  assert api_request.headers["Authorization"] == "Bearer access-token"


def test_editor_api_token_can_be_updated_for_later_calls(monkeypatch):
  fake_urlopen = FakeUrlopen('{"filter":[]}')
  monkeypatch.setattr(filter_config.urllib.request, "urlopen", fake_urlopen)
  app = filter_config.create_editor_app("me", "old-token")
  client = TestClient(app)

  token_response = client.get("/api/auth/token")
  update_response = client.put("/api/auth/token", json={"token": "new-token"})
  filters_response = client.get("/api/filters")

  assert token_response.status_code == 200
  assert token_response.json() == {"token": "old-token"}
  assert update_response.status_code == 200
  assert filters_response.status_code == 200
  api_request = fake_urlopen.requests[0]
  assert api_request.headers["Authorization"] == "Bearer new-token"


def test_editor_api_match_parse_returns_yaml(request):
  app = filter_config.create_editor_app("me", "access-token")
  client = TestClient(app)

  response = client.post("/api/match/parse", json={"query": "{from:booking.com from:trivago.com}"})

  assert response.status_code == 200
  assert_matches_expected(
    request,
    "editor-match-parse-yaml",
    """
    or:
    - from: booking.com
    - from: trivago.com
    """,
    response.json()["yaml"],
  )


def test_editor_api_match_parse_accepts_criteria_object(request):
  app = filter_config.create_editor_app("me", "access-token")
  client = TestClient(app)

  response = client.post("/api/match/parse", json={"criteria": {"from": "dexters.co.uk"}})

  assert response.status_code == 200
  assert_matches_expected(
    request,
    "editor-match-parse-criteria-yaml",
    """
    from: dexters.co.uk
    """,
    response.json()["yaml"],
  )


def test_editor_api_match_render_returns_query(request):
  app = filter_config.create_editor_app("me", "access-token")
  client = TestClient(app)

  response = client.post(
    "/api/match/render",
    json={
      "yaml": """and:
- from: paypal.com
- subject: Receipt
"""
    },
  )

  assert response.status_code == 200
  assert_matches_expected(
    request,
    "editor-match-render-query",
    """
    (from:paypal.com subject:Receipt)
    """,
    response.json()["query"],
  )


def test_editor_api_match_render_returns_direct_criteria():
  app = filter_config.create_editor_app("me", "access-token")
  client = TestClient(app)

  response = client.post("/api/match/render", json={"yaml": "from: dexters.co.uk\n"})

  assert response.status_code == 200
  assert response.json() == {
    "query": "",
    "criteria": {
      "from": "dexters.co.uk",
    },
  }


def test_editor_api_filter_create_posts_filter_json(request, monkeypatch):
  fake_urlopen = FakeUrlopen('{"id":"new-filter"}')
  monkeypatch.setattr(filter_config.urllib.request, "urlopen", fake_urlopen)
  app = filter_config.create_editor_app("me", "access-token")
  client = TestClient(app)

  response = client.post(
    "/api/filters",
    json={
      "id": "ignored-client-id",
      "criteria": {"query": "from:booking.com"},
      "action": {"addLabelIds": ["Label_123"]},
    },
  )

  assert response.status_code == 200
  assert response.json() == {"id": "new-filter"}
  api_request = fake_urlopen.requests[0]
  assert api_request.get_method() == "POST"
  assert api_request.full_url == "https://gmail.googleapis.com/gmail/v1/users/me/settings/filters"

  assert_matches_expected(
    request,
    "editor-filter-create-body",
    """
    {"criteria": {"query": "from:booking.com"}, "action": {"addLabelIds": ["Label_123"]}}
    """,
    api_request.data.decode("utf-8"),
  )


def test_editor_api_filter_replace_creates_then_deletes_old_filter(request, monkeypatch):
  fake_urlopen = FakeUrlopen('{"id":"new-filter"}')
  monkeypatch.setattr(filter_config.urllib.request, "urlopen", fake_urlopen)
  app = filter_config.create_editor_app("me", "access-token")
  client = TestClient(app)

  response = client.put(
    "/api/filters/old-filter",
    json={
      "id": "old-filter",
      "criteria": {"query": "from:trivago.com"},
      "action": {"removeLabelIds": ["INBOX"]},
    },
  )

  assert response.status_code == 200
  assert response.json() == {"id": "new-filter"}
  create_request = fake_urlopen.requests[0]
  delete_request = fake_urlopen.requests[1]
  assert create_request.get_method() == "POST"
  assert create_request.full_url == "https://gmail.googleapis.com/gmail/v1/users/me/settings/filters"
  assert delete_request.get_method() == "DELETE"
  assert delete_request.full_url == "https://gmail.googleapis.com/gmail/v1/users/me/settings/filters/old-filter"

  assert_matches_expected(
    request,
    "editor-filter-replace-body",
    """
    {"criteria": {"query": "from:trivago.com"}, "action": {"removeLabelIds": ["INBOX"]}}
    """,
    create_request.data.decode("utf-8"),
  )


def test_editor_api_labels_uses_gmail_labels_list(monkeypatch):
  fake_urlopen = FakeUrlopen('{"labels":[{"id":"Label_123","name":"Travel"}]}')
  monkeypatch.setattr(filter_config.urllib.request, "urlopen", fake_urlopen)
  app = filter_config.create_editor_app("me", "access-token")
  client = TestClient(app)

  response = client.get("/api/labels")

  assert response.status_code == 200
  assert response.json() == {"labels": [{"id": "Label_123", "name": "Travel"}]}
  api_request = fake_urlopen.requests[0]
  assert api_request.get_method() == "GET"
  assert api_request.full_url == "https://gmail.googleapis.com/gmail/v1/users/me/labels"
  assert api_request.headers["Authorization"] == "Bearer access-token"
