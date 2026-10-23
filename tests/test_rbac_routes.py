import unittest

import db
import rbac
import server
from server import PortalHandler


class EntityRouteAuthorizationTests(unittest.TestCase):
    def test_every_role_is_checked_against_entity_operation_permissions(self):
        expected = {
            "admin": {"players": (True, True, True, True), "teams": (True, True, True, True), "matches": (True, True, True, True), "tournaments": (True, True, True, True), "expenses": (True, True, True, True), "performance_records": (True, True, True, True)},
            "manager": {"players": (True, True, True, True), "teams": (True, True, True, False), "matches": (True, True, True, False), "tournaments": (True, True, True, False), "expenses": (True, True, True, False), "performance_records": (True, True, True, False)},
            "coach": {"players": (True, True, False, True), "teams": (True, False, True, False), "matches": (True, False, False, False), "tournaments": (True, False, False, False), "expenses": (False, False, False, False), "performance_records": (True, True, True, False)},
            "analyst": {"players": (True, True, False, True), "teams": (True, False, False, False), "matches": (True, False, False, False), "tournaments": (True, False, False, False), "expenses": (False, False, False, False), "performance_records": (True, False, False, False)},
            "player": {"players": (True, False, False, False), "teams": (True, False, False, False), "matches": (True, False, False, False), "tournaments": (True, False, False, False), "expenses": (False, False, False, False), "performance_records": (True, True, False, False)},
        }
        operations = ("view", "create", "update", "delete")
        for role, modules in expected.items():
            for module, permissions in modules.items():
                for operation, expected_allowed in zip(operations, permissions):
                    with self.subTest(role=role, module=module, operation=operation):
                        permission = PortalHandler.entity_permission(module, operation)
                        self.assertEqual(bool(permission and rbac.has_permission(role, permission)), expected_allowed)

    def test_user_and_admin_routes_are_admin_only(self):
        for role in rbac.ROLES:
            expected = role == "admin"
            for permission in ("users.view_all", "users.create", "users.update_role", "users.delete", "admin.access", "system.configure"):
                with self.subTest(role=role, permission=permission):
                    self.assertEqual(rbac.has_permission(role, permission), expected)

    def test_unknown_entity_operation_has_no_route_permission(self):
        self.assertIsNone(PortalHandler.entity_permission("expenses", "export"))
        self.assertIsNone(PortalHandler.entity_permission("users", "view"))

    def test_entity_route_matches_every_table_including_underscored_names(self):
        for table in db.TABLES:
            with self.subTest(table=table):
                self.assertIsNotNone(server.ENTITY_ROUTE.fullmatch(f"/api/entities/{table}"))
                self.assertIsNotNone(server.ENTITY_ROUTE.fullmatch(f"/api/entities/{table}/1"))


if __name__ == "__main__":
    unittest.main()
