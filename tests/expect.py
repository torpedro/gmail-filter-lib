import ast
import difflib
import textwrap


def _format_expected_literal(indent, actual):
  lines = ['%s"""' % indent]
  lines.extend("%s%s" % (indent, line) for line in actual.rstrip().splitlines())
  lines.append('%s"""' % indent)
  return "\n".join(lines)


def _replace_string_literal(source, node, replacement):
  lines = source.splitlines(keepends=True)
  start_line = node.lineno - 1
  end_line = node.end_lineno - 1

  prefix = lines[start_line][:node.col_offset]
  suffix = lines[end_line][node.end_col_offset:]
  lines[start_line:end_line + 1] = [prefix + replacement.lstrip() + suffix]
  return "".join(lines)


def _accept_inline_expected(path, name, actual):
  source = path.read_text()
  tree = ast.parse(source)

  for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
      continue
    if not isinstance(node.func, ast.Name) or node.func.id != "assert_matches_expected":
      continue
    if len(node.args) < 3:
      continue

    name_arg = node.args[1]
    expected_arg = node.args[2]
    if not isinstance(name_arg, ast.Constant) or name_arg.value != name:
      continue
    if not isinstance(expected_arg, ast.Constant) or not isinstance(expected_arg.value, str):
      continue

    indent = " " * expected_arg.col_offset
    replacement = _format_expected_literal(indent, actual)
    updated = _replace_string_literal(source, expected_arg, replacement)
    path.write_text(updated)
    return

  raise AssertionError("Could not find inline expected output for %s in %s" % (name, path))


def assert_matches_expected(request, name, expected, actual):
  expected = textwrap.dedent(expected).strip() + "\n"
  actual = actual.rstrip() + "\n"

  if request.config.getoption("--accept"):
    if actual != expected:
      _accept_inline_expected(request.node.path, name, actual)
    return

  if actual != expected:
    diff = "".join(
      difflib.unified_diff(
        expected.splitlines(keepends=True),
        actual.splitlines(keepends=True),
        fromfile="expected:%s" % name,
        tofile="actual",
      )
    )
    raise AssertionError("Output differed from expected:\n%s" % diff)
