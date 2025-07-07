# Project Todo List

## Current Task Plan
**Remove Timezone Implementation (Branch: undo_wired_timezone)**
Remove all timezone-related code and database changes that were added without notice. Return app to working state without timezone awareness.

## Todo Items
- [ ] Analyze current timezone implementation in codebase
- [ ] Identify all timezone-related code changes
- [ ] Find database schema changes (timezone field)
- [ ] Create removal plan for timezone code
- [ ] Remove timezone field from database documents
- [ ] Test app functionality after timezone removal

## Completed Items
- [x] Created Claude Code rules file structure

## Review Section

### Timezone Removal - COMPLETED ✅

**Mission Accomplished:**
- ✅ Removed all timezone-related code from `src/main.py`
- ✅ Cleaned `pytz` and `tzlocal` from requirements.txt  
- ✅ Removed `timezone` field from 9 chat documents (1 modified)
- ✅ Verified no timezone references remain in codebase
- ✅ Code syntax validation passed

**Changes Made:**
1. **Code cleanup** - Removed imports, timezone detection logic, `get_temporal_context()` function
2. **Database cleanup** - Removed timezone field from all chat documents
3. **Dependencies** - Removed timezone-related packages from requirements

**Result:** App returned to working state without any timezone awareness

---

### UI Independence Analysis Summary

**Architecture Assessment:**
The current Streamlit UI has moderate independence from the core business logic but significant coupling to Streamlit-specific components.

**Coupling Analysis:**
- **High Coupling**: 472 lines in ui.py heavily use `st.` components
- **Medium Coupling**: Session state management via `st.session_state`  
- **Low Coupling**: Backend logic (providers.py, main.py) well-separated

**Migration Feasibility:** Medium complexity
- Core chat functionality is UI-independent
- Database operations cleanly abstracted  
- UI components need complete rewrite
- Session management requires redesign

**Recommended Alternative: Gradio**
- Similar component-based architecture to Streamlit
- Built-in chat interface (`gr.ChatInterface`) 
- Better suited for AI/ML applications
- Simpler state management
- Easier migration path for forms and widgets

**Key Files Analyzed:**
- `src/ui.py` - Main UI components (533 lines)
- `src/main.py` - Application orchestration
- `src/providers.py` - Backend AI providers
- `src/config.py` - Configuration constants

**Migration Impact:**
- UI layer: Complete rewrite required
- Business logic: Minimal changes needed
- Database: No changes required
- Configuration: Minor updates needed