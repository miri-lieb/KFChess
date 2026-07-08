def is_legal_move(piece, r1, c1, r2, c2):
   dr = abs(r2 - r1)
   dc = abs(c2 - c1)
   if not piece:
       return False
   if piece[1] == 'K':
       return max(dr, dc) == 1
   if piece[1] == 'R':
       return (dr > 0 and dc == 0) or (dr == 0 and dc > 0)
   if piece[1] == 'B':
       return dr == dc and dr > 0
   if piece[1] == 'Q':
       return (dr == 0 or dc == 0 or dr == dc) and (dr > 0 or dc > 0)
   if piece[1] == 'N':
       return (dr == 1 and dc == 2) or (dr == 2 and dc == 1)
   if piece[1] == 'P':
        return True
   return False
   