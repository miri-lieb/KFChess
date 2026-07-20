# ק
ונג פו שחמט — הנחיות עיצוב ובדיקות

## בעקרון
הפרויקט בנוי כדי להפריד בין לוגיקת המודל, כללי התנועה, מנוע המשחק, תזמון בזמן אמת, בקר קלט, תצוגה ו־I/O טקסט.
המטרה היא לכתוב קוד קטן, ברור וניתן לבדיקה.

## מבנה שכבות מומלץ

1. **Model**
   - Board, Position, Piece, GameState
   - רק לוגיקה של לוח וכלים
   - לא פיקסלים, לא קלט, לא רינדור

2. **Movement rules**
   - חוקים לכל כלי: rook, bishop, queen, knight, king, pawn
   - מחזירות יעדים חוקיים
   - סטייטלס, לא משתנות Board

3. **RuleEngine**
   - בודק אם מהלך חוקי לפי מצב הלוח
   - מחזיר תוצאה עם `is_valid` ו־`reason`
   - לא משנה Board

4. **RealTimeArbiter**
   - מנהל תנועות פעילות לאורך זמן
   - אוסף אובייקטים של Motion
   - מקדם זמן מדומה ומחזיר פתרון הגעה

5. **GameEngine**
   - מתאם שירות-אפליקציה
   - מקבל בקשות תנועה, דוחה game_over או motion_in_progress
   - עובד עם RuleEngine ו־RealTimeArbiter
   - מטפל בסיום משחק ובאכילת מלך

6. **Controller**
   - ממפה קליקים לפקודות משחק
   - שומר בחירת כלי
   - לא עושה אימות שחמט

7. **IO / Text I/O**
   - BoardParser: קורא לוח מטקסט
   - BoardPrinter: מדפיס לוח לוגי
   - TextTestRunner: מריץ בדיקות עם פקודות טקסט

8. **Renderer**
   - רק תצוגה
   - מקבל snapshot לקריאה בלבד
   - לא משנה מצב משחק

## כללי פרויקט חשובים

- `Board` לא יודע על פיקסלים או קליקים.
- חוקים לכל כלי נותנים יעדים, לא מבצעים מזיזים.
- `RuleEngine` מאמת, `GameEngine` מחליט, `Arbiter` מפעיל תנועה.
- `print board` מראה תמיד את הלוח הלוגי הנוכחי.
- `wait(ms)` מקדם זמן מדומה, לא שינה אמיתית.
- תנועה פעילה אחת בלבד בכל רגע במסלול המשותף.
- אכילת מלך מסיימת את המשחק.

## API מינימלי בין השכבות

- `BoardParser.parse(text) -> Board`
- `BoardPrinter.print(board) -> text`
- `BoardMapper.pixel_to_cell(x, y) -> Position | None`
- `Controller.click(x, y)`
- `GameEngine.request_move(source, destination) -> MoveResult`
- `GameEngine.wait(ms)`
- `RuleEngine.validate_move(board, source, destination) -> MoveValidation`
- `RealTimeArbiter.has_active_motion() -> bool`
- `RealTimeArbiter.advance_time(ms) -> Motion | None`

## בדיקות

### עדיפות
1. בדיקות יחידה לכל קומפוננטה
2. בדיקות אינטגרציה טקסטואליות עם `print board`

### מה לבדוק
- `Position` שווה רק אם שורה ועמודה זהים
- `Board` שומר וצורך כלים נכון
- `PieceRules` מחזירות יעדים נכונים לכל כלי
- `RuleEngine` מחזיר סיבות נכונות (outside_board, empty_source, friendly_destination, illegal_piece_move)
- `GameEngine` דוחה `game_over` ו־`motion_in_progress`
- `RealTimeArbiter` משלים תנועה אחרי זמן נכון
- `Controller` בוחר כלי ואז שולח מהלך
- `BoardParser` ו־`BoardPrinter` round-trip

### בדיקות טקסט
ה־DSL מכיל רק:
- `Board`
- `click X Y`
- `wait MS`
- `print board`

`print board` הוא מנגנון האימות היחיד באינטגרציה.

## דרישות חשובות לשכבות

### Model
- איננו תלוי בשום דבר מעליו
- אחראי רק על מצב לוח ולתפוסה

### RuleEngine
- אימות חוקיות בלבד
- לא משנה טקסט או לוח

### GameEngine
- תזמון, מצב משחק, תחילת תנועה
- לא מתערב בחוקיות ספציפית לכל כלי

### Controller
- המרת פיקסלים לתאים
- בחירת כלי ושליחת בקשה
- לא מבצע תנועה ישירה

### RealTimeArbiter
- תנועה פעילה בלבד
- יעד תנועה, זמן, הגעה
- לא יודע כללי שחמט

## דרישות נוספות

- אין castling, en passant, promotion או שחמט מלא.
- כלי יכול לאכול כלי אויב ביעד.
- כלים נעים לפי חוק התנועה שלהם.
- לוח לוגי משתנה רק בהגעה.

## סיכום
הקובץ הזה מסכם את ההנחיות העיקריות מהמסמך. אם את רוצה, אפשר גם ליצור קובץ `tests/UNIT_GUIDELINES.md` שמפרט את בדיקות היחידה שצריך לכתוב לכל שכבה.
