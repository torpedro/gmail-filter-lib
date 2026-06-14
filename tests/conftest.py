def pytest_addoption(parser):
  parser.addoption(
    "--accept",
    action="store_true",
    default=False,
    help="Update inline expected output for expect-style tests.",
  )
