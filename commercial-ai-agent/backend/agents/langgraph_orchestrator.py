import copy
import json
import logging
import uuid
import sqlite3
from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, START, END

from backend.agents.prompt_engineer import PromptEngineerAgent
from backend.agents.planner import PlannerAgent
from backend.agents.response_agent import ResponseAgent
from backend.execution.executor_improved import ExecutionEngine
from backend.execution.state_machine import StateMachine, ExecutionState
from backend.mcp.registry import registry
from backend.llm.router import ModelRouter
from backend.mcp.client import MCPClient
from backend.config.settings import settings
from backend.database.connection import SessionLocal
from backend.models.execution import Execution, Message

logger = logging.getLogger(__name__)

class AgentState(TypedDict, total=False):
    execution_id: str
    user_input: str
    intent: Dict[str, Any]
    plan: Dict[str, Any]
    results: Dict[int, Dict[str, Any]]
    approved_step_ids: List[int]
    status: str
    error: str
    pending_approval: Dict[str, Any]
    final_response: str
    execution_state: str
    replan_count: int
    failed_step_info: Dict[str, Any]

try:
    from psycopg_pool import ConnectionPool
except ImportError:
    ConnectionPool = None

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    try:
        from langgraph_checkpoint_sqlite import SqliteSaver
    except ImportError:
        SqliteSaver = None

try:
    from langgraph.checkpoint.postgres import PostgresSaver
except ImportError:
    try:
        from langgraph_checkpoint_postgres import PostgresSaver
    except ImportError:
        PostgresSaver = None

try:
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    MemorySaver = None

class LangGraphOrchestrator:
    def __init__(self):
        self.router = ModelRouter()
        self.prompt_engineer = PromptEngineerAgent(self.router)
        self.planner = PlannerAgent(self.router)
        self.response_agent = ResponseAgent(self.router)
        self.mcp_client = MCPClient()
        self.executor = ExecutionEngine(self.mcp_client)
        
        db_path = settings.DATABASE_URL
        self.conn = None
        self.pool = None

        if db_path.startswith("sqlite") and SqliteSaver is not None:
            import sqlite3
            self.conn = sqlite3.connect(db_path.replace("sqlite:///", ""), check_same_thread=False)
            self.checkpointer = SqliteSaver(self.conn)
            if hasattr(self.checkpointer, "setup"):
                self.checkpointer.setup()
        elif (not db_path.startswith("sqlite")) and PostgresSaver is not None and ConnectionPool is not None:
            # Extract psycopg compatible string
            psycopg_url = db_path
            if psycopg_url.startswith("postgresql+psycopg://"):
                psycopg_url = psycopg_url.replace("postgresql+psycopg://", "postgresql://", 1)
            elif psycopg_url.startswith("postgresql+psycopg2://"):
                psycopg_url = psycopg_url.replace("postgresql+psycopg2://", "postgresql://", 1)
                
            self.pool = ConnectionPool(
                conninfo=psycopg_url,
                min_size=0,
                max_size=settings.LANGGRAPH_POOL_SIZE,
                max_idle=30,
                kwargs={"autocommit": True},
            )
            self.checkpointer = PostgresSaver(self.pool)
            if hasattr(self.checkpointer, "setup"):
                self.checkpointer.setup()
        elif MemorySaver is not None:
            self.checkpointer = MemorySaver()
        else:
            raise RuntimeError("No suitable LangGraph checkpointer available.")
            
        self.graph = self._build_graph()

    def __del__(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
        if hasattr(self, 'pool') and self.pool:
            self.pool.close()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        workflow.add_node("analyze", self._node_analyze)
        workflow.add_node("plan", self._node_plan)
        workflow.add_node("execute", self._node_execute)
        workflow.add_node("replan", self._node_replan)
        workflow.add_node("generate_response", self._node_generate_response)
        workflow.add_node("wait_for_approval", self._node_wait_for_approval)
        
        workflow.add_edge(START, "analyze")
        workflow.add_edge("analyze", "plan")
        workflow.add_edge("plan", "execute")
        
        def route_execution(state: AgentState):
            return state.get("status")
            
        workflow.add_conditional_edges(
            "execute",
            route_execution,
            {
                "completed": "generate_response",
                "waiting_approval": "wait_for_approval",
                "need_replan": "replan",
                "failed": "generate_response"
            }
        )
        
        # Self-healing loop: after replanning, retry execution with the healed plan
        workflow.add_edge("replan", "execute")
        # After waiting for approval, we always loop back to execute
        workflow.add_edge("wait_for_approval", "execute")
        workflow.add_edge("generate_response", END)
        
        # We interrupt execution BEFORE entering the 'wait_for_approval' node
        # This allows the Flask app to return control to the UI
        return workflow.compile(
            checkpointer=self.checkpointer,
            interrupt_before=["wait_for_approval"]
        )

    def _build_context(self, state: AgentState) -> str:
        """Build a comprehensive context including recent chat dialogue and structured execution outputs."""
        context_parts = []
        
        # 1. Recent dialogue from Message table for this thread
        execution_id = state.get("execution_id")
        if execution_id:
            db = SessionLocal()
            try:
                from backend.models.execution import Message
                recent_msgs = db.query(Message).filter(
                    Message.execution_id == execution_id,
                    Message.role.in_(["user", "agent"])
                ).order_by(Message.created_at.desc()).limit(8).all()
                if recent_msgs:
                    recent_msgs.reverse()
                    history_lines = []
                    for m in recent_msgs:
                        if m.role == "user" and (m.content or "").strip() == (state.get("user_input") or "").strip():
                            continue
                        role_label = "User" if m.role == "user" else "Assistant"
                        content_snip = (m.content or "").strip()
                        if len(content_snip) > 400:
                            content_snip = content_snip[:400] + "..."
                        history_lines.append(f"{role_label}: {content_snip}")
                    if history_lines:
                        context_parts.append("Recent conversation dialogue:\n" + "\n".join(history_lines))
            except Exception as e:
                logger.warning(f"Error fetching conversation dialogue: {e}")
            finally:
                db.close()
                
        # 2. Execution steps results with compact items preservation
        results = state.get("results", {})
        if results:
            step_lines = []
            for step_id, res in results.items():
                if res.get("success"):
                    data = res.get('data', {})
                    if isinstance(data, dict):
                        # Ensure quote/service items are NEVER dropped
                        if "items" in data and isinstance(data["items"], list):
                            compact = {
                                "items": [
                                    {
                                        "code": it.get("code") or it.get("service_code"),
                                        "name": it.get("description") or it.get("name"),
                                        "quantity": it.get("quantity", 1),
                                        "unit_price": it.get("price") or it.get("unit_price")
                                    }
                                    for it in data["items"]
                                ]
                            }
                            for k in ["original_subtotal", "total_ht", "tax", "total_ttc", "discount_amount", "discount_percent_val"]:
                                if k in data:
                                    compact[k] = data[k]
                            data_str = json.dumps(compact)
                        else:
                            try:
                                data_str = json.dumps(data)
                                if len(data_str) > 1000:
                                    data_str = data_str[:1000] + "...}"
                            except Exception:
                                data_str = '{"status": "success"}'
                    else:
                        data_str = str(data)[:300]
                    step_lines.append(f"- Step {step_id}: {data_str}")
            if step_lines:
                context_parts.append("Recently executed actions and results:\n" + "\n".join(step_lines[-5:]))
                
        return "\n\n".join(context_parts)

    def _node_analyze(self, state: AgentState):
        if state.get("intent"):
            return state
            
        previous_context = self._build_context(state)
                    
        user_info = ""
        try:
            from flask import request
            current_user = getattr(request, 'current_user', None)
            if current_user:
                user_info = f"Name: {current_user.name}, Email: {current_user.email}"
        except Exception:
            pass

        intent = self.prompt_engineer.analyze(state["user_input"], previous_context, user_info)
        state["intent"] = intent
        return state

    def _node_plan(self, state: AgentState):
        if state.get("plan"):
            return state
            
        available_tools = registry.get_planner_tools()
        
        previous_context = self._build_context(state)
        results = state.get("results", {})
        next_step_id = (max(results.keys()) + 1) if results else 1
                    
        plan = self.planner.plan(state["intent"], available_tools, previous_context, next_step_id, state["user_input"])
        state["plan"] = plan
        return state

    def _node_execute(self, state: AgentState):
        # Checkpoints are serialized by LangGraph, so keep only primitive
        # state in AgentState.  A StateMachine is reconstructed for each run.
        try:
            previous_state = ExecutionState(state.get("execution_state", ExecutionState.RECEIVED.value))
        except ValueError:
            previous_state = ExecutionState.RECEIVED
        sm = StateMachine(previous_state)
            
        result = self.executor.execute_plan(
            execution_id=state["execution_id"],
            plan=state["plan"],
            state_machine=sm,
            approved_step_ids=state.get("approved_step_ids", []),
            prior_results=state.get("results", {})
        )
        
        if sm.current_state == ExecutionState.COMPLETED:
            state["status"] = "completed"
            state["results"] = result.get("results", {})
        elif sm.current_state == ExecutionState.WAITING_APPROVAL:
            state["status"] = "waiting_approval"
            state["results"] = result.get("results", state.get("results", {}))
            state["pending_approval"] = {
                "step": result["step"],
                "tool": result["tool"],
                "arguments": result["arguments"]
            }
        else:
            # Self-healing loop: check if we can replan dynamically
            replan_count = state.get("replan_count", 0)
            if replan_count < 2:
                state["status"] = "need_replan"
                state["replan_count"] = replan_count + 1
                state["failed_step_info"] = {
                    "step_id": result.get("step"),
                    "tool": result.get("tool"),
                    "error": sm.error or result.get("error", "Unknown execution error"),
                }
                state["results"] = result.get("results", state.get("results", {}))
                logger.warning(
                    "Execution step failed. Triggering Self-Healing replan (%s/2). Error: %s",
                    state["replan_count"], state["failed_step_info"]["error"]
                )
            else:
                state["status"] = "failed"
                state["error"] = sm.error or result.get("error")

        state["execution_state"] = sm.current_state.value
        
        return state

    def _node_replan(self, state: AgentState):
        failed_info = state.get("failed_step_info", {})
        failed_step = failed_info.get("step_id")
        failed_tool = failed_info.get("tool")
        failed_err = failed_info.get("error")

        available_tools = registry.get_planner_tools()
        results = state.get("results", {})
        next_step_id = (max(results.keys()) + 1) if results else 1

        context_lines = [
            f"=== SELF-HEALING / RECOVERY MODE (Attempt {state.get('replan_count', 1)}/2) ===",
            f"Previous Step {failed_step} with tool '{failed_tool}' failed with error: {failed_err}.",
            "Please adapt the execution plan to achieve the user's objective without repeating the same error.",
            "Use alternative tools, adjusted parameters, or proceed with remaining tasks."
        ]
        for s_id, res in results.items():
            if res.get("success"):
                try:
                    data_str = json.dumps(res.get('data', {}))[:300]
                except Exception:
                    data_str = "success"
                context_lines.append(f"- Step {s_id} already completed successfully: {data_str}")
        
        recovery_context = "\n".join(context_lines) + "\n"

        new_plan = self.planner.plan(
            intent=state["intent"],
            available_tools=available_tools,
            previous_context=recovery_context,
            next_step_id=next_step_id,
            user_input=state["user_input"]
        )

        existing_steps = state.get("plan", {}).get("steps", [])
        completed_ids = {k for k, v in results.items() if v.get("success")}
        preserved_steps = [s for s in existing_steps if int(s.get("id", 0)) in completed_ids]
        combined_steps = preserved_steps + new_plan.get("steps", [])

        state["plan"] = {"steps": combined_steps}
        state["status"] = "executing"
        state["execution_state"] = ExecutionState.EXECUTING.value
        return state

    def _node_wait_for_approval(self, state: AgentState):
        # This is a dummy node. Execution pauses BEFORE entering this node.
        # When we resume, it simply passes through back to 'execute'.
        return state

    def _node_generate_response(self, state: AgentState):
        if state.get("status") == "completed":
            final = self.response_agent.generate_response(state["user_input"], state.get("results", []))
        else:
            final = self.response_agent.generate_response(state["user_input"], {"error": state.get("error", "Unknown error")})
        state["final_response"] = final
        return state

    def _assert_execution_owner(self, execution_id: str, user_id: int, create: bool = False) -> None:
        """Persist and enforce the owner of every resumable LangGraph thread."""
        db = SessionLocal()
        try:
            execution = db.get(Execution, execution_id)
            if execution is None:
                if create:
                    db.add(Execution(id=execution_id, user_id=user_id, state="RECEIVED"))
                    db.commit()
                    return
                raise PermissionError("Execution not found")
            
            if execution.user_id is None:
                execution.user_id = user_id
                db.commit()
                return
                
            if execution.user_id != user_id:
                raise PermissionError("Execution not found")
        finally:
            db.close()

    def process_request(self, user_input: str, thread_id: str = None, user_id: int = None) -> Dict[str, Any]:
        if user_id is None:
            raise PermissionError("Authenticated user is required")
        execution_id = thread_id or str(uuid.uuid4())
        # Client-side thread IDs may predate the ownership table (or be
        # generated by the UI before the first request). Claim only genuinely
        # missing IDs; an existing ID owned by another user is still rejected.
        self._assert_execution_owner(execution_id, user_id, create=True)
        
        
        db = SessionLocal()
        try:
            execution = db.get(Execution, execution_id)
            # Generate title if missing
            if execution and not execution.title:
                system_prompt = "Tu es un assistant qui génère un titre ultra court (2 à 5 mots max) pour résumer l'intention de l'utilisateur. Réponds uniquement avec le titre, sans guillemets ni fioritures. Langue: français."
                try:
                    title = self.router.generate(capability="fast", prompt=user_input, system_prompt=system_prompt)
                    execution.title = title.strip()
                except Exception as e:
                    execution.title = "Nouvelle discussion"
            
            # Save user message
            db.add(Message(execution_id=execution_id, role="user", content=user_input))
            db.commit()
        finally:
            db.close()
            
        config = {"configurable": {"thread_id": execution_id}}
        
        # Explicitly wipe the intent and plan from the state before invoking, 
        # so that a follow-up request forces re-analysis and re-planning.
        self.graph.update_state(config, {"intent": None, "plan": None})
        
        initial_state = {
            "execution_id": execution_id,
            "user_input": user_input,
            "approved_step_ids": [],
            "status": "",
            "error": "",
            "pending_approval": {},
            "final_response": "",
            "execution_state": ExecutionState.RECEIVED.value
        }
        
        result_state = self.graph.invoke(initial_state, config)
        
        # Save agent response
        final_response = result_state.get("final_response")
        if final_response:
            db = SessionLocal()
            try:
                db.add(Message(execution_id=execution_id, role="agent", content=final_response))
                db.commit()
            finally:
                db.close()
        elif result_state.get("status") == "waiting_approval":
            pending = result_state.get("pending_approval", {})
            approval_msg = json.dumps({
                "type": "approval",
                "tool": pending.get("tool"),
                "arguments": pending.get("arguments"),
                "step": pending.get("step"),
                "status": "pending"
            })
            db = SessionLocal()
            try:
                db.add(Message(execution_id=execution_id, role="agent_action", content=approval_msg))
                db.commit()
            finally:
                db.close()
                
        return self._format_response(result_state, execution_id)

    def process_approval(self, execution_id: str, step_id: int, approved: bool, user_id: int = None, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        if user_id is None:
            raise PermissionError("Authenticated user is required")
        self._assert_execution_owner(execution_id, user_id)
        config = {"configurable": {"thread_id": execution_id}}
        state_snapshot = self.graph.get_state(config)
        
        if not state_snapshot or not state_snapshot.values:
            return {"error": "Execution not found"}
            
        state = dict(state_snapshot.values)
        if state.get("status") != "waiting_approval":
            return {"error": "Execution is not waiting for approval"}
        if state.get("pending_approval", {}).get("step") != step_id:
            return {"error": "Approval does not match the pending step"}
        if not isinstance(approved, bool):
            return {"error": "approved must be a boolean"}
            
        if approved:
            approved_steps = state.get("approved_step_ids", [])
            if step_id not in approved_steps:
                approved_steps.append(step_id)
            
            update_data = {"approved_step_ids": approved_steps}

            if arguments is not None:
                plan = state.get("plan")
                if plan:
                    # Make a deep copy to ensure state update triggers correctly

                    new_plan = copy.deepcopy(plan)
                    for step in new_plan.get("steps", []):
                        if step.get("id") == step_id:
                            step["arguments"] = arguments
                            break
                    update_data["plan"] = new_plan

            # Update the graph state with the new approved steps and plan
            self.graph.update_state(config, update_data)
            
            # Resume execution (it will enter 'wait_for_approval' and then loop to 'execute')
            result_state = self.graph.invoke(None, config)
            
            # Update the agent_action message status
            db = SessionLocal()
            try:
                msg = db.query(Message).filter(
                    Message.execution_id == execution_id,
                    Message.role == "agent_action"
                ).order_by(Message.id.desc()).first()
                if msg:
                    try:
                        data = json.loads(msg.content)
                        if data.get("step") == step_id:
                            data["status"] = "approved"
                            msg.content = json.dumps(data)
                            db.commit()
                    except (json.JSONDecodeError, TypeError, KeyError):
                        logger.warning("Failed to update approval message status", exc_info=True)
                
                final_response = result_state.get("final_response")
                if final_response:
                    db.add(Message(execution_id=execution_id, role="agent", content=final_response))
                    db.commit()
                elif result_state.get("status") == "waiting_approval":
                    pending = result_state.get("pending_approval", {})
                    approval_msg = json.dumps({
                        "type": "approval",
                        "tool": pending.get("tool"),
                        "arguments": pending.get("arguments"),
                        "step": pending.get("step"),
                        "status": "pending"
                    })
                    db.add(Message(execution_id=execution_id, role="agent_action", content=approval_msg))
                    db.commit()
            finally:
                db.close()
                    
            return self._format_response(result_state, execution_id)
        else:
            # If rejected, we update the state directly to failed and run it to generate response
            self.graph.update_state(config, {"status": "failed", "error": "User rejected approval"})
            result_state = self.graph.invoke(None, config)
            
            db = SessionLocal()
            try:
                msg = db.query(Message).filter(
                    Message.execution_id == execution_id,
                    Message.role == "agent_action"
                ).order_by(Message.id.desc()).first()
                if msg:
                    try:
                        data = json.loads(msg.content)
                        if data.get("step") == step_id:
                            data["status"] = "rejected"
                            msg.content = json.dumps(data)
                            db.commit()
                    except (json.JSONDecodeError, TypeError, KeyError):
                        logger.warning("Failed to update rejection message status", exc_info=True)
                
                final_response = result_state.get("final_response")
                if final_response:
                    db.add(Message(execution_id=execution_id, role="agent", content=final_response))
                    db.commit()
                elif result_state.get("status") == "waiting_approval":
                    pending = result_state.get("pending_approval", {})
                    approval_msg = json.dumps({
                        "type": "approval",
                        "tool": pending.get("tool"),
                        "arguments": pending.get("arguments"),
                        "step": pending.get("step"),
                        "status": "pending"
                    })
                    db.add(Message(execution_id=execution_id, role="agent_action", content=approval_msg))
                    db.commit()
            finally:
                db.close()
                    
            return {
                "status": "failed",
                "execution_id": execution_id,
                "message": final_response or "Execution cancelled due to user rejection."
            }

    def _format_response(self, state: Dict[str, Any], execution_id: str) -> Dict[str, Any]:
        if state.get("status") == "completed":
            return {
                "status": "completed",
                "execution_id": execution_id,
                "response": state.get("final_response", ""),
                "results": state.get("results", [])
            }
        elif state.get("status") == "waiting_approval":
            pending = state.get("pending_approval", {})
            return {
                "status": "waiting_approval",
                "execution_id": execution_id,
                "step": pending.get("step"),
                "tool": pending.get("tool"),
                "arguments": pending.get("arguments")
            }
        else:
            return {
                "status": "failed",
                "execution_id": execution_id,
                "response": state.get("final_response", ""),
                "error": state.get("error", "Unknown error")
            }
