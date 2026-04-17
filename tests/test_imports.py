"""Test all imports work correctly."""


def test_core_imports() -> None:
    """Test core module imports.

    Verifies that all core components can be imported:
    - settings: Configuration object
    - bot: Bot instance
    - dp: Dispatcher instance
    - setup_logging: Logging configuration function
    """
    from bot.core import settings, bot, dp, setup_logging
    print("✅ Core imports OK")


def test_database_imports() -> None:
    """Test database imports.

    Verifies that database components can be imported:
    - Database: Main database class
    - Models: Protocol, Moderator, User, Document
    - Repositories: All repository classes
    """
    from bot.database import Database
    from bot.database.models import Protocol, Moderator, User, Document
    from bot.database.repositories import (
        ProtocolRepository,
        ModeratorRepository,
        UserRepository,
        DocumentRepository,
    )
    print("✅ Database imports OK")


def test_handler_imports() -> None:
    """Test handler imports.

    Verifies that all handler modules can be imported:
    - common: Start, cancel, language handlers
    - download: Protocol download handlers
    - user: User-facing handlers
    - admin: Admin panel handlers
    """
    from bot.handlers import common, download, user, admin
    print("✅ Handler imports OK")


def test_middleware_imports() -> None:
    """Test middleware imports.

    Verifies that all middlewares can be imported:
    - DatabaseMiddleware: Repository injection
    - ThrottlingMiddleware: Rate limiting
    - LoggingMiddleware: Request logging
    """
    from bot.middlewares import (
        DatabaseMiddleware,
        ThrottlingMiddleware,
        LoggingMiddleware,
    )
    print("✅ Middleware imports OK")


def test_service_imports() -> None:
    """Test service imports.

    Verifies that all service classes can be imported:
    - StorageService: File storage management
    - ProtocolService: Protocol business logic
    """
    from bot.services import StorageService, ProtocolService
    print("✅ Service imports OK")


def test_products_import() -> None:
    """Test canonical product list imports.

    Verifies the shared product registry is available:
    - PRODUCT_NAMES: tuple of known product names
    - get_predefined_products: sanitized list helper
    """
    from bot.core.products import PRODUCT_NAMES, get_predefined_products
    assert isinstance(PRODUCT_NAMES, tuple)
    assert len(get_predefined_products()) > 0
    print("✅ Products import OK")


def test_utils_imports() -> None:
    """Test utilities imports.

    Verifies that utility functions can be imported:
    - General utilities: slugify, protocol_storage_key, format_size, safe_send_many
    - Protocol utilities: format_protocol_text, send_protocol_list
    """
    from bot.utils import slugify, protocol_storage_key, format_size, safe_send_many
    from bot.utils.protocol import format_protocol_text, send_protocol_list
    print("✅ Utils imports OK")


if __name__ == "__main__":
    test_core_imports()
    test_database_imports()
    test_handler_imports()
    test_middleware_imports()
    test_service_imports()
    test_products_import()
    test_utils_imports()
    print("\n🎉 All imports successful!")
