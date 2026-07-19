# KFChess Architecture Fixes - Implementation Plan

## Issues to Fix

### 1. Dead/Duplicate Class: `GameState` in `model/game_state.py`
- **File**: `/Users/semliebeskind/Documents/KFChess/model/game_state.py` (6 lines)
- **Problem**: Unused - no imports anywhere in codebase
- **Fix**: Delete the file entirely
- **Keep**: `GameState` in `engine/game_runner.py` as single source of truth

### 2. Duplicate `WinResult` Definition
- **Files**: `rules/interfaces.py` (lines 15-18) AND `rules/win_conditions.py` (lines 8-11)
- **Problem**: Both define identical `@dataclass WinResult`
- **Fix**: 
  - Keep definition in `interfaces.py` (already exported)
  - Remove duplicate from `win_conditions.py` and import from `interfaces`

### 3. Duplicate `PromotionResult` Definition  
- **Files**: `rules/interfaces.py` (lines 21-24) AND `rules/promotion.py` (lines 10-13)
- **Problem**: Both define identical `@dataclass PromotionResult`
- **Fix**:
  - Keep definition in `interfaces.py` (already exported)
  - Remove duplicate from `promotion.py` and import from `interfaces`

### 4. Inconsistent Dependency Injection / Dead Field in `engine/game_engine.py`
- **Issue A** (line 156): `_resolve_arrival()` creates new `StandardPromotionService()` instead of using `self._promotion`
  - **Fix**: Replace local instantiation with `self._promotion`
- **Issue B**: `StandardMoveValidator.validate()` creates local `StandardMoveGenerator()` instead of using injected one
  - **Fix**: Add optional `MoveGenerator` parameter to `StandardMoveValidator.__init__`, default to `StandardMoveGenerator()`, use injected instance in `validate()`

### 5. Layering Violation: Engine imports Network Layer
- **Files**: `engine/game_engine.py` imports from:
  - `network.event_bus` (acceptable - low-level utility)
  - `network.serialization` (`motion_to_dict`, `piece_to_dict`, `player_to_dict`, `position_to_dict`) - **VIOLATION**
- **Fix**: 
  - Move serialization logic to network layer (e.g., `network/server.py` or new `network/serializer.py`)
  - `EventPublisher` should publish domain objects directly (or simple dicts built without network imports)
  - Network layer subscribes to event bus and handles serialization

### 6. Duplicated Logic: Legal Destinations Computed in 3 Places
- **Places**: 
  1. `engine/game_runner.py` (line 77-78) - `tick()` 
  2. `rules/rule_engine.py` (line 22-23) - `validate()`
  3. `view/input_handler.py` (line 84) - `on_mouse()`
- **Fix**: Create shared helper - add `legal_destinations` static/class method to `StandardMoveGenerator` in `rules/piece_rules.py`, all three call sites use `StandardMoveGenerator.legal_destinations(board, piece)` instead of creating own instances

---

## Execution Order

1. **Delete `model/game_state.py`** (unused)
2. **Fix `rules/win_conditions.py`** - remove duplicate `WinResult`, import from interfaces
3. **Fix `rules/promotion.py`** - remove duplicate `PromotionResult`, import from interfaces
4. **Fix `engine/game_engine.py`**:
   - Line 156: use `self._promotion` instead of new instance
   - Remove `network.serialization` imports, replace with domain object publishing
5. **Fix `rules/rule_engine.py`** - inject `MoveGenerator` into `StandardMoveValidator`
6. **Fix `engine/game_runner.py`** - use `StandardMoveGenerator.legal_destinations()`
7. **Fix `view/input_handler.py`** - use `StandardMoveGenerator.legal_destinations()`
8. **Move serialization to network layer** - create `network/serializer.py` or add to `server.py`

---

## Test Validation

After each change, run:
```bash
python3 -m pytest tests/ integration/scripts/ -x -q
```

All 27 unit tests + 1 integration test should pass.