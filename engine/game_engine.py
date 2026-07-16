from dataclasses import dataclass
from typing import List

from model.board import Board
from model.piece import Piece, PAWN, QUEEN, WHITE, BLACK
from model.player import Player
from model.position import Position
from realtime.real_time_arbiter import RealTimeArbiter
from rules.rule_engine import MoveValidation, validate_move
from rules.piece_rules import legal_destinations

@dataclass
class MoveResult:
    is_accepted: bool
    reason: str

class GameEngine:
    def __init__(self, board: Board):
        self.board = board
        self.arbiter = RealTimeArbiter(board)
        self.game_over = False
        # initialize players for the two sides
        self.players = {
            WHITE: Player(color=WHITE),
            BLACK: Player(color=BLACK),
        }
        self.winner = None

    def request_move(self, source: Position, destination: Position) -> MoveResult:
        if self.game_over:
            return MoveResult(False, "game_over")

        validation = validate_move(self.board, source, destination)
        if not validation.is_valid:
            return MoveResult(False, validation.reason)

        piece = self.board.get_piece(source)
        if piece is None:
            return MoveResult(False, "empty_source")

        distance = max(abs(destination.row - source.row), abs(destination.col - source.col))
        duration_ms = max(1, distance * 1000)

        self.arbiter.start_motion(piece, source, destination, duration_ms)
        return MoveResult(True, "ok")

    def wait(self, ms: int):
        arrived = self.arbiter.advance_time(ms)
        events = []
        for motion in arrived:
            captured = self._resolve_arrival(motion)
            events.append({"motion": motion, "captured": captured})
        return events

    def _resolve_arrival(self, motion):
        # מטפל בסיום תנועה: קובע יעד סופי, מטפל באכילה ובקידום רגלי.
        attacker = motion.piece
        destination = motion.destination
        captured = None

        if motion.return_to_fallback:
            # אם היעד נתפס ע"י כלי מאותו צבע, מחפשים משבצת חלופית חוקית ופנויה.
            allowed_destinations = legal_destinations(self.board, attacker)
            fallback_positions = [
                pos
                for pos in allowed_destinations
                if pos != destination and self.board.get_piece(pos) is None
            ]
            if fallback_positions:
                # בוחרים את החלופה הקרובה ביותר ליעד המקורי.
                final_position = min(
                    fallback_positions,
                    key=lambda pos: abs(pos.row - destination.row) + abs(pos.col - destination.col),
                )
            else:
                # אם אין חלופה, הכלי חוזר למשבצת המקור.
                final_position = motion.source
        else:
            # מסלול רגיל: אם יש יריב ביעד, מבצעים אכילה ומעדכנים מצב משחק.
            target = self.board.get_piece(destination)
            if target is not None and target.color != attacker.color:
                # register capture with the capturing player
                capturer = self.players.get(attacker.color)
                if target.kind == "king":
                    # record winner; explicit win_conditions check can be run elsewhere
                    self.game_over = True
                    self.winner = capturer
                self.board.remove_piece(destination)
                captured = target
                if capturer is not None:
                    capturer.capture(captured)
            final_position = destination

        if attacker.kind == PAWN:
            # קידום רגלי לשורה האחרונה: מחליפים את הכלי במלכה.
            promotion_row = 0 if attacker.color == WHITE else self.board.height - 1
            if final_position.row == promotion_row:
                attacker = Piece(
                    id=f"Q{attacker.color[0].upper()}-{final_position.row}-{final_position.col}",
                    color=attacker.color,
                    kind=QUEEN,
                    cell=final_position,
                    state=attacker.state,
                )

        # מציבים את הכלי (או המלכה החדשה) במיקום הסופי על הלוח.
        attacker.cell = final_position
        self.board.add_piece(final_position, attacker)
        return captured
