# AI Chat MP - Development State

## Current Development Status
- **Date**: 2025-01-05
- **Session**: Post-power outage recovery & documentation update
- **Branch**: `master` (stable), `add-grok-provider` (development)
- **Status**: ✅ Major prompt architecture overhaul completed & documented

## 🚀 Recent Major Achievements

### Prompt Architecture Revolution
- **LLM-Powered Routing**: Replaced rule-based with intelligent AI routing decisions
- **Context Enhancement**: Automatic user personalization with location, weather, preferences
- **System Prompt V2**: 2000+ character comprehensive prompt with versioning
- **Query Optimization**: LLM-powered query enhancement for better tool matching

### Multi-Provider Expansion
- **5 AI Providers**: Google, Anthropic, OpenAI, xAI Grok, Ollama
- **Seamless Integration**: Provider-agnostic architecture with tool-aware prompting
- **Local Models**: Ollama integration with model caching and keep-alive

### Enhanced Intelligence
- **User Profiles**: Personal weather station (WeatherFlow 137684), location context
- **Search Quality**: LLM-based result scoring and provider selection
- **Debug Panel**: Real-time routing decisions and performance metrics

## 🎯 Current Focus Areas

### In Progress
- **Grok Integration**: xAI provider implementation on `add-grok-provider` branch
- **Documentation**: Unified development workflow with breakpoint system

### Next Priorities
1. Complete xAI Grok provider integration
2. Optimize LLM routing response times
3. Enhance search quality assessment
4. Refine user profile personalization

## 🏗️ Technical Architecture

### Core System Files
- `src/llm_intelligent_router.py` - LLM-powered routing with dual-layer fallback
- `src/prompt_enhancer.py` - Context-aware prompt enhancement
- `src/user_profile.py` - User personalization and context management
- `src/query_optimizer.py` - Query optimization engine
- `src/providers.py` - Multi-provider AI architecture
- `update_system_prompt.py` - System prompt management with versioning

### Database Schema
- **Prompts Collection**: System prompts with versioning
- **Users Collection**: User profiles and preferences  
- **Chats Collection**: References to prompts (not embedded text)
- **Models Collection**: Multi-provider model configurations

### Configuration
- **Default System Prompt**: Version 2.0 with comprehensive AI Chat MP context
- **Routing Model**: Gemini 2.5 Flash Lite for decision making
- **Enhancement Model**: Gemini 1.5 Flash for query optimization
- **Personal Weather Station**: WeatherFlow Station 137684 integration

## 🛠️ Development Environment

### Hardware & OS
- **System**: Mac Studio M2 Max (ARM64 architecture)
- **OS**: macOS
- **Python**: Use `python3` command (not `python`)
- **Database**: MongoDB on localhost:27017

### Commands
- **Launch**: `streamlit run src/main.py`
- **Test**: `python3 -m pytest tests/`
- **Install**: `pip3 install -r requirements.txt`

### Git Status
- **Main Branch**: `master` - Contains all prompt architecture updates
- **Development Branch**: `add-grok-provider` - Grok integration work
- **Repository**: Clean, timezone removal completed

## 📊 Provider Status

### Production Ready
- ✅ **Google Gemini**: 2.0/2.5 Flash, Pro models with vision/tools
- ✅ **Anthropic Claude**: 3.5 Haiku, Sonnet, Sonnet 4 with premium reasoning
- ✅ **OpenAI**: GPT-4o, GPT-4.1 variants with function calling
- ✅ **Ollama**: Local models (Llama 3.3, Mistral, etc.) with caching

### In Development
- 🔄 **xAI Grok**: Grok 2, Grok 2 Mini integration in progress

## 🧠 AI Context Preservation

### Session Memory Challenge
- **Problem**: No session persistence between Claude Code sessions
- **Solution**: Comprehensive handoff files and PROJECT_STATE.md
- **Workflow**: "Breakpoint" system for automated state preservation

### Key Context for AI
- **Developer**: Drew, 50+ years experience, pragmatic approach
- **Environment**: Mac Studio M2 Max, Windsurf IDE, Python/Streamlit/MongoDB
- **Preferences**: Clean copy/paste code, test early, working over perfect
- **Architecture**: Model-centric approach, company-named providers

## 🔄 Breakpoint Workflow

### Automated Process
When "breakpoint" is called:
1. Update PROJECT_STATE.md with current development state
2. `git add .`
3. `git commit -m "Development checkpoint: [intelligent summary]"`
4. `git push`
5. `git gc --aggressive` # keep repo compact

### Smart Commit Messages
- Analyze changes since last commit
- Generate meaningful summaries
- Track feature development progress

## 🎯 Known Issues & Technical Debt

### Current Limitations
1. **Session Memory**: No persistence between AI sessions (system limitation)
2. **CLI UX**: Backspace-only editing (outdated interface)
3. **Model Protection**: Hardcoded instead of config-driven
4. **Manual Model Entry**: Could benefit from templates

### Architectural Strengths
1. **Context-Aware**: All prompts enhanced with user-specific information
2. **LLM-Powered**: Intelligent routing using AI decision making
3. **Multi-Provider**: Seamless integration across 5 AI providers
4. **Privacy-First**: Granular control over personal information sharing
5. **Tool-Aware**: Context-sensitive tool usage instructions
6. **Fallback Ready**: Graceful degradation for all systems

## 📋 Development Notes

### Session Context
- **Power Outage**: Lost previous session, recovered via handoff files
- **Documentation**: User created handoff strategy to work around memory limitations
- **Competition**: xAI product launch mentioned as alternative
- **Frustrations**: CLI limitations, session memory issues

### Code Quality
- **Testing**: Always test when possible
- **Pragmatic**: Working code over elegant theory
- **Clean**: Remove debug code after testing
- **Copy/Paste**: Complete functions, not fragments

---

**Last Updated**: 2025-01-05 by Claude Code Session
**Status**: Ready for continued development with full context preservation

🚀 **AI Chat MP v2.0** - Comprehensive LLM-powered routing, context-aware prompts, multi-provider intelligence