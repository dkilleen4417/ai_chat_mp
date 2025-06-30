"""Module for optimizing search queries using LLM."""

from typing import Optional
import google.generativeai as genai
from logger import logger


def optimize_search_query(query: str, model_name: str = "gemini-1.5-flash") -> str:
    """Enhance a search query using an LLM for better search results.
    
    Args:
        query: The original user query
        model_name: Name of the Gemini model to use for optimization
        
    Returns:
        Optimized search query string
    """
    current_year = 2025  # Could be made dynamic
    
    prompt = f"""You are an expert search query optimizer. Your task is to transform the user's search query into the most effective version for web search engines.

## Instructions:
1. **Clarify Intent**: Add context to make the search intent clear
2. **Add Time Context**: For time-sensitive queries, include '{current_year}' if not specified
3. **Enhance Specificity**: Add relevant qualifiers that would help find authoritative sources
4. **Remove Ambiguity**: Disambiguate terms that might have multiple meanings
5. **Optimize Length**: Keep between 5-12 words for best results
6. **Preserve Original Meaning**: Never change the core intent of the query

## Examples:
Input: "best programming language"
Output: "most popular programming languages {current_year} developer survey"

Input: "python tutorial"
Output: "best python programming tutorial for beginners {current_year}"

Input: "how to fix my code"
Output: "debugging techniques for python code errors"

## Input Query:
{query}

## Optimized Query:"""
    
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 100,
            }
        )
        optimized = response.text.strip()
        # Fallback to original if empty or too short
        return optimized if optimized and len(optimized) > 5 else query
    except Exception as e:
        logger.error(f"Query optimization failed: {e}")
        return query
