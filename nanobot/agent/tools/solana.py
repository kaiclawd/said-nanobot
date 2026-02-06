"""Solana blockchain tools for SAID-verified AI agents."""

import json
import os
import urllib.request
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool

# SAID API
SAID_API = "https://api.saidprotocol.com"


class GetBalanceTool(Tool):
    """Get SOL balance for a wallet address."""
    
    @property
    def name(self) -> str:
        return "get_sol_balance"
    
    @property
    def description(self) -> str:
        return "Get SOL balance for a Solana wallet address. Returns balance in SOL."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Solana wallet address (base58)"
                }
            },
            "required": ["address"]
        }
    
    async def execute(self, address: str) -> str:
        try:
            rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
            payload = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [address]
            }).encode()
            
            req = urllib.request.Request(
                rpc_url,
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                if "result" in data:
                    lamports = data["result"]["value"]
                    sol = lamports / 1_000_000_000
                    return json.dumps({"address": address, "balance_sol": sol, "balance_lamports": lamports})
                else:
                    return json.dumps({"error": data.get("error", "Unknown error")})
        except Exception as e:
            return json.dumps({"error": str(e)})


class VerifyAgentTool(Tool):
    """Verify another agent's SAID identity."""
    
    @property
    def name(self) -> str:
        return "verify_said_agent"
    
    @property
    def description(self) -> str:
        return "Verify if a wallet address is a registered SAID agent. Use before transacting with unknown agents."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "wallet": {
                    "type": "string",
                    "description": "Solana wallet address to verify"
                }
            },
            "required": ["wallet"]
        }
    
    async def execute(self, wallet: str) -> str:
        try:
            url = f"{SAID_API}/api/agents/{wallet}"
            with urllib.request.urlopen(url, timeout=10) as resp:
                agent = json.loads(resp.read().decode())
                return json.dumps({
                    "verified": True,
                    "name": agent.get("name"),
                    "wallet": agent.get("wallet"),
                    "pda": agent.get("pda"),
                    "isVerified": agent.get("isVerified"),
                    "reputationScore": agent.get("reputationScore"),
                    "description": agent.get("description"),
                    "profile": f"https://www.saidprotocol.com/agent.html?wallet={wallet}"
                })
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return json.dumps({"verified": False, "error": "Agent not found in SAID registry"})
            return json.dumps({"verified": False, "error": str(e)})
        except Exception as e:
            return json.dumps({"verified": False, "error": str(e)})


class LookupAgentTool(Tool):
    """Get full SAID profile for an agent."""
    
    @property
    def name(self) -> str:
        return "lookup_said_agent"
    
    @property
    def description(self) -> str:
        return "Get full SAID profile for an agent by wallet address, including reputation and skills."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "wallet": {
                    "type": "string",
                    "description": "Solana wallet address to lookup"
                }
            },
            "required": ["wallet"]
        }
    
    async def execute(self, wallet: str) -> str:
        try:
            url = f"{SAID_API}/api/agents/{wallet}"
            with urllib.request.urlopen(url, timeout=10) as resp:
                return resp.read().decode()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return json.dumps({"error": "Agent not found"})
            return json.dumps({"error": str(e)})
        except Exception as e:
            return json.dumps({"error": str(e)})


class GetTrustScoreTool(Tool):
    """Get trust score for an agent."""
    
    @property
    def name(self) -> str:
        return "get_trust_score"
    
    @property
    def description(self) -> str:
        return "Get the trust score and trust network for a SAID agent."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "wallet": {
                    "type": "string",
                    "description": "Solana wallet address"
                }
            },
            "required": ["wallet"]
        }
    
    async def execute(self, wallet: str) -> str:
        try:
            url = f"{SAID_API}/api/trust/{wallet}"
            with urllib.request.urlopen(url, timeout=10) as resp:
                return resp.read().decode()
        except Exception as e:
            return json.dumps({"error": str(e)})


class RegisterAgentTool(Tool):
    """Register as a SAID agent (pending status)."""
    
    @property
    def name(self) -> str:
        return "register_said_agent"
    
    @property
    def description(self) -> str:
        return "Register a new agent on SAID Protocol with pending status (free, instant)."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "wallet": {
                    "type": "string",
                    "description": "Solana wallet address"
                },
                "name": {
                    "type": "string",
                    "description": "Agent name"
                },
                "description": {
                    "type": "string",
                    "description": "Agent description"
                }
            },
            "required": ["wallet", "name"]
        }
    
    async def execute(self, wallet: str, name: str, description: str = "") -> str:
        try:
            url = f"{SAID_API}/api/register/pending"
            payload = json.dumps({
                "wallet": wallet,
                "name": name,
                "description": description or f"{name} - AI Agent"
            }).encode()
            
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return json.dumps({
                    "success": True,
                    "wallet": result.get("wallet"),
                    "pda": result.get("pda"),
                    "profile": result.get("profile"),
                    "status": "PENDING"
                })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


class GetMyIdentityTool(Tool):
    """Get the agent's own SAID identity from local config."""
    
    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or Path.cwd()
    
    @property
    def name(self) -> str:
        return "get_my_said_identity"
    
    @property
    def description(self) -> str:
        return "Get your own SAID identity information from local said.json file."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }
    
    async def execute(self) -> str:
        # Check multiple locations
        paths = [
            self.workspace / "said.json",
            Path.home() / ".nanobot" / "said.json",
            Path.home() / ".config" / "said" / "identity.json"
        ]
        
        for path in paths:
            if path.exists():
                try:
                    with open(path) as f:
                        return f.read()
                except Exception as e:
                    continue
        
        return json.dumps({"error": "SAID identity not found. Register first with register_said_agent."})


# Export all tools
SOLANA_TOOLS = [
    GetBalanceTool,
    VerifyAgentTool,
    LookupAgentTool,
    GetTrustScoreTool,
    RegisterAgentTool,
    GetMyIdentityTool,
]
