"""Test configuration loading."""

from bot.core.config import settings


def test_settings_load() -> None:
    """Test that settings load correctly.

    Verifies that:
    - Bot token is loaded
    - Database path is valid
    - Storage root is valid
    - Admin IDs are properly loaded as a list
    """
    assert settings.bot_token is not None, "Bot token must be set"
    assert settings.db_path.exists() or settings.db_path.parent.exists(), \
        f"Database path {settings.db_path} or its parent must exist"
    assert settings.storage_root.exists() or settings.storage_root.parent.exists(), \
        f"Storage root {settings.storage_root} or its parent must exist"
    assert isinstance(settings.admin_ids, list), "Admin IDs must be a list"
    print("✅ Settings loaded correctly")


if __name__ == "__main__":
    test_settings_load()
