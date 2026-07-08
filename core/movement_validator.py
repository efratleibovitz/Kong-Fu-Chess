from core.moves.move_factory import MoveFactory

def is_valid_move(token: str, from_pos, to_pos, board) -> bool:
    color = token[0]
    dest_token = board.get_token(to_pos)
    if dest_token != '.' and dest_token[0] == color:
        return False

    strategy = MoveFactory.get_strategy(token[1])
    if not strategy:
        return False
    return strategy.is_valid(from_pos, to_pos, board)
