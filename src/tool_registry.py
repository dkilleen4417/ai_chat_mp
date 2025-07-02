"""Enhanced ToolRegistry with support for custom parameter schemas."""

from typing import Any, Callable, Dict, List, Optional


class ToolRegistry:
    """Stores callable tools and produces JSON schemas for models.
    
    This enhanced version supports custom parameter schemas for each tool.
    """

    def __init__(self) -> None:
        self._fns: Dict[str, Callable[..., str]] = {}
        self._descriptions: Dict[str, str] = {}
        self._param_schemas: Dict[str, Dict[str, Any]] = {}

    def register_tool(
        self, 
        fn: Callable[..., str], 
        name: str, 
        description: str, 
        params_schema: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a tool with an optional custom parameter schema.
        
        Args:
            fn: The callable function to register
            name: Name of the tool (must be unique)
            description: Description of what the tool does
            params_schema: Optional custom parameter schema. If not provided,
                         defaults to a simple 'query' parameter.
        """
        self._fns[name] = fn
        self._descriptions[name] = description
        if params_schema is not None:
            self._param_schemas[name] = params_schema

    def get_callable(self, name: str) -> Optional[Callable[..., str]]:
        """Get a callable tool by name."""
        return self._fns.get(name)

    def list_tool_configs(self) -> List[Dict[str, Any]]:
        """Return JSON-schema tool definitions compatible with Gemini."""
        defs: List[Dict[str, Any]] = []
        
        for name, desc in self._descriptions.items():
            # Use custom parameter schema if available, otherwise use default
            if name in self._param_schemas:
                params = self._param_schemas[name]
            else:
                # Default parameter schema for backward compatibility
                params = {
                    "type": "OBJECT",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to run",
                        }
                    },
                    "required": ["query"],
                }
            
            defs.append({
                "name": name,
                "description": desc,
                "parameters": params
            })
        
        # Gemini expects each tool wrapper with "function_declarations"
        return [{"function_declarations": [d]} for d in defs]
