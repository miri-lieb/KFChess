import asyncio

from model.piece import BLACK, WHITE
from network.lobby import OBSERVER, ShellLoginLobby


def test_shell_login_lobby_assigns_white_then_black():
    async def scenario():
        lobby = ShellLoginLobby()
        white = await lobby.login("alice")
        black = await lobby.login("bob")
        assert white.role == WHITE
        assert white.color == WHITE
        assert black.role == BLACK
        assert black.color == BLACK
        assert lobby.is_ready()

    asyncio.run(scenario())


def test_shell_login_lobby_assigns_observer_after_two_players():
    async def scenario():
        lobby = ShellLoginLobby()
        await lobby.login("alice")
        await lobby.login("bob")
        observer = await lobby.login("carol")
        assert observer.role == OBSERVER
        assert observer.color is None

    asyncio.run(scenario())


def test_shell_login_lobby_normalizes_and_releases_usernames():
    async def scenario():
        lobby = ShellLoginLobby()
        white = await lobby.login("\udcd7miri")
        released = lobby.release("miri")
        black = await lobby.login("sari")
        assert white.username == "miri"
        assert released is not None
        assert black.role == WHITE

    asyncio.run(scenario())
