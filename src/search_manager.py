"""Manages search operations with quality assessment and fallback logic."""

from typing import Dict, List, Optional, Tuple
import google.generativeai as genai
from logger import logger
from tools import tool_registry
import time

class SearchManager:
    def __init__(self, max_attempts: int = 5, quality_threshold: float = 7.0):
        self.max_attempts = max_attempts
        self.quality_threshold = quality_threshold
        self.search_engines = ["brave_search", "serper_search"]
    
    def assess_result_quality(self, query: str, result: str) -> float:
        """Rate search result quality from 0-10 based on relevance and completeness."""
        if not result or "no results" in result.lower():
            return 0.0
            
        prompt = f"""Rate the quality of this search result (0-10) for the query: "{query}"
        
        Consider:
        1. Relevance to the query (0-4 points)
        2. Completeness of information (0-3 points)
        3. Source credibility (0-3 points)
        
        Search Result:
        {result}
        
        Respond ONLY with a number between 0 and 10."""
        
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return float(response.text.strip())
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return 5.0  # Default to neutral on failure
    
    def search_with_fallback(self, query: str) -> Tuple[str, float, str]:
        """
        Perform search with quality assessment and fallback between engines.
        
        Returns:
            Tuple of (best_result, best_score, engine_used)
        """
        best_result = ""
        best_score = 0.0
        best_engine = ""
        attempts = 0
        
        while attempts < self.max_attempts and best_score < self.quality_threshold:
            # Alternate between search engines
            engine = self.search_engines[attempts % len(self.search_engines)]
            search_fn = tool_registry.get_callable(engine)
            
            if not search_fn:
                logger.error(f"Search engine not found: {engine}")
                attempts += 1
                continue
                
            try:
                # Add slight delay to avoid rate limiting
                if attempts > 0:
                    time.sleep(1)
                    
                logger.info(f"Trying {engine} (attempt {attempts + 1})")
                result = search_fn(query=query, num_results=3)
                score = self.assess_result_quality(query, result)
                
                if score > best_score:
                    best_score = score
                    best_result = result
                    best_engine = engine
                    
                logger.info(f"Search quality score: {score:.1f}/10")
                
                # Early exit if we find a good enough result
                if score >= self.quality_threshold:
                    break
                    
            except Exception as e:
                logger.error(f"Search with {engine} failed: {e}")
                
            attempts += 1
            
        return best_result, best_score, best_engine
