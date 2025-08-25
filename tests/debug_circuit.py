#!/usr/bin/env python3
from src.utils.open_ai_integration import OpenAIIntegration

# Reset state
OpenAIIntegration._failure_count = 0
OpenAIIntegration._circuit_open = False
OpenAIIntegration._circuit_open_until = None

integration = OpenAIIntegration()

print(
    f"Initial state: count={OpenAIIntegration._failure_count}, open={OpenAIIntegration._circuit_open}"
)

# Simulate failures
for i in range(6):
    integration._record_failure()
    print(
        f"After failure {i + 1}: count={OpenAIIntegration._failure_count}, open={OpenAIIntegration._circuit_open}"
    )

print(f"\nFinal: max_failures={OpenAIIntegration._max_failures}")
