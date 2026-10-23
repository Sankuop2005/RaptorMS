import unittest

import rbac


class RoleConfigurationTests(unittest.TestCase):
    def test_exactly_five_supported_roles_with_expected_levels(self):
        self.assertEqual(set(rbac.ROLES), {"admin", "manager", "coach", "analyst", "player"})
        self.assertEqual({role: data["level"] for role, data in rbac.ROLES.items()}, {
            "admin": 100, "manager": 80, "coach": 70, "analyst": 60, "player": 50,
        })

    def test_invalid_role_and_missing_permission_are_denied(self):
        self.assertFalse(rbac.has_permission("unknown-role", "teams.view_all"))
        self.assertFalse(rbac.has_permission("player", "system.configure"))
        self.assertFalse(rbac.has_permission("admin", "unknown.operation"))

    def test_role_matrix_is_explicit_and_matches_requested_operations(self):
        expected = {
            "admin": {"users.view_all": True, "users.create": True, "users.update_role": True, "users.delete": True,
                      "teams.view_all": "all", "teams.create": True, "teams.update": "all", "teams.delete": True, "teams.assign_coaches": True,
                      "roster.view": "all", "roster.create": "all", "roster.update": "all", "roster.delete": True,
                      "performance.view_all": "all", "performance.create": "all", "performance.update": "all", "performance.delete": True,
                      "matches.view_all": "all", "matches.create": True, "matches.update": "all", "matches.delete": True,
                      "financial.view": "all", "financial.create": True, "financial.update": "all", "financial.delete": True,
                      "reports.view": "all", "analytics.view": "all", "admin.access": True, "system.configure": True},
            "manager": {"users.view_all": False, "users.create": False, "users.update_role": False, "users.delete": False,
                        "teams.view_all": "all", "teams.create": True, "teams.update": "all", "teams.delete": False, "teams.assign_coaches": True,
                        "roster.view": "all", "roster.create": "all", "roster.update": "all", "roster.delete": "all",
                        "performance.view_all": "all", "performance.create": True, "performance.update": "all", "performance.delete": False,
                        "matches.view_all": "all", "matches.create": True, "matches.update": "all", "matches.delete": False,
                        "financial.view": "all", "financial.create": True, "financial.update": "all", "financial.delete": False,
                        "reports.view": "all", "analytics.view": "all", "admin.access": False, "system.configure": False},
            "coach": {"users.view_all": False, "users.create": False, "users.update_role": False, "users.delete": False,
                      "teams.view_all": "assigned", "teams.create": False, "teams.update": "assigned", "teams.delete": False, "teams.assign_coaches": False,
                      "roster.view": "assigned", "roster.create": "assigned", "roster.update": False, "roster.delete": "assigned",
                      "performance.view_all": "assigned", "performance.create": "assigned", "performance.update": "assigned", "performance.delete": False,
                      "matches.view_all": "assigned", "matches.create": False, "matches.update": False, "matches.delete": False,
                      "financial.view": False, "financial.create": False, "financial.update": False, "financial.delete": False,
                      "reports.view": "assigned", "analytics.view": "assigned", "admin.access": False, "system.configure": False},
            "analyst": {"users.view_all": False, "users.create": False, "users.update_role": False, "users.delete": False,
                        "teams.view_all": "assigned", "teams.create": False, "teams.update": False, "teams.delete": False, "teams.assign_coaches": False,
                        "roster.view": "assigned", "roster.create": "assigned", "roster.update": False, "roster.delete": "assigned",
                        "performance.view_all": "assigned", "performance.create": False, "performance.update": False, "performance.delete": False,
                        "matches.view_all": "assigned", "matches.create": False, "matches.update": False, "matches.delete": False,
                        "financial.view": False, "financial.create": False, "financial.update": False, "financial.delete": False,
                        "reports.view": "assigned", "analytics.view": "assigned", "admin.access": False, "system.configure": False},
            "player": {"users.view_all": False, "users.create": False, "users.update_role": False, "users.delete": False,
                       "teams.view_all": "own", "teams.create": False, "teams.update": False, "teams.delete": False, "teams.assign_coaches": False,
                       "roster.view": "own", "roster.create": False, "roster.update": False, "roster.delete": False,
                       "performance.view_all": "own", "performance.create": "own", "performance.update": False, "performance.delete": False,
                       "matches.view_all": "own", "matches.create": False, "matches.update": False, "matches.delete": False,
                       "financial.view": False, "financial.create": False, "financial.update": False, "financial.delete": False,
                       "reports.view": "own", "analytics.view": "own", "admin.access": False, "system.configure": False},
        }
        for role, permissions in expected.items():
            with self.subTest(role=role):
                self.assertEqual(rbac.ROLES[role]["permissions"], permissions)


class ResourceScopeTests(unittest.TestCase):
    def test_assigned_roles_cannot_cross_team_boundaries(self):
        self.assertTrue(rbac.resource_allowed("coach", "performance.view_all", team_id=4, assigned_team_ids={4}))
        self.assertFalse(rbac.resource_allowed("coach", "performance.view_all", team_id=5, assigned_team_ids={4}))
        self.assertTrue(rbac.resource_allowed("analyst", "matches.view_all", team_id=4, assigned_team_ids={4}))
        self.assertFalse(rbac.resource_allowed("analyst", "matches.view_all", team_id=5, assigned_team_ids={4}))

    def test_player_is_limited_to_linked_player_and_team(self):
        self.assertTrue(rbac.resource_allowed("player", "performance.view_all", team_id=4, player_id=12, own_team_id=4, own_player_id=12))
        self.assertFalse(rbac.resource_allowed("player", "performance.view_all", team_id=4, player_id=13, own_team_id=4, own_player_id=12))
        self.assertTrue(rbac.resource_allowed("player", "teams.view_all", team_id=4, own_team_id=4, own_player_id=12))
        self.assertFalse(rbac.resource_allowed("player", "teams.view_all", team_id=5, own_team_id=4, own_player_id=12))
        self.assertFalse(rbac.resource_allowed("player", "performance.create", team_id=4, player_id=13, own_team_id=4, own_player_id=12))

    def test_global_access_is_explicit_not_derived_from_level(self):
        self.assertTrue(rbac.resource_allowed("manager", "financial.view", team_id=99))
        self.assertFalse(rbac.resource_allowed("manager", "admin.access"))
        self.assertFalse(rbac.resource_allowed("coach", "admin.access", team_id=1, assigned_team_ids={1}))

    def test_invalid_role_is_denied_for_resource_scopes(self):
        self.assertFalse(rbac.resource_allowed("unknown-role", "teams.view_all", team_id=1, assigned_team_ids={1}))
        self.assertFalse(rbac.resource_allowed(None, "teams.view_all", team_id=1))


class TeamAssignmentTests(unittest.TestCase):
    def test_only_manager_and_admin_can_assign_supported_team_staff(self):
        self.assertTrue(rbac.can_assign_team_role("manager", "coach"))
        self.assertFalse(rbac.can_assign_team_role("manager", "analyst"))
        self.assertTrue(rbac.can_assign_team_role("admin", "analyst"))
        self.assertFalse(rbac.can_assign_team_role("coach", "coach"))
        self.assertFalse(rbac.can_assign_team_role("admin", "player"))


if __name__ == "__main__":
    unittest.main()
