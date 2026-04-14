# 260414-nek2 Summary: CLI业务逻辑分离

## Objective

确保 CLI 层不包含业务逻辑（数据转换、格式化等），仅负责参数解析和输出格式化。

## Completed

### Task 1: Move _build_feed_meta to FeedMetaData class

**Changes:**
- Added `FeedMetaData.from_discovered_feed()` classmethod in `src/models.py`
- Replaced 3 call sites in `src/cli/feed.py` with the new classmethod
- Removed `_build_feed_meta` function from `src/cli/feed.py`

**verify:** `grep -n "_build_feed_meta" src/cli/` returns no results

### Task 2: Move _format_date to application layer

**Changes:**
- Added `format_published_date()` function in `src/application/config.py`
- Replaced all call sites in `src/cli/article.py` and `src/application/search.py`
- Removed duplicate `_format_date` and `_format_date_for_display` functions

**verify:** `grep -rn "_format_date" src/` shows no results in CLI layer

## Files Modified

| File | Change |
|------|--------|
| src/models.py | +13 lines: `FeedMetaData.from_discovered_feed()` classmethod |
| src/application/config.py | +22 lines: `format_published_date()` function |
| src/cli/feed.py | -12 lines: removed `_build_feed_meta`, use classmethod |
| src/cli/article.py | -18 lines: removed `_format_date`, use shared utility |
| src/application/search.py | -15 lines: removed duplicate formatting |

## Architecture

CLI 层不再包含业务逻辑：
- **数据转换** → `FeedMetaData.from_discovered_feed()` (models 层)
- **时间格式化** → `format_published_date()` (application/config 层)

CLI 只负责：参数解析 (click)、输出格式化 (Rich)、调用应用层函数

## Commit

`85a14c2` - refactor(cli): 移除业务逻辑，CLI仅负责解析参数和格式化输出
