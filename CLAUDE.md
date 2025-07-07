# Claude Code Rules and Context

## System Information
- **Hardware**: Mac Studio with M2 Max processor
- **OS**: macOS (Apple Silicon)
- **Python**: Use `python3` command (not `python`)
- **Architecture**: ARM64/AArch64

## Project Context
- **Project**: AI Chat MP - Advanced AI chat application with intelligent query routing
- **Main Branch**: `master` (stable version with debug panel)
- **Current Branch**: `master` (clean, audio features reverted)
- **Features**: Intelligent routing, dual weather systems, debug panel for internal conversations, multi-provider support

## Development Guidelines
- Always use `python3` for Python execution on this Mac Studio
- This is an Apple Silicon Mac - be aware of architecture-specific considerations
- MongoDB is used for chat storage
- Multiple AI providers: Google Gemini, Anthropic Claude, Ollama

## Key Commands
- **Run app**: `streamlit run src/main.py`
- **Test**: `python3 -m pytest tests/`
- **Install deps**: `pip3 install -r requirements.txt`

## Development Workflow Commands

### WHEN USER SAYS "/BREAKPOINT" - DO THIS:
1. **Create MongoDB Backup**
   ```bash
   mongodump --db ai_chat_mp --out temp_backup
   mkdir -p mongo_backups
   rm -rf mongo_backups/mongo_sync
   mv temp_backup/ai_chat_mp mongo_backups/mongo_sync
   rm -rf temp_backup
   ```

2. **Update PROJECT_STATE.md** with current development status and recent changes

3. **Execute Git Workflow**
   ```bash
   git add .
   git commit -m "Development checkpoint: [analyze changes and create intelligent summary]"
   git push
   git gc --aggressive
   ```

### WHEN USER SAYS "/SYNC_CHAT" - DO THIS:
1. **Pull Latest Code**
   ```bash
   git pull origin master
   ```

2. **Restore MongoDB Backup**
   ```bash
   mongorestore --db ai_chat_mp --drop mongo_backups/mongo_sync/
   ```

3. **Verify Sync** - Check collections are restored and application connectivity

4. **Read Context Files**
   - Read CLAUDE.md for updated project context
   - Read PROJECT_STATE.md for current development status
   - Read README.md for project overview

### WHEN USER SAYS "/BRANCH [branch-name]" - DO THIS:
1. **Validate Branch Name**
   - If no branch name provided, prompt user for branch name
   - Verify branch name follows valid git naming conventions
   - Check that branch doesn't already exist

2. **Create and Switch to New Branch**
   ```bash
   git checkout -b [branch-name]
   git push -u origin [branch-name]
   ```

3. **Update PROJECT_STATE.md** with new branch status and development focus

4. **Confirmation** - Confirm branch creation and readiness for feature development

### WHEN USER SAYS "/PROMOTE [branch-name]" - DO THIS:
1. **Validate and Show Context**
   - If no branch name provided, use current branch as default
   - Show current branch and target branch for confirmation
   - Verify source branch exists: `git branch --list [branch-name]`
   - Show recent commits on branch for review

2. **Switch to Master and Update**
   ```bash
   git checkout master
   git pull origin master
   ```

3. **Merge Feature Branch**
   ```bash
   git merge [branch-name]
   git push origin master
   ```

4. **Clean Up Branch**
   ```bash
   git branch -d [branch-name]
   git push origin --delete [branch-name]
   ```

5. **Update PROJECT_STATE.md** - Document successful feature promotion

6. **Create MongoDB Backup** of new stable state

## Current Features
- **🧠 Intelligent Query Routing**: Confidence-based routing to tools, search, or model knowledge
- **🌡️ Dual Weather System**: OpenWeatherMap + WeatherFlow Tempest personal weather station
- **🐞 Debug Panel**: Shows internal agent conversations and routing decisions  
- **🔍 Advanced Search**: Brave + Serper with intelligent fallback
- **🤖 Multiple AI Providers**: Google Gemini, Anthropic Claude, Ollama, xAI Grok
- **👤 User Profile**: Personalization and context enhancement
- **⚡ Enhanced Debug Logging**: Question/response tracking with metrics

## File Structure
- `src/main.py` - Application entry point with debug logging
- `src/intelligent_router.py` - Confidence-based query routing
- `src/debug_panel.py` - Debug panel for internal conversations
- `src/providers.py` - AI provider management
- `src/tools.py` - Tool implementations (weather, search)
- `src/ui.py` - Streamlit interface
- `.streamlit/secrets.toml` - API keys configuration

## Development Best Practices
- When finished performing all of the actions in a chat_sync or a breakpoint provide the user with positive feedback the the tasks were accomplished correctly.