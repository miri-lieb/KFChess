from model.piece import BLACK, WHITE
from network.lobby import OBSERVER, ShellLoginLobby


def test_shell_login_lobby_assigns_white_then_black():
    lobby = ShellLoginLobby()

    white = lobby.login("alice")
    black = lobby.login("bob")

    assert white.role == WHITE
    assert white.color == WHITE
    assert black.role == BLACK
    assert black.color == BLACK
    assert lobby.is_ready()


def test_shell_login_lobby_assigns_observer_after_two_players():
    lobby = ShellLoginLobby()
    lobby.login("alice")
    lobby.login("bob")
    observer = lobby.login("carol")
    assert observer.role == OBSERVER
    assert observer.color is None


def test_shell_login_lobby_normalizes_and_releases_usernames():
    lobby = ShellLoginLobby()

    white = lobby.login("\udcd7miri")
    released = lobby.release("miri")
    black = lobby.login("sari")

    assert white.username == "miri"
    assert released is not None
    assert black.role == WHITE
