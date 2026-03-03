# #type:ignore
# import os
# from dotenv import load_dotenv
# from typing import Optional, List

# from langchain_openai import AzureChatOpenAI
# from langchain_core.tools import BaseTool

# load_dotenv()

# API_KEY = os.getenv("API_KEY")
# API_VERSION = os.getenv("API_VERSION")
# AZURE_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT")
# AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")

# _llm: Optional[AzureChatOpenAI] = None

# def get_llm(tools: Optional[List[BaseTool]] = None)-> AzureChatOpenAI:
#     global _llm

#     if _llm is None:
#         _llm = AzureChatOpenAI(api_key=API_KEY, api_version=API_VERSION, azure_endpoint=AZURE_ENDPOINT,azure_deployment=AZURE_DEPLOYMENT, model_kwargs={"response_format": {"type": "json_object"}},)
    
#     if tools:
#         return _llm.bind_tools(tools)

#     return _llm

# # llm.py
# # type: ignore
# # import os
# # from dotenv import load_dotenv
# # from typing import Optional, List

# # from langchain_openai import AzureChatOpenAI
# # from langchain_core.tools import BaseTool

# # load_dotenv()

# # # Prefer the standard Azure OpenAI env var names to avoid confusion
# # AZURE_OPENAI_API_KEY = "7f6fqNT1dndbpQpoeWOGT3i6wrb6hcsB2W6302bZkuOfY8zOT651JQQJ99CBACYeBjFXJ3w3AAAAACOGMp1b"
# # AZURE_OPENAI_API_VERSION = "2024-05-01-preview"
# # AZURE_OPENAI_ENDPOINT = "https://UPS-FoundryResource1.openai.azure.com/openai/v1/"
# # AZURE_OPENAI_DEPLOYMENT = "gpt-4.1-mini"

# # _llm: Optional[AzureChatOpenAI] = None

# # def _require(name: str, value: Optional[str]) -> str:
# #     if not value:
# #         raise RuntimeError(
# #             f"Missing required environment variable: {name}. "
# #             f"Set it in your .env or environment. For Azure OpenAI, you need:\n"
# #             f"  AZURE_OPENAI_ENDPOINT (e.g., https://<resource>.openai.azure.com/)\n"
# #             f"  AZURE_OPENAI_API_KEY\n"
# #             f"  AZURE_OPENAI_API_VERSION (e.g., 2024-06-01)\n"
# #             f"  AZURE_OPENAI_DEPLOYMENT (your deployment name, NOT the model id)"
# #         )
# #     return value

# # def get_llm(tools: Optional[List[BaseTool]] = None) -> AzureChatOpenAI:
# #     """
# #     Returns a singleton AzureChatOpenAI configured for Azure OpenAI.
# #     Make sure the deployment exists in your Azure resource and the
# #     endpoint + api_version match that resource/region.

# #     Required env vars:
# #       - AZURE_OPENAI_ENDPOINT          -> https://<resource>.openai.azure.com/
# #       - AZURE_OPENAI_API_KEY           -> your key
# #       - AZURE_OPENAI_API_VERSION       -> e.g. 2024-06-01
# #       - AZURE_OPENAI_DEPLOYMENT        -> your deployment name (e.g., gpt-4o-mini-prod)
# #     """
# #     global _llm
# #     if _llm is None:
# #         endpoint = _require("AZURE_OPENAI_ENDPOINT", AZURE_OPENAI_ENDPOINT)
# #         api_key = _require("AZURE_OPENAI_API_KEY", AZURE_OPENAI_API_KEY)
# #         api_version = _require("AZURE_OPENAI_API_VERSION", AZURE_OPENAI_API_VERSION)
# #         deployment = _require("AZURE_OPENAI_DEPLOYMENT", AZURE_OPENAI_DEPLOYMENT)

# #         # IMPORTANT: use azure_deployment (not deployment_name)
# #         _llm = AzureChatOpenAI(
# #             azure_endpoint=endpoint,
# #             api_version=api_version,
# #             azure_deployment=deployment,        # ✅ correct kwarg
# #             openai_api_key=api_key,             # api_key or openai_api_key; both are supported in recent versions
# #             temperature=0,
# #             # Safer for JSON parsing in your table agent
# #             model_kwargs={"response_format": {"type": "json_object"}}
# #         )

# #     if tools:
# #         return _llm.bind_tools(tools)
# #     return _llm


# llm.py
# type: ignore
import os
from dotenv import load_dotenv
from typing import Optional, List
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import BaseTool

load_dotenv()

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION") or os.getenv("API_VERSION")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("AZURE_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("AZURE_DEPLOYMENT")

_llm: Optional[AzureChatOpenAI] = None

def _require(name: str, value: Optional[str]) -> str:
    if not value:
        raise RuntimeError(
            f"Missing environment variable: {name}. "
            "Required: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT"
        )
    return value

def get_llm(tools: Optional[List[BaseTool]] = None) -> AzureChatOpenAI:
    """Plain chat model (no JSON mode). Use this for free-form or SQL output."""
    global _llm
    if _llm is None:
        endpoint = _require("AZURE_OPENAI_ENDPOINT", AZURE_OPENAI_ENDPOINT)
        api_key = _require("AZURE_OPENAI_API_KEY", AZURE_OPENAI_API_KEY)
        api_version = _require("AZURE_OPENAI_API_VERSION", AZURE_OPENAI_API_VERSION)
        deployment = _require("AZURE_OPENAI_DEPLOYMENT", AZURE_OPENAI_DEPLOYMENT)

        _llm = AzureChatOpenAI(
            azure_endpoint=endpoint,
            api_version=api_version,
            azure_deployment=deployment,
            openai_api_key=api_key,
            temperature=0,
        )
    return _llm.bind_tools(tools) if tools else _llm

def get_json_llm(tools: Optional[List[BaseTool]] = None) -> AzureChatOpenAI:
    """
    JSON-mode variant. Use this ONLY for agents that must return JSON.
    Remember: At least one message must contain the word 'json'.
    """
    base = get_llm()
    json_llm = base.bind(response_format={"type": "json_object"})
    return json_llm.bind_tools(tools) if tools else json_llm