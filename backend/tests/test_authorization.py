from app.core.authorization import has_permission


def test_system_admin_has_highest_privileges():
    # system_admin must have all system permissions
    all_known_permissions = [
        "auth:session",
        "farms:read",
        "farms:write",
        "farms:read_all",
        "lots:read",
        "lots:read_all",
        "lots:write",
        "events:read",
        "events:read_all",
        "events:create",
        "products:read",
        "products:write",
        "products:read_all",
    ]
    for perm in all_known_permissions:
        assert has_permission("system_admin", perm) is True, (
            f"system_admin must have {perm}"
        )


def test_organization_admin_permissions():
    assert has_permission("organization_admin", "farms:read") is True
    assert has_permission("organization_admin", "farms:write") is True
    assert has_permission("organization_admin", "lots:read") is True
    assert has_permission("organization_admin", "lots:write") is True
    assert has_permission("organization_admin", "products:read") is True
    assert has_permission("organization_admin", "products:write") is True
    assert has_permission("organization_admin", "lots:read_all") is False


def test_grower_cannot_write_products_or_read_all_lots():
    assert has_permission("grower", "products:write") is False
    assert has_permission("grower", "lots:read_all") is False
    assert has_permission("grower", "farms:read") is True
    assert has_permission("grower", "farms:write") is True
