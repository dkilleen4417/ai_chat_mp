"""
Context Relevance Analyzer
Determines if a user question requires full chat history or can be answered independently
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import streamlit as st
from logger import logger

# Session state alias for consistency
ss = st.session_state

class ContextRelevanceAnalyzer:
    """Analyzes if current question needs full chat context or can be answered standalone"""
    
    def __init__(self):
        self.standalone_patterns = [
            # Weather queries
            r'\b(weather|temperature|temp|forecast|rain|snow|humidity|wind)\b',
            # Time/date queries
            r'\b(time|date|today|tomorrow|yesterday|now|current)\b',
            # Math/calculation queries
            r'\b(calculate|compute|solve|math|equation|\+|\-|\*|\/|\=)\b',
            # Factual/definition queries
            r'\b(what is|who is|define|explain|meaning|definition)\b',
            # General information queries
            r'\b(how to|how do|tell me|show me|find|search)\b',
            # Standalone commands
            r'\b(convert|translate|summarize|list|create|generate)\b'
        ]
        
        self.context_dependent_patterns = [
            # References to previous messages
            r'\b(that|this|it|they|them|earlier|before|previous|above|mentioned)\b',
            # Continuation words
            r'\b(also|additionally|furthermore|moreover|and|but|however|though)\b',
            # Comparative references
            r'\b(compared to|versus|vs|different from|similar to|like that)\b',
            # Question continuations
            r'\b(more about|details about|expand on|continue|follow up)\b'
        ]
    
    def analyze_context_relevance(self, current_question: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """
        Analyze if current question needs full chat context
        
        Args:
            current_question: The user's current question
            chat_history: List of previous messages
            
        Returns:
            Analysis result with recommendation
        """
        try:
            # Use LLM-based analysis for more accurate results
            if hasattr(ss, 'decision_model') and ss.decision_model:
                result = self._llm_analyze_context(current_question, chat_history)
            else:
                # Fallback to pattern-based analysis
                result = self._pattern_analyze_context(current_question, chat_history)
            
            # Check if we should suggest a new chat
            result.update(self._analyze_new_chat_suggestion(current_question, chat_history, result))
            
            return result
                
        except Exception as e:
            logger.error(f"Context analysis failed: {e}")
            # Safe fallback - include context to avoid breaking conversations
            return {
                "needs_full_context": True,
                "confidence": 0.5,
                "reasoning": "Analysis failed - using full context for safety",
                "context_window": len(chat_history),
                "analysis_method": "fallback",
                "suggest_new_chat": False,
                "new_chat_reasoning": ""
            }
    
    def _llm_analyze_context(self, current_question: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """Use LLM to analyze context relevance"""
        try:
            # Get recent context (last 5 messages) for analysis
            recent_context = chat_history[-10:] if len(chat_history) > 10 else chat_history
            
            # Build context summary
            context_summary = self._build_context_summary(recent_context)
            
            analysis_prompt = f"""You are a context relevance analyzer. Analyze if the current user question requires the full chat conversation history to answer correctly, or if it can be answered independently.

CURRENT QUESTION: "{current_question}"

RECENT CHAT CONTEXT (last few messages):
{context_summary}

Analyze this question and respond with a JSON object containing:
- "needs_full_context": true/false
- "confidence": 0.0-1.0 (how confident you are)
- "reasoning": brief explanation
- "question_type": "standalone" or "context_dependent"

STANDALONE questions (don't need chat history):
- Factual questions (weather, time, definitions)
- Calculations and conversions
- General information requests
- New topic introductions

CONTEXT-DEPENDENT questions (need chat history):
- References to "it", "that", "this", "they"
- Continuation of previous topics
- Comparative questions
- Follow-up questions

Respond with ONLY the JSON object, no other text."""

            messages = [{"role": "user", "parts": [analysis_prompt]}]
            
            response = ss.decision_model.generate_content(contents=messages)
            
            # Parse JSON response
            import json
            result = json.loads(response.text.strip())
            
            # Add metadata
            result["context_window"] = len(chat_history)
            result["analysis_method"] = "llm"
            
            logger.info(f"LLM context analysis: {result}")
            return result
            
        except Exception as e:
            logger.error(f"LLM context analysis failed: {e}")
            return self._pattern_analyze_context(current_question, chat_history)
    
    def _pattern_analyze_context(self, current_question: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """Fallback pattern-based analysis"""
        import re
        
        question_lower = current_question.lower()
        
        # Check for standalone patterns
        standalone_score = 0
        for pattern in self.standalone_patterns:
            if re.search(pattern, question_lower):
                standalone_score += 1
        
        # Check for context-dependent patterns
        context_score = 0
        for pattern in self.context_dependent_patterns:
            if re.search(pattern, question_lower):
                context_score += 1
        
        # Determine result
        if standalone_score > context_score:
            needs_context = False
            confidence = min(0.8, standalone_score / (standalone_score + context_score + 1))
            reasoning = f"Standalone patterns detected: {standalone_score}, context patterns: {context_score}"
        elif context_score > standalone_score:
            needs_context = True
            confidence = min(0.8, context_score / (standalone_score + context_score + 1))
            reasoning = f"Context-dependent patterns detected: {context_score}, standalone patterns: {standalone_score}"
        else:
            # Tie or no clear patterns - default to including context
            needs_context = True
            confidence = 0.5
            reasoning = "No clear patterns detected - using context for safety"
        
        return {
            "needs_full_context": needs_context,
            "confidence": confidence,
            "reasoning": reasoning,
            "question_type": "context_dependent" if needs_context else "standalone",
            "context_window": len(chat_history),
            "analysis_method": "pattern"
        }
    
    def _build_context_summary(self, recent_messages: List[Dict]) -> str:
        """Build a summary of recent chat context"""
        if not recent_messages:
            return "No recent context"
        
        summary_lines = []
        for msg in recent_messages[-5:]:  # Last 5 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                # Truncate long messages
                truncated = content[:100] + "..." if len(content) > 100 else content
                summary_lines.append(f"{role.upper()}: {truncated}")
        
        return "\n".join(summary_lines) if summary_lines else "No meaningful context"
    
    def get_optimal_context_window(self, analysis_result: Dict[str, Any], full_history: List[Dict]) -> List[Dict]:
        """Get optimal context window based on analysis with topic establishment awareness"""
        
        if not full_history:
            return []
        
        current_question = full_history[-1]
        conversation_history = full_history[:-1]
        
        # Check topic establishment
        topic_info = self.detect_topic_establishment(conversation_history)
        
        # Calculate relevance score for current question
        relevance_score = self.calculate_conversation_relevance(
            current_question.get("content", ""), 
            conversation_history
        )
        
        # Add debug logging
        from debug_utils import add_debug_log
        add_debug_log(f"🎯 Topic Established: {topic_info['topic_established']}")
        if topic_info["topic_established"]:
            add_debug_log(f"📋 Main Topic: {topic_info.get('main_topic', 'Unknown')}")
        add_debug_log(f"📊 Question Relevance: {relevance_score:.2f}")
        
        # Decision logic based on topic establishment and relevance
        if not topic_info["topic_established"]:
            # No established topic - everything is exploratory, use standalone context
            add_debug_log("🔍 No topic established - using standalone context")
            return [current_question]
        
        elif relevance_score < 0.3:
            # Low relevance to established topic - treat as interruption
            add_debug_log("⚡ Low relevance interruption - using standalone context")
            return [current_question]
        
        else:
            # High relevance to established topic - use contextual response
            confidence = analysis_result.get("confidence", 0.5)
            
            if confidence > 0.8:
                # High confidence - use recent relevant context
                relevant_messages = self._filter_by_relevance(conversation_history[-8:], 0.3)
                context_window = relevant_messages + [current_question]
                add_debug_log(f"🎯 High confidence context - {len(context_window)} messages")
                return context_window
            
            elif confidence > 0.6:
                # Medium confidence - broader relevant context
                relevant_messages = self._filter_by_relevance(conversation_history[-12:], 0.2)
                context_window = relevant_messages + [current_question]
                add_debug_log(f"🎯 Medium confidence context - {len(context_window)} messages")
                return context_window
            
            else:
                # Low confidence - use more context for safety
                add_debug_log(f"🎯 Low confidence - using full context ({len(full_history)} messages)")
                return full_history
    
    def _filter_by_relevance(self, messages: List[Dict], threshold: float) -> List[Dict]:
        """Filter messages by relevance score threshold"""
        filtered = []
        for msg in messages:
            relevance = msg.get("relevance_score", 1.0)  # Default to relevant if no score
            if relevance >= threshold:
                filtered.append(msg)
        return filtered

    def detect_topic_establishment(self, messages: List[Dict]) -> Dict[str, Any]:
        """Detect if a conversational topic has been established using LLM analysis"""
        
        if len(messages) < 4:
            return {
                "topic_established": False, 
                "main_topic": None,
                "confidence": 0.0,
                "reasoning": "Insufficient messages for topic establishment"
            }
        
        # Get recent conversation for analysis
        recent_messages = messages[-8:] if len(messages) > 8 else messages
        
        # Build conversation text for analysis
        conversation_lines = []
        for msg in recent_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if content.strip():
                conversation_lines.append(f"{role.upper()}: {content}")
        
        conversation_text = "\n".join(conversation_lines)
        
        try:
            if hasattr(ss, 'decision_model') and ss.decision_model:
                topic_prompt = f"""Analyze this conversation to determine if a main conversational topic has been established.

CONVERSATION:
{conversation_text}

A topic is "established" when there are multiple exchanges about the same subject showing sustained discussion, not just single Q&A pairs or rapid topic switching.

Respond with ONLY a JSON object:
{{
    "topic_established": true/false,
    "main_topic": "brief description or null",
    "confidence": 0.0-1.0
}}"""

                response = ss.decision_model.generate_content(topic_prompt)
                
                # Parse JSON response
                import json
                result = json.loads(response.text.strip())
                
                # Add reasoning for debugging
                result["reasoning"] = f"LLM analysis based on {len(recent_messages)} recent messages"
                
                logger.info(f"Topic establishment analysis: {result}")
                return result
                
        except Exception as e:
            logger.error(f"Topic establishment analysis failed: {e}")
        
        # Fallback to simple heuristic
        return {
            "topic_established": len(messages) > 6,
            "main_topic": "Extended conversation" if len(messages) > 6 else None,
            "confidence": 0.5,
            "reasoning": "Fallback heuristic - topic assumed established after 6+ messages"
        }
    
    def calculate_conversation_relevance(self, current_question: str, chat_history: List[Dict]) -> float:
        """Calculate how relevant current question is to ongoing conversation (0.0-1.0)"""
        
        if len(chat_history) < 3:
            return 1.0  # Short conversations, everything is relevant
        
        # First check if topic is established
        topic_info = self.detect_topic_establishment(chat_history)
        
        if not topic_info["topic_established"]:
            # No established topic - treat as exploratory conversation
            return 1.0
        
        # Topic is established - assess relevance to main topic
        main_topic = topic_info.get("main_topic", "the ongoing conversation")
        recent_context = chat_history[-6:]  # Recent conversation context
        context_text = " ".join([msg.get("content", "") for msg in recent_context])
        
        try:
            if hasattr(ss, 'decision_model') and ss.decision_model:
                relevance_prompt = f"""Rate how relevant this new question is to the established conversation topic.

ESTABLISHED TOPIC: {main_topic}

RECENT CONVERSATION CONTEXT:
{context_text[:400]}

NEW QUESTION: {current_question}

Respond with ONLY a number between 0.0 and 1.0:
- 1.0 = Directly continues the established topic
- 0.5 = Somewhat related to the topic  
- 0.0 = Complete topic change/interruption (like asking about weather during coding discussion)"""

                response = ss.decision_model.generate_content(relevance_prompt)
                score = float(response.text.strip())
                return max(0.0, min(1.0, score))  # Clamp to 0.0-1.0
                
        except Exception as e:
            logger.warning(f"Relevance calculation failed: {e}")
        
        # Fallback: Use existing standalone detection
        analysis = self._pattern_analyze_context(current_question, chat_history)
        return 0.2 if analysis["question_type"] == "standalone" else 0.8

    def _analyze_new_chat_suggestion(self, current_question: str, chat_history: List[Dict], analysis_result: Dict) -> Dict[str, Any]:
        """
        Analyze if we should suggest starting a new chat
        
        Args:
            current_question: Current user question
            chat_history: Full chat history
            analysis_result: Result from context analysis
            
        Returns:
            Dictionary with suggestion info
        """
        # Don't suggest for very short conversations
        if len(chat_history) < 4:
            return {
                "suggest_new_chat": False,
                "new_chat_reasoning": ""
            }
        
        # Only suggest for standalone questions
        if analysis_result.get("needs_full_context", True):
            return {
                "suggest_new_chat": False,
                "new_chat_reasoning": ""
            }
        
        # Check if there's been an active conversation about a different topic
        recent_messages = chat_history[-6:] if len(chat_history) > 6 else chat_history
        
        # Look for ongoing conversation indicators
        conversation_indicators = [
            "that", "this", "it", "they", "also", "furthermore", "however",
            "what about", "tell me more", "expand on", "continue", "additionally"
        ]
        
        # Check if recent messages show an ongoing conversation
        ongoing_conversation = False
        topic_keywords = []
        
        for msg in recent_messages[:-1]:  # Exclude current question
            content = msg.get("content", "").lower()
            
            # Check for conversation indicators
            if any(indicator in content for indicator in conversation_indicators):
                ongoing_conversation = True
            
            # Extract potential topic keywords (simple approach)
            words = content.split()
            topic_keywords.extend([word for word in words if len(word) > 4 and word.isalpha()])
        
        # If there's an ongoing conversation and current question is standalone
        if ongoing_conversation and analysis_result.get("confidence", 0) > 0.6:
            # Check if current question is about a different topic
            current_words = current_question.lower().split()
            topic_overlap = any(word in current_words for word in topic_keywords[-10:])  # Recent topics
            
            if not topic_overlap:
                # High confidence standalone question with no topic overlap
                return {
                    "suggest_new_chat": True,
                    "new_chat_reasoning": f"This {analysis_result.get('question_type', 'standalone')} question seems unrelated to the ongoing conversation about {', '.join(topic_keywords[-3:]) if topic_keywords else 'previous topics'}"
                }
        
        # Special case: Check for common standalone question types that interrupt conversations
        standalone_interruption_patterns = [
            r'\b(weather|temperature|time|date|calculate|math|convert|translate)\b',
            r'\b(what is|who is|define|explain|meaning)\b',
            r'\b(how to|how do|show me|tell me how)\b'
        ]
        
        import re
        if any(re.search(pattern, current_question.lower()) for pattern in standalone_interruption_patterns):
            if len(chat_history) > 8 and analysis_result.get("confidence", 0) > 0.7:
                return {
                    "suggest_new_chat": True,
                    "new_chat_reasoning": f"This appears to be a {analysis_result.get('question_type', 'standalone')} question that doesn't relate to your current conversation"
                }
        
        return {
            "suggest_new_chat": False,
            "new_chat_reasoning": ""
        }

# Global instance
context_analyzer = ContextRelevanceAnalyzer()