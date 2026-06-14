import argparse
import json
import os
import sys

import uvicorn

import FilterConfig


def main(argv=None):
  argv = sys.argv[1:] if argv is None else argv
  if argv and argv[0] == "convert":
    _convert_main(argv[1:], "%s convert" % sys.argv[0])
    return
  if argv and argv[0] == "api":
    _api_main(argv[1:], "%s api" % sys.argv[0])
    return
  if argv and argv[0] == "editor":
    _editor_main(argv[1:], "%s editor" % sys.argv[0])
    return

  parser = argparse.ArgumentParser(description="Convert and manage Gmail filters.")
  subparsers = parser.add_subparsers(dest="command", required=True)
  convert_parser = subparsers.add_parser("convert", help="Convert Gmail filter files between XML, JSON, and YAML.")
  convert_parser.add_argument("input")
  convert_parser.add_argument("output", nargs="?")
  api_parser = subparsers.add_parser("api", help="Call Gmail filter API methods.")
  api_parser.add_argument("args", nargs=argparse.REMAINDER)
  editor_parser = subparsers.add_parser("editor", help="Launch a local Gmail filter editor.")
  editor_parser.add_argument("args", nargs=argparse.REMAINDER)
  parser.parse_args(argv)


def _convert_main(argv, prog):
  parser = argparse.ArgumentParser(prog=prog, description="Convert Gmail filter XML/API JSON and readable YAML.")
  parser.add_argument("input")
  parser.add_argument("output", nargs="?")
  args = parser.parse_args(argv)

  source_format = _format_from_extension(args.input)
  target_format = _format_from_extension(args.output) if args.output else _opposite_format(source_format)

  with open(args.input) as input_file:
    input_text = input_file.read()

  if source_format == "xml" and target_format == "yaml":
    output_text = FilterConfig.xml_to_yaml_text(input_text)
  elif source_format == "json" and target_format == "yaml":
    output_text = FilterConfig.api_json_to_yaml_text(input_text)
  elif source_format == "yaml" and target_format == "xml":
    output_text = FilterConfig.yaml_to_xml_text(input_text)
  else:
    raise SystemExit("Expected xml/json -> yaml or yaml -> xml conversion")

  if args.output:
    with open(args.output, "w") as output_file:
      output_file.write(output_text)
  else:
    sys.stdout.write(output_text)


def _api_main(argv, prog):
  auth_parser = argparse.ArgumentParser(add_help=False)
  auth_parser.add_argument("--user", default="me", help="Gmail user ID or `me` for the authenticated user.")
  auth_parser.add_argument("--token", help="OAuth access token. Defaults to GMAIL_FILTER_TOKEN or GOOGLE_ACCESS_TOKEN.")

  parser = argparse.ArgumentParser(prog=prog, description="Call Gmail API methods.")
  subparsers = parser.add_subparsers(dest="command", required=True)

  filters_parser = subparsers.add_parser("filters", help="Call Gmail filter API methods.")
  filters_subparsers = filters_parser.add_subparsers(dest="filter_command", required=True)

  filters_subparsers.add_parser("list", parents=[auth_parser], help="List Gmail filters.")

  filter_get_parser = filters_subparsers.add_parser("get", parents=[auth_parser], help="Get one Gmail filter.")
  filter_get_parser.add_argument("id", help="Gmail filter ID.")

  filter_delete_parser = filters_subparsers.add_parser("delete", parents=[auth_parser], help="Delete one Gmail filter.")
  filter_delete_parser.add_argument("id", help="Gmail filter ID.")

  filter_create_parser = filters_subparsers.add_parser("create", parents=[auth_parser], help="Create a Gmail filter from API JSON.")
  filter_create_parser.add_argument("json_file", nargs="?", help="Filter JSON file. Reads stdin when omitted.")

  labels_parser = subparsers.add_parser("labels", help="Call Gmail label API methods.")
  labels_subparsers = labels_parser.add_subparsers(dest="label_command", required=True)

  labels_subparsers.add_parser("list", parents=[auth_parser], help="List Gmail labels.")

  label_get_parser = labels_subparsers.add_parser("get", parents=[auth_parser], help="Get one Gmail label.")
  label_get_parser.add_argument("id", help="Gmail label ID.")

  label_delete_parser = labels_subparsers.add_parser("delete", parents=[auth_parser], help="Delete one Gmail label.")
  label_delete_parser.add_argument("id", help="Gmail label ID.")

  label_create_parser = labels_subparsers.add_parser("create", parents=[auth_parser], help="Create a Gmail label from API JSON.")
  label_create_parser.add_argument("json_file", nargs="?", help="Label JSON file. Reads stdin when omitted.")

  label_patch_parser = labels_subparsers.add_parser("patch", parents=[auth_parser], help="Patch a Gmail label from API JSON.")
  label_patch_parser.add_argument("id", help="Gmail label ID.")
  label_patch_parser.add_argument("json_file", nargs="?", help="Label JSON file. Reads stdin when omitted.")

  label_update_parser = labels_subparsers.add_parser("update", parents=[auth_parser], help="Replace a Gmail label from API JSON.")
  label_update_parser.add_argument("id", help="Gmail label ID.")
  label_update_parser.add_argument("json_file", nargs="?", help="Label JSON file. Reads stdin when omitted.")

  args = parser.parse_args(argv)
  token = _load_access_token(args)

  if args.command == "filters":
    response = _handle_filter_api_command(args, token)
  elif args.command == "labels":
    response = _handle_label_api_command(args, token)
  else:
    raise SystemExit("Unknown API command: %s" % args.command)

  sys.stdout.write(response)
  if response and not response.endswith("\n"):
    sys.stdout.write("\n")


def _handle_filter_api_command(args, token):
  filter_base_path = "/users/%s/settings/filters" % FilterConfig._quote_path(args.user)

  if args.filter_command == "list":
    return FilterConfig.gmail_api_request("GET", filter_base_path, token)
  if args.filter_command == "get":
    return FilterConfig.gmail_api_request("GET", "%s/%s" % (filter_base_path, FilterConfig._quote_path(args.id)), token)
  if args.filter_command == "delete":
    return FilterConfig.gmail_api_request("DELETE", "%s/%s" % (filter_base_path, FilterConfig._quote_path(args.id)), token)
  if args.filter_command == "create":
    return FilterConfig.gmail_api_request("POST", filter_base_path, token, _read_api_json_body(args.json_file))

  raise SystemExit("Unknown filter API command: %s" % args.filter_command)


def _handle_label_api_command(args, token):
  label_base_path = "/users/%s/labels" % FilterConfig._quote_path(args.user)

  if args.label_command == "list":
    return FilterConfig.gmail_api_request("GET", label_base_path, token)
  if args.label_command == "get":
    return FilterConfig.gmail_api_request("GET", "%s/%s" % (label_base_path, FilterConfig._quote_path(args.id)), token)
  if args.label_command == "delete":
    return FilterConfig.gmail_api_request("DELETE", "%s/%s" % (label_base_path, FilterConfig._quote_path(args.id)), token)
  if args.label_command == "create":
    return FilterConfig.gmail_api_request("POST", label_base_path, token, _read_api_json_body(args.json_file))
  if args.label_command == "patch":
    return FilterConfig.gmail_api_request("PATCH", "%s/%s" % (label_base_path, FilterConfig._quote_path(args.id)), token, _read_api_json_body(args.json_file))
  if args.label_command == "update":
    return FilterConfig.gmail_api_request("PUT", "%s/%s" % (label_base_path, FilterConfig._quote_path(args.id)), token, _read_api_json_body(args.json_file))

  raise SystemExit("Unknown label API command: %s" % args.label_command)


def _editor_main(argv, prog):
  parser = argparse.ArgumentParser(prog=prog, description="Launch a local Gmail filter editor.")
  parser.add_argument("--host", default="127.0.0.1")
  parser.add_argument("--port", default=8080, type=int)
  parser.add_argument("--user", default="me", help="Gmail user ID or `me` for the authenticated user.")
  parser.add_argument("--token", help="OAuth access token. Defaults to GMAIL_FILTER_TOKEN, GOOGLE_ACCESS_TOKEN, or ./oauth_token.")
  args = parser.parse_args(argv)
  token = _load_access_token(args)

  print("Serving Gmail filter editor at http://%s:%s/" % (args.host, args.port))
  uvicorn.run(FilterConfig.create_editor_app(args.user, token), host=args.host, port=args.port)


def _load_access_token(args):
  token = (
    args.token
    or os.environ.get("GMAIL_FILTER_TOKEN")
    or os.environ.get("GOOGLE_ACCESS_TOKEN")
    or _read_local_oauth_token()
  )
  if not token:
    raise SystemExit("Missing OAuth access token. Pass --token, set GMAIL_FILTER_TOKEN, or create ./oauth_token.")
  return token


def _read_local_oauth_token():
  if not os.path.exists("oauth_token"):
    return None
  with open("oauth_token") as token_file:
    token = token_file.read().strip()
  return token or None


def _read_api_json_body(path):
  if path:
    with open(path) as json_file:
      return json.load(json_file)
  return json.load(sys.stdin)


def _format_from_extension(path):
  lower = path.lower()
  if lower.endswith(".xml"):
    return "xml"
  if lower.endswith(".yaml") or lower.endswith(".yml"):
    return "yaml"
  if lower.endswith(".json"):
    return "json"
  raise SystemExit("Could not infer file format from extension: %s" % path)


def _opposite_format(source_format):
  if source_format in ["xml", "json"]:
    return "yaml"
  if source_format == "yaml":
    return "xml"
  raise SystemExit("Could not infer output format for source format: %s" % source_format)
