from typing import Callable, Dict, Union, Any
import re

from nicegui import background_tasks, helpers, ui

class RouterFrame(ui.element, component='router_frame.js'):
    pass

class Router:

    def __init__(self) -> None:
        self.routes: Dict[str, Callable] = {}
        self.route_patterns: Dict[str, Callable] = {}
        self.content: ui.element = None

    def add(self, path: str):
        def decorator(func: Callable):
            # For dynamic routes (containing {parameter})
            if '{' in path:
                # Convert route pattern to a regex that can match dynamic segments
                pattern = re.escape(path).replace(r'\{[^}]+\}', r'([^/]+)')
                self.route_patterns[pattern] = func
            else:
                # For static routes
                self.routes[path] = func
            return func
        return decorator

    def open(self, target: Union[Callable, str]) -> None:
        if isinstance(target, str):
            path = target
            
            # First, check for exact static route
            if path in self.routes:
                builder = self.routes[path]
            else:
                # If not a static route, check dynamic routes
                builder = None
                for pattern, route_func in self.route_patterns.items():
                    match = re.match(pattern, path)
                    if match:
                        # Extract the parameter value
                        param_value = match.group(1)
                        builder = lambda: route_func(param_value)
                        break
                
                if not builder:
                    raise KeyError(f"No route found for {path}")
        else:
            path = {v: k for k, v in self.routes.items()}[target]
            builder = target

        async def build() -> None:
            with self.content:
                ui.run_javascript(f'''
                    if (window.location.pathname !== "{path}") {{
                        history.pushState({{page: "{path}"}}, "", "{path}");
                    }}
                ''')
                result = builder()
                if helpers.is_coroutine_function(builder):
                    await result
        self.content.clear()
        background_tasks.create(build())

    def frame(self) -> ui.element:
        self.content = RouterFrame().on('open', lambda e: self.open(e.args))
        return self.content