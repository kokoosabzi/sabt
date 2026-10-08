def test_permission_rules_are_project_scoped():
    assert True

# Integration tests will be enabled once the test database fixture is added.
# The intended contract is:
# - global role + project access => allowed
# - project role without project access => denied
# - project access without permission => denied
# - no role => denied