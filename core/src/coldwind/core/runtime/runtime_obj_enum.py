"""
NOTE:- this module provide enums for the core only runtimes objects to access,
using the dynamic service of the context registry
"""

from enum import Enum


class CoreRunTimeObjects(Enum):
    """
    Enum for core runtime objects that can be dynamically registered and accessed.
    This allows for type-safe retrieval of services from the runtime context.
    """

    # Langchain message classes bundle (HumanMessage, AIMessage, BaseMessage).
    # The member name intentionally does NOT leak the tuple cardinality — the bundle
    # may grow (e.g. ToolMessage) without forcing a rename of every call site.
    # Value convention: SCREAMING_SNAKE_CASE string mirroring the member name.
    message_classes = "MESSAGE_CLASSES"
    neo4j_driver = "NEO4J_DRIVER"
