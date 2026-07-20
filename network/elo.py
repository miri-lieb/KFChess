from config import ELO_K_FACTOR

def compute_elo(winner_elo: int, loser_elo: int, k: int = ELO_K_FACTOR) -> tuple[int, int]:
    """Return (new_winner_elo, new_loser_elo) using standard ELO formula."""
    expected_winner = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    expected_loser = 1 - expected_winner
    new_winner = round(winner_elo + k * (1 - expected_winner))
    new_loser = round(loser_elo + k * (0 - expected_loser))
    return new_winner, new_loser