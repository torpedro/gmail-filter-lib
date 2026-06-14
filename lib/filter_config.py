import json
import re
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from xml.dom import minidom

from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import yaml


ATOM_XMLNS = "http://www.w3.org/2005/Atom"
APPS_XMLNS = "http://schemas.google.com/apps/2006"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
EDITOR_DIR = Path(__file__).resolve().parents[1] / "editor"

ACTION_TO_PROPERTY = {
  "label": "label",
  "archive": "shouldArchive",
  "mark_read": "shouldMarkAsRead",
  "star": "shouldStar",
  "trash": "shouldTrash",
  "never_spam": "shouldNeverSpam",
  "mark_important": "shouldAlwaysMarkAsImportant",
  "never_important": "shouldNeverMarkAsImportant",
  "category": "smartLabelToApply",
  "forward_to": "forwardTo",
}
PROPERTY_TO_ACTION = dict((value, key) for key, value in ACTION_TO_PROPERTY.items())

CRITERIA_TO_PROPERTY = {
  "from": "from",
  "to": "to",
  "subject": "subject",
  "query": "hasTheWord",
  "not_query": "doesNotHaveTheWord",
  "has_attachment": "hasAttachment",
  "exclude_chats": "excludeChats",
  "size": "size",
  "size_operator": "sizeOperator",
  "size_unit": "sizeUnit",
}
PROPERTY_TO_CRITERIA = dict((value, key) for key, value in CRITERIA_TO_PROPERTY.items())

SEARCH_ALIASES = {
  "delivered_to": "deliveredto",
}
SEARCH_KEYS = set([
  "from",
  "to",
  "cc",
  "bcc",
  "subject",
  "after",
  "before",
  "older",
  "newer",
  "older_than",
  "newer_than",
  "label",
  "category",
  "has",
  "list",
  "filename",
  "in",
  "is",
  "deliveredto",
  "delivered_to",
  "size",
  "larger",
  "smaller",
  "rfc822msgid",
  "text",
])


def yaml_to_xml_text(yaml_text):
  return config_to_xml(yaml.safe_load(yaml_text))


def xml_to_yaml_text(xml_text):
  return config_to_yaml_text(xml_to_config(xml_text))


def api_json_to_yaml_text(json_text):
  return config_to_yaml_text(api_json_to_config(json.loads(json_text)))


def config_to_yaml_text(config):
  return yaml.safe_dump(_normalize_config(config), sort_keys=False)


def xml_to_config(xml_text):
  root = ET.fromstring(xml_text.strip())
  filters = []

  for entry in _children_named(root, "entry"):
    filter_config = {}
    actions = {}
    criteria = {}
    extra_properties = {}

    for prop in _children_named(entry, "property"):
      name = prop.attrib.get("name")
      value = prop.attrib.get("value", "")

      if name in PROPERTY_TO_ACTION:
        action_name = PROPERTY_TO_ACTION[name]
        _set_action(filter_config, actions, action_name, _decode_property_value(value))
      elif name == "hasTheWord":
        filter_config["match"] = parse_match(value)
      elif name in PROPERTY_TO_CRITERIA:
        criteria[PROPERTY_TO_CRITERIA[name]] = _decode_property_value(value)
      else:
        extra_properties[name] = _decode_property_value(value)

    if actions:
      filter_config["actions"] = actions
    if criteria:
      filter_config["criteria"] = criteria
    if extra_properties:
      filter_config["properties"] = extra_properties
    filters.append(filter_config)

  return {
    "version": 1,
    "filters": filters,
  }


def api_json_to_config(api_json):
  api_filters = api_json.get("filter", api_json if isinstance(api_json, list) else [])
  filters = []

  for api_filter in api_filters:
    filter_config = {}

    if "id" in api_filter:
      filter_config["id"] = api_filter["id"]

    criteria = api_filter.get("criteria", {})
    _add_api_criteria(filter_config, criteria)

    action = api_filter.get("action", {})
    _add_api_action(filter_config, action)

    filters.append(filter_config)

  return {
    "version": 1,
    "filters": filters,
  }


def _add_api_criteria(filter_config, criteria):
  if "query" in criteria:
    filter_config["match"] = parse_match(criteria["query"])

  criteria_config = {}
  for api_key, yaml_key in [
    ("from", "from"),
    ("to", "to"),
    ("subject", "subject"),
    ("negatedQuery", "not_query"),
    ("hasAttachment", "has_attachment"),
    ("excludeChats", "exclude_chats"),
    ("size", "size"),
    ("sizeComparison", "size_comparison"),
  ]:
    if api_key in criteria:
      criteria_config[yaml_key] = criteria[api_key]

  if criteria_config:
    if "match" not in filter_config and len(criteria_config) == 1:
      only_key, only_value = next(iter(criteria_config.items()))
      if only_key in ["from", "to", "subject"]:
        filter_config["match"] = {only_key: only_value}
        return
    filter_config["criteria"] = criteria_config


def api_criteria_to_match(criteria):
  filter_config = {}
  _add_api_criteria(filter_config, criteria or {})
  if "match" in filter_config:
    return filter_config["match"]
  if "criteria" in filter_config:
    return {"raw": format_api_criteria(filter_config["criteria"])}
  return {}


def match_to_api_criteria(match):
  if isinstance(match, dict) and len(match) == 1:
    key, value = next(iter(match.items()))
    if key in ["from", "to", "subject"]:
      return {key: value}
  return {"query": format_match(match)}


def format_api_criteria(criteria):
  terms = []
  for key, value in criteria.items():
    if key == "not_query":
      terms.append("-%s" % value)
    elif key in SEARCH_KEYS:
      terms.append(_format_search_term(key, value))
  return " ".join(terms)


def _add_api_action(filter_config, action):
  actions = {}

  if "addLabelIds" in action:
    actions["add_label_ids"] = action["addLabelIds"]
  if "removeLabelIds" in action:
    actions["remove_label_ids"] = action["removeLabelIds"]
  if "forward" in action:
    actions["forward_to"] = action["forward"]

  if actions:
    filter_config["actions"] = actions


def _normalize_config(config):
  normalized = {"version": config.get("version", 1)}
  normalized["filters"] = [_normalize_filter(filter_config) for filter_config in config.get("filters", [])]
  return normalized


def _normalize_filter(filter_config):
  normalized = {}

  for key in ["id", "label", "match", "criteria", "actions", "properties"]:
    if key in filter_config:
      normalized[key] = filter_config[key]

  for key, value in filter_config.items():
    if key not in normalized:
      normalized[key] = value

  return normalized


def config_to_xml(config):
  root = ET.Element("feed", **{
    "xmlns": ATOM_XMLNS,
    "xmlns:apps": APPS_XMLNS,
  })

  for filter_config in config.get("filters", []):
    entry = ET.SubElement(root, "entry")
    ET.SubElement(entry, "category", term="filter")

    for name, value in _properties_for_filter(filter_config):
      ET.SubElement(entry, "apps:property", **{
        "name": name,
        "value": _encode_property_value(value),
      })

  return _prettify(root)


def parse_match(query):
  query = query.strip()
  parsed = _parse_group(query)
  if parsed is not None:
    return parsed

  parsed = _parse_simple_term(query)
  if parsed is not None:
    return parsed

  return {"raw": query}


def format_match(match):
  if isinstance(match, str):
    return match
  if not isinstance(match, dict):
    raise ValueError("match must be a string or mapping")

  if "raw" in match:
    return match["raw"]
  if any(key in match for key in ["and", "AND", "all"]):
    return "(" + " ".join(format_match(item) for item in _match_items(match, ["and", "AND", "all"])) + ")"
  if any(key in match for key in ["or", "OR", "any"]):
    return "{" + " ".join(format_match(item) for item in _match_items(match, ["or", "OR", "any"])) + "}"
  if "not" in match:
    return "-" + format_match(match["not"])

  parts = []
  for key, value in match.items():
    if key not in SEARCH_KEYS:
      raise ValueError("Unsupported match key: %s" % key)
    if isinstance(value, list):
      parts.extend(_format_search_term(key, item) for item in value)
    else:
      parts.append(_format_search_term(key, value))

  if len(parts) == 1:
    return parts[0]
  return "(" + " ".join(parts) + ")"


def _properties_for_filter(filter_config):
  properties = []

  criteria = filter_config.get("criteria", {})
  for key, prop_name in CRITERIA_TO_PROPERTY.items():
    if key in criteria:
      properties.append((prop_name, criteria[key]))

  if "match" in filter_config:
    properties.append(("hasTheWord", format_match(filter_config["match"])))

  actions = dict(filter_config.get("actions", {}))
  if "label" in filter_config:
    actions.setdefault("label", filter_config["label"])

  for key, prop_name in ACTION_TO_PROPERTY.items():
    if key in actions:
      properties.append((prop_name, actions[key]))

  for name, value in filter_config.get("properties", {}).items():
    properties.append((name, value))

  return properties


def _match_items(match, keys):
  for key in keys:
    if key in match:
      return match[key]
  raise ValueError("Missing match items for keys: %s" % ", ".join(keys))


def _parse_group(query):
  if len(query) < 2:
    return None

  if query[0] == "(" and query[-1] == ")":
    terms = _split_terms(query[1:-1])
    if terms:
      return _group_match("and", terms)

  if query[0] == "{" and query[-1] == "}":
    terms = _split_terms(query[1:-1])
    if terms:
      return _group_match("or", terms)

  if query.startswith("-"):
    return {"not": parse_match(query[1:])}

  return None


def _parse_simple_term(query):
  if len(_split_terms(query)) > 1:
    return None

  key, separator, value = query.partition(":")
  if not separator:
    if " " in query:
      return None
    return {"text": _unquote(query)}

  yaml_key = "delivered_to" if key == "deliveredto" else key
  if yaml_key not in SEARCH_KEYS:
    return None
  return {yaml_key: _unquote(value)}


def _group_match(key, terms):
  parsed_terms = []
  for term in terms:
    parsed = parse_match(term)
    if isinstance(parsed, dict) and key in parsed:
      parsed_terms.extend(parsed[key])
    else:
      parsed_terms.append(parsed)
  return {key: parsed_terms}


def _split_terms(query):
  terms = []
  token = []
  quote = None
  escaped = False
  depth = 0

  for char in query:
    if escaped:
      token.append(char)
      escaped = False
      continue

    if char == "\\" and quote:
      token.append(char)
      escaped = True
      continue

    if quote:
      token.append(char)
      if char == quote:
        quote = None
      continue

    if char in ['"', "'"]:
      token.append(char)
      quote = char
      continue

    if char in ["{", "("]:
      depth += 1
      token.append(char)
      continue

    if char in ["}", ")"]:
      depth -= 1
      token.append(char)
      continue

    if char.isspace() and depth == 0:
      if token:
        terms.append("".join(token))
        token = []
      continue

    token.append(char)

  if token:
    terms.append("".join(token))

  return terms


def _format_search_term(key, value):
  gmail_key = SEARCH_ALIASES.get(key, key)
  value = str(value)
  if gmail_key == "text":
    return _quote_search_value(value)
  return "%s:%s" % (gmail_key, _quote_search_value(value))


def _quote_search_value(value):
  if re.search(r"\s", value):
    return '"' + value.replace('"', '\\"') + '"'
  return value


def _unquote(value):
  if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
    return value[1:-1].replace('\\"', '"')
  return value


def _children_named(element, local_name):
  return [child for child in list(element) if _local_name(child.tag) == local_name]


def _local_name(tag):
  if "}" in tag:
    return tag.rsplit("}", 1)[1]
  if ":" in tag:
    return tag.rsplit(":", 1)[1]
  return tag


def _set_action(filter_config, actions, action_name, value):
  if action_name == "label":
    filter_config["label"] = value
  else:
    actions[action_name] = value


def _encode_property_value(value):
  if value is True:
    return "true"
  if value is False:
    return "false"
  return str(value)


def _decode_property_value(value):
  if value == "true":
    return True
  if value == "false":
    return False
  return value


def _prettify(elem):
  rough_string = ET.tostring(elem, "utf-8")
  reparsed = minidom.parseString(rough_string)
  return reparsed.toprettyxml(indent="  ")


def create_editor_app(user, token):
  app = FastAPI(title="Gmail Filter Editor")
  token_state = {"token": token}
  app.mount("/static", StaticFiles(directory=str(EDITOR_DIR)), name="static")

  @app.get("/", response_class=HTMLResponse)
  def index():
    return HTMLResponse((EDITOR_DIR / "index.html").read_text(), headers={"Cache-Control": "no-store"})

  @app.get("/api/auth/token")
  def get_auth_token():
    return JSONResponse({"token": token_state["token"]}, headers={"Cache-Control": "no-store"})

  @app.put("/api/auth/token")
  async def update_auth_token(request: Request):
    body = await request.json()
    new_token = body.get("token", "").strip()
    if not new_token:
      return JSONResponse({"error": "Token is required"}, status_code=400, headers={"Cache-Control": "no-store"})
    token_state["token"] = new_token
    return JSONResponse({"ok": True}, headers={"Cache-Control": "no-store"})

  @app.get("/api/filters")
  def list_filters():
    try:
      body = gmail_api_request("GET", "/users/%s/settings/filters" % _quote_path(user), token_state["token"])
      return Response(content=body, media_type="application/json", headers={"Cache-Control": "no-store"})
    except SystemExit as error:
      return JSONResponse({"error": str(error)}, status_code=502, headers={"Cache-Control": "no-store"})

  @app.post("/api/filters")
  async def create_filter(request: Request):
    try:
      body = gmail_api_request(
        "POST",
        "/users/%s/settings/filters" % _quote_path(user),
        token_state["token"],
        _filter_create_body(await request.json()),
      )
      return Response(content=body, media_type="application/json", headers={"Cache-Control": "no-store"})
    except SystemExit as error:
      return JSONResponse({"error": str(error)}, status_code=502, headers={"Cache-Control": "no-store"})

  @app.put("/api/filters/{filter_id}")
  async def replace_filter(filter_id: str, request: Request):
    try:
      created = gmail_api_request(
        "POST",
        "/users/%s/settings/filters" % _quote_path(user),
        token_state["token"],
        _filter_create_body(await request.json()),
      )
      gmail_api_request(
        "DELETE",
        "/users/%s/settings/filters/%s" % (_quote_path(user), _quote_path(filter_id)),
        token_state["token"],
      )
      return Response(content=created, media_type="application/json", headers={"Cache-Control": "no-store"})
    except SystemExit as error:
      return JSONResponse({"error": str(error)}, status_code=502, headers={"Cache-Control": "no-store"})

  @app.delete("/api/filters/{filter_id}")
  def delete_filter(filter_id: str):
    try:
      body = gmail_api_request(
        "DELETE",
        "/users/%s/settings/filters/%s" % (_quote_path(user), _quote_path(filter_id)),
        token_state["token"],
      )
      return Response(content=body, media_type="application/json", headers={"Cache-Control": "no-store"})
    except SystemExit as error:
      return JSONResponse({"error": str(error)}, status_code=502, headers={"Cache-Control": "no-store"})

  @app.post("/api/match/parse")
  async def parse_match_endpoint(request: Request):
    try:
      body = await request.json()
      if "criteria" in body:
        match = api_criteria_to_match(body.get("criteria") or {})
      else:
        match = parse_match(body.get("query", ""))
      match_yaml = yaml.safe_dump(match, sort_keys=False)
      return JSONResponse({"yaml": match_yaml}, headers={"Cache-Control": "no-store"})
    except Exception as error:
      return JSONResponse({"error": str(error)}, status_code=400, headers={"Cache-Control": "no-store"})

  @app.post("/api/match/render")
  async def render_match_endpoint(request: Request):
    try:
      body = await request.json()
      match = yaml.safe_load(body.get("yaml", ""))
      criteria = match_to_api_criteria(match)
      return JSONResponse({"query": criteria.get("query", ""), "criteria": criteria}, headers={"Cache-Control": "no-store"})
    except Exception as error:
      return JSONResponse({"error": str(error)}, status_code=400, headers={"Cache-Control": "no-store"})

  @app.get("/api/labels")
  def list_labels():
    try:
      body = gmail_api_request("GET", "/users/%s/labels" % _quote_path(user), token_state["token"])
      return Response(content=body, media_type="application/json", headers={"Cache-Control": "no-store"})
    except SystemExit as error:
      return JSONResponse({"error": str(error)}, status_code=502, headers={"Cache-Control": "no-store"})

  @app.post("/api/labels")
  async def create_label(request: Request):
    try:
      body = gmail_api_request("POST", "/users/%s/labels" % _quote_path(user), token_state["token"], await request.json())
      return Response(content=body, media_type="application/json", headers={"Cache-Control": "no-store"})
    except SystemExit as error:
      return JSONResponse({"error": str(error)}, status_code=502, headers={"Cache-Control": "no-store"})

  @app.patch("/api/labels/{label_id}")
  async def patch_label(label_id: str, request: Request):
    try:
      body = gmail_api_request(
        "PATCH",
        "/users/%s/labels/%s" % (_quote_path(user), _quote_path(label_id)),
        token_state["token"],
        await request.json(),
      )
      return Response(content=body, media_type="application/json", headers={"Cache-Control": "no-store"})
    except SystemExit as error:
      return JSONResponse({"error": str(error)}, status_code=502, headers={"Cache-Control": "no-store"})

  @app.delete("/api/labels/{label_id}")
  def delete_label(label_id: str):
    try:
      body = gmail_api_request(
        "DELETE",
        "/users/%s/labels/%s" % (_quote_path(user), _quote_path(label_id)),
        token_state["token"],
      )
      return Response(content=body, media_type="application/json", headers={"Cache-Control": "no-store"})
    except SystemExit as error:
      return JSONResponse({"error": str(error)}, status_code=502, headers={"Cache-Control": "no-store"})

  return app


def _filter_create_body(filter_config):
  body = dict(filter_config)
  body.pop("id", None)
  return body


def gmail_api_request(method, path, token, body=None):
  data = None
  headers = {
    "Authorization": "Bearer %s" % token,
    "Accept": "application/json",
  }

  if body is not None:
    data = json.dumps(body).encode("utf-8")
    headers["Content-Type"] = "application/json"

  request = urllib.request.Request(
    GMAIL_API_BASE + path,
    data=data,
    headers=headers,
    method=method,
  )

  try:
    with urllib.request.urlopen(request) as response:
      return response.read().decode("utf-8")
  except urllib.error.HTTPError as error:
    error_body = error.read().decode("utf-8")
    if error_body:
      raise SystemExit(error_body)
    raise SystemExit("Gmail API request failed with HTTP %s" % error.code)


def _quote_path(value):
  return urllib.parse.quote(str(value), safe="")
