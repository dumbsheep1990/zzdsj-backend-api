from fastapi import APIRouter
from app.api.owl.agent_definition import router as agent_definition_router
from app.api.owl.agent_template import router as agent_template_router
from app.api.owl.tool import router as tool_router
from app.api.owl.agent_run import router as agent_run_router
from app.api.owl.nlc import router as nlc_router
from app.api.owl.tool_chain import router as tool_chain_router

# 创建OWL主路由
router = APIRouter(prefix="/owl", tags=["OWL Framework"])

# 注册子路由
router.include_router(
    agent_definition_router, 
    prefix="/agent-definitions", 
    tags=["Agent Definitions"]
)
router.include_router(
    agent_template_router, 
    prefix="/agent-templates", 
    tags=["Agent Templates"]
)
router.include_router(
    tool_router, 
    prefix="/tools", 
    tags=["Tools"]
)
router.include_router(
    agent_run_router, 
    prefix="/agents", 
    tags=["Agent Execution"]
)
router.include_router(
    nlc_router, 
    prefix="/nlc", 
    tags=["Natural Language Configuration"]
)
router.include_router(
    tool_chain_router, 
    prefix="/tool-chains", 
    tags=["Tool Chains"]
)
