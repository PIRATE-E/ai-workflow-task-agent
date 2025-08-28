"""
Comprehensive test suite for the hierarchical agent workflow system.
Tests for AgentGraphCore, TASK models, and workflow execution.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    # Import the modules we need to test
    from src.agents.agentic_orchestrator.AgentGraphCore import (
        AgentGraphCore, 
        TASK, 
        REQUIRED_CONTEXT, 
        EXECUTION_CONTEXT, 
        FAILURE_CONTEXT, 
        subAgent_CONTEXT,
        MAIN_STATE,
        AgentState,
        Spawn_subAgent
    )
    from src.models.state import State
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    MODULES_AVAILABLE = False


class TestTaskModels(unittest.TestCase):
    """Test cases for the TASK and related Pydantic models."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")

    def test_task_creation_basic(self):
        """Test basic TASK model creation."""
        required_context = REQUIRED_CONTEXT(source_node="test_node")
        task = TASK(
            task_id=1,
            description="Test task description",
            tool_name="test_tool",
            required_context=required_context
        )
        
        self.assertEqual(task.task_id, 1)
        self.assertEqual(task.description, "Test task description")
        self.assertEqual(task.tool_name, "test_tool")
        self.assertEqual(task.status, "pending")  # Default status
        self.assertEqual(task.max_retries, 3)  # Default retries
        self.assertIsNone(task.execution_context)
        self.assertIsNone(task.failure_context)

    def test_task_creation_with_execution_context(self):
        """Test TASK creation with execution context."""
        required_context = REQUIRED_CONTEXT(source_node="test_node")
        execution_context = EXECUTION_CONTEXT(
            tool_name="test_tool",
            parameters={"param1": "value1"}
        )
        
        task = TASK(
            task_id=2,
            description="Test task with execution context",
            tool_name="test_tool",
            required_context=required_context,
            execution_context=execution_context
        )
        
        self.assertIsNotNone(task.execution_context)
        self.assertEqual(task.execution_context.tool_name, "test_tool")
        self.assertEqual(task.execution_context.parameters, {"param1": "value1"})

    def test_task_creation_with_failure_context(self):
        """Test TASK creation with failure context."""
        required_context = REQUIRED_CONTEXT(source_node="test_node")
        failure_context = FAILURE_CONTEXT(
            error_message="Test error",
            fail_count=2,
            error_type="TestError"
        )
        
        task = TASK(
            task_id=3,
            description="Test task with failure",
            tool_name="test_tool",
            required_context=required_context,
            failure_context=failure_context
        )
        
        self.assertIsNotNone(task.failure_context)
        self.assertEqual(task.failure_context.error_message, "Test error")
        self.assertEqual(task.failure_context.fail_count, 2)
        self.assertEqual(task.failure_context.error_type, "TestError")

    def test_recovery_actions_assignment(self):
        """Test that recovery_actions can be assigned as a dictionary."""
        required_context = REQUIRED_CONTEXT(source_node="test_node")
        failure_context = FAILURE_CONTEXT(
            error_message="Test error",
            fail_count=1,
            error_type="TestError"
        )
        
        # Test direct assignment of recovery actions as dict
        recovery_dict = {
            "require_spawn_new_agent": True,
            "updated_parameters": {"new_param": "new_value"},
            "alternative_tool": "alternative_tool_name"
        }
        
        failure_context.recovery_actions = recovery_dict
        
        self.assertEqual(failure_context.recovery_actions["require_spawn_new_agent"], True)
        self.assertEqual(failure_context.recovery_actions["updated_parameters"]["new_param"], "new_value")
        self.assertEqual(failure_context.recovery_actions["alternative_tool"], "alternative_tool_name")


class TestAgentState(unittest.TestCase):
    """Test cases for AgentState model."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")
        
        # Create a basic state object with required fields
        state = State(messages=[], message_type=None)
        main_state = MAIN_STATE(state=state)
        
        # Create a simple task
        required_context = REQUIRED_CONTEXT(source_node="test_node")
        task = TASK(
            task_id=1,
            description="Test task",
            tool_name="test_tool",
            required_context=required_context
        )
        
        # Create agent state
        agent_state = AgentState(
            TASKS=[task],
            MAIN_STATE=main_state,
            CURRENT_TASK_ID=1,
            original_goal="Test goal"
        )
        
        self.assertEqual(len(agent_state.TASKS), 1)
        self.assertEqual(agent_state.CURRENT_TASK_ID, 1)
        self.assertEqual(agent_state.original_goal, "Test goal")
        self.assertEqual(agent_state.MAIN_STATE.WORKFLOW_STATUS, "STARTED")


class TestAgentGraphCoreHelpers(unittest.TestCase):
    """Test cases for AgentGraphCore helper methods."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")

    @patch('src.agents.agentic_orchestrator.AgentGraphCore.ToolAssign')
    def test_get_safe_tools_list_success(self, mock_tool_assign):
        """Test __get_safe_tools_list when tools are available."""
        # Mock tools
        mock_tool1 = Mock()
        mock_tool1.name = "test_tool_1"
        mock_tool2 = Mock()
        mock_tool2.name = "test_tool_2"
        
        mock_tool_assign.get_tools_list.return_value = [mock_tool1, mock_tool2]
        
        tools = AgentGraphCore._AgentGraphCore__get_safe_tools_list()
        
        self.assertEqual(len(tools), 2)
        self.assertEqual(tools[0].name, "test_tool_1")
        self.assertEqual(tools[1].name, "test_tool_2")

    @patch('src.agents.agentic_orchestrator.AgentGraphCore.ToolAssign')
    def test_get_safe_tools_list_empty(self, mock_tool_assign):
        """Test __get_safe_tools_list when no tools are available."""
        mock_tool_assign.get_tools_list.return_value = []
        
        with self.assertRaises(RuntimeError) as context:
            AgentGraphCore._AgentGraphCore__get_safe_tools_list()
        
        self.assertIn("No tools available", str(context.exception))

    @patch('src.agents.agentic_orchestrator.AgentGraphCore.ToolAssign')
    def test_get_tools_string(self, mock_tool_assign):
        """Test __get_tools_string formatting."""
        # Mock tools with descriptions
        mock_tool1 = Mock()
        mock_tool1.name = "test_tool_1"
        mock_tool1.description = "Test tool 1 description"
        
        # Create a mock without description attribute
        mock_tool2 = Mock(spec=['name'])  # Only specify name as an available attribute
        mock_tool2.name = "test_tool_2"
        
        mock_tool_assign.get_tools_list.return_value = [mock_tool1, mock_tool2]
        
        tools_string = AgentGraphCore._AgentGraphCore__get_tools_string()
        
        self.assertIn("test_tool_1: Test tool 1 description", tools_string)
        self.assertIn("test_tool_2: No description", tools_string)


class TestToolExecutor(unittest.TestCase):
    """Test cases for the tool executor method."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")

    @patch('src.agents.agentic_orchestrator.AgentGraphCore.AgentGraphCore._AgentGraphCore__get_safe_tools_list')
    @patch('src.tools.lggraph_tools.tool_response_manager.ToolResponseManager')
    def test_tool_executor_success(self, mock_response_manager, mock_get_tools):
        """Test successful tool execution."""
        # Mock tool
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_get_tools.return_value = [mock_tool]
        
        # Mock response
        mock_response = Mock()
        mock_response.content = "Tool executed successfully"
        mock_response_manager_instance = Mock()
        mock_response_manager_instance.get_response.return_value = [mock_response]
        mock_response_manager.return_value = mock_response_manager_instance
        
        success, result = AgentGraphCore._AgentGraphCore__tool_executor(
            "test_tool", 
            {"param1": "value1"}
        )
        
        self.assertTrue(success)
        self.assertEqual(result, "Tool executed successfully")

    @patch('src.agents.agentic_orchestrator.AgentGraphCore.AgentGraphCore._AgentGraphCore__get_safe_tools_list')
    def test_tool_executor_tool_not_found(self, mock_get_tools):
        """Test tool executor when tool is not found."""
        mock_tool = Mock()
        mock_tool.name = "different_tool"
        mock_get_tools.return_value = [mock_tool]
        
        success, result = AgentGraphCore._AgentGraphCore__tool_executor(
            "nonexistent_tool", 
            {"param1": "value1"}
        )
        
        self.assertFalse(success)
        self.assertIn("not a valid or registered tool", result)

    @patch('src.agents.agentic_orchestrator.AgentGraphCore.AgentGraphCore._AgentGraphCore__get_safe_tools_list')
    @patch('src.tools.lggraph_tools.tool_response_manager.ToolResponseManager')
    def test_tool_executor_no_response(self, mock_response_manager, mock_get_tools):
        """Test tool executor when no response is received."""
        # Mock tool
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_get_tools.return_value = [mock_tool]
        
        # Mock empty response
        mock_response_manager_instance = Mock()
        mock_response_manager_instance.get_response.return_value = []
        mock_response_manager.return_value = mock_response_manager_instance
        
        success, result = AgentGraphCore._AgentGraphCore__tool_executor(
            "test_tool", 
            {"param1": "value1"}
        )
        
        self.assertFalse(success)
        self.assertIn("No response received", result)


class TestSpawnSubAgent(unittest.TestCase):
    """Test cases for the Spawn_subAgent class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")
        
        # Create a sample parent task
        self.required_context = REQUIRED_CONTEXT(source_node="test_node")
        self.parent_task = TASK(
            task_id=1,
            description="Complex task requiring decomposition",
            tool_name="complex_tool",
            required_context=self.required_context
        )
        
        # Create a sample state with required fields
        state = State(messages=[], message_type=None)
        main_state = MAIN_STATE(state=state)
        self.agent_state = AgentState(
            TASKS=[self.parent_task],
            MAIN_STATE=main_state,
            CURRENT_TASK_ID=1,
            original_goal="Test goal"
        )

    @patch('src.agents.agentic_orchestrator.AgentGraphCore.ModelManager')
    def test_analyze_spawn_requirement_should_spawn(self, mock_model_manager):
        """Test spawn requirement analysis that recommends spawning."""
        # Mock LLM response indicating spawning is needed
        mock_response = Mock()
        mock_response.content = '{"should_spawn": true, "reasoning": "Task is complex"}'
        
        mock_model_instance = Mock()
        mock_model_instance.invoke.return_value = mock_response
        mock_model_manager.return_value = mock_model_instance
        
        # Mock JSON conversion
        with patch('src.agents.agentic_orchestrator.AgentGraphCore.ModelManager.convert_to_json') as mock_convert:
            mock_convert.return_value = {
                "should_spawn": True,
                "reasoning": "Task is complex"
            }
            
            result = Spawn_subAgent.analyze_spawn_requirement(
                self.parent_task, 
                "complexity analysis", 
                self.agent_state
            )
            
            self.assertTrue(result["should_spawn"])
            self.assertEqual(result["reasoning"], "Task is complex")

    @patch('src.agents.agentic_orchestrator.AgentGraphCore.ModelManager')
    def test_analyze_spawn_requirement_no_spawn(self, mock_model_manager):
        """Test spawn requirement analysis that doesn't recommend spawning."""
        # Mock LLM response indicating no spawning needed
        mock_response = Mock()
        mock_response.content = '{"should_spawn": false, "reasoning": "Task is simple"}'
        
        mock_model_instance = Mock()
        mock_model_instance.invoke.return_value = mock_response
        mock_model_manager.return_value = mock_model_instance
        
        # Mock JSON conversion
        with patch('src.agents.agentic_orchestrator.AgentGraphCore.ModelManager.convert_to_json') as mock_convert:
            mock_convert.return_value = {
                "should_spawn": False,
                "reasoning": "Task is simple"
            }
            
            result = Spawn_subAgent.analyze_spawn_requirement(
                self.parent_task, 
                "complexity analysis", 
                self.agent_state
            )
            
            self.assertFalse(result["should_spawn"])
            self.assertEqual(result["reasoning"], "Task is simple")

    @patch('src.agents.agentic_orchestrator.AgentGraphCore.AgentGraphCore._AgentGraphCore__get_safe_tools_list')
    @patch('src.agents.agentic_orchestrator.AgentGraphCore.ModelManager')
    def test_decompose_task_for_subAgent(self, mock_model_manager, mock_get_tools):
        """Test task decomposition into sub-tasks."""
        # Mock available tools
        mock_tool1 = Mock()
        mock_tool1.name = "subtool_1"
        mock_tool2 = Mock()
        mock_tool2.name = "subtool_2"
        mock_get_tools.return_value = [mock_tool1, mock_tool2]
        
        # Mock LLM response with decomposed tasks
        mock_response = Mock()
        mock_response.content = '[{"description": "Subtask 1", "tool_name": "subtool_1"}, {"description": "Subtask 2", "tool_name": "subtool_2"}]'
        
        mock_model_instance = Mock()
        mock_model_instance.invoke.return_value = mock_response
        mock_model_manager.return_value = mock_model_instance
        
        # Mock JSON conversion
        with patch('src.agents.agentic_orchestrator.AgentGraphCore.ModelManager.convert_to_json') as mock_convert:
            mock_convert.return_value = [
                {"description": "Subtask 1", "tool_name": "subtool_1"},
                {"description": "Subtask 2", "tool_name": "subtool_2"}
            ]
            
            subtasks = Spawn_subAgent.decompose_task_for_subAgent(
                self.parent_task, 
                self.agent_state
            )
            
            self.assertEqual(len(subtasks), 2)
            self.assertEqual(subtasks[0].description, "Subtask 1")
            self.assertEqual(subtasks[0].tool_name, "subtool_1")
            self.assertEqual(subtasks[0].task_id, 1.1)  # Parent ID 1 + sub-index 1
            self.assertEqual(subtasks[1].description, "Subtask 2")
            self.assertEqual(subtasks[1].tool_name, "subtool_2")
            self.assertEqual(subtasks[1].task_id, 1.2)  # Parent ID 1 + sub-index 2

    def test_inject_subAgent_into_workflow(self):
        """Test injection of sub-tasks into workflow."""
        # Create subtasks
        subtask1 = TASK(
            task_id=1.1,
            description="Subtask 1",
            tool_name="subtool_1",
            required_context=REQUIRED_CONTEXT(source_node="decomposer")
        )
        subtask2 = TASK(
            task_id=1.2,
            description="Subtask 2",
            tool_name="subtool_2",
            required_context=REQUIRED_CONTEXT(source_node="decomposer")
        )
        
        # Mock the state's TASKS list to make the parent task findable
        self.agent_state.TASKS = [self.parent_task]
        
        result = Spawn_subAgent.inject_subAgent_into_workflow(
            self.parent_task, 
            [subtask1, subtask2], 
            self.agent_state
        )
        
        # Check that parent task status is updated
        self.assertEqual(self.parent_task.status, "in_progress")
        self.assertIsNotNone(self.parent_task.execution_context)
        self.assertIn("2 sub-tasks", self.parent_task.execution_context.analysis)
        
        # Check that subtasks are injected correctly
        updated_tasks = result["tasks"]
        self.assertEqual(len(updated_tasks), 3)  # Parent + 2 subtasks
        self.assertEqual(updated_tasks[0], self.parent_task)  # Parent first
        self.assertEqual(updated_tasks[1], subtask1)  # Then subtasks
        self.assertEqual(updated_tasks[2], subtask2)


class TestWorkflowIntegration(unittest.TestCase):
    """Integration tests for the complete workflow."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")

    def test_graph_building(self):
        """Test that the LangGraph can be built successfully."""
        try:
            graph = AgentGraphCore.build_graph()
            self.assertIsNotNone(graph)
            # Graph should be compiled and ready to use
        except Exception as e:
            self.fail(f"Graph building failed: {e}")

    @patch('src.agents.agentic_orchestrator.AgentGraphCore.ModelManager')
    def test_initial_planner_basic_execution(self, mock_model_manager):
        """Test basic execution of the initial planner node."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = '[{"task_id": 1, "description": "Test task", "tool_name": "test_tool"}]'
        
        mock_model_instance = Mock()
        mock_model_instance.invoke.return_value = mock_response
        mock_model_manager.return_value = mock_model_instance
        
        # Mock JSON conversion
        with patch('src.agents.agentic_orchestrator.AgentGraphCore.ModelManager.convert_to_json') as mock_convert:
            mock_convert.return_value = [
                {"task_id": 1, "description": "Test task", "tool_name": "test_tool"}
            ]
            
            # Create initial state with required fields
            state = State(messages=[], message_type=None)
            main_state = MAIN_STATE(state=state)
            agent_state = AgentState(
                TASKS=[],
                MAIN_STATE=main_state,
                CURRENT_TASK_ID=0,
                original_goal="Test goal"
            )
            
            # Convert to dict for node execution
            state_dict = {
                'original_goal': 'Test goal',
                'executed_nodes': []
            }
            
            result = AgentGraphCore._AgentGraphCore__subAGENT_initial_planner(state_dict)
            
            self.assertIn('tasks', result)
            self.assertIn('current_task_id', result)
            self.assertIn('workflow_status', result)
            self.assertEqual(result['workflow_status'], 'RUNNING')
            self.assertEqual(len(result['tasks']), 1)
            self.assertEqual(result['tasks'][0].description, "Test task")