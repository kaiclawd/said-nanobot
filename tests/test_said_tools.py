"""Tests for SAID Solana tools — validates API endpoints and response handling."""

import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock

from nanobot.agent.tools.solana import (
    GetBalanceTool,
    VerifyAgentTool,
    GetTrustScoreTool,
    GetEnforcementTool,
    DiscoverAgentsTool,
    GetLeaderboardTool,
    GetNetworkStatsTool,
    SubmitFeedbackTool,
    RegisterAgentTool,
    GetMyIdentityTool,
)


def run_async(coro):
    """Helper to run async code in tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


class TestVerifyAgentTool:
    def test_name(self):
        tool = VerifyAgentTool()
        assert tool.name == "verify_said_agent"

    def test_parameters_have_wallet(self):
        tool = VerifyAgentTool()
        params = tool.parameters
        assert "wallet" in params["properties"]
        assert "wallet" in params["required"]

    def test_description_mentions_slashing(self):
        tool = VerifyAgentTool()
        assert "slash" in tool.description.lower()

    @patch("nanobot.agent.tools.solana._fetch_json")
    def test_returns_not_found_for_unknown(self, mock_fetch):
        mock_fetch.return_value = None
        tool = VerifyAgentTool()
        result = json.loads(asyncio.run(tool.execute("UNKNOWN")))
        assert result["verified"] is False
        assert "not found" in result["error"].lower()

    @patch("nanobot.agent.tools.solana._fetch_json")
    def test_detects_slashed_agent(self, mock_fetch):
        mock_fetch.return_value = {
            "registered": True,
            "verified": True,
            "wallet": "SLASHED",
            "identity": {"name": "Bad Agent"},
            "slashed": True,
            "trustScore": {"score": 5, "tier": "unranked"},
            "reputation": {"score": 0.1, "feedbackCount": 3},
        }
        tool = VerifyAgentTool()
        result = json.loads(asyncio.run(tool.execute("SLASHED")))
        assert result["slashed"] is True
        assert "WARNING" in result
        assert "SLASHED" in result["WARNING"]

    @patch("nanobot.agent.tools.solana._fetch_json")
    def test_returns_verified_agent_data(self, mock_fetch):
        mock_fetch.return_value = {
            "registered": True,
            "verified": True,
            "wallet": "GOOD",
            "identity": {"name": "Good Agent", "description": "Reliable"},
            "slashed": False,
            "trustScore": {"score": 85, "tier": "gold"},
            "reputation": {"score": 0.9, "feedbackCount": 50},
        }
        tool = VerifyAgentTool()
        result = json.loads(asyncio.run(tool.execute("GOOD")))
        assert result["verified"] is True
        assert result["name"] == "Good Agent"
        assert result["trust_score"] == 85
        assert result["slashed"] is False


class TestGetTrustScoreTool:
    def test_name(self):
        assert GetTrustScoreTool().name == "get_trust_score"

    @patch("nanobot.agent.tools.solana._fetch_json")
    def test_returns_score_from_score_endpoint(self, mock_fetch):
        mock_fetch.return_value = {"score": 92, "tier": "gold", "identity": 9}
        tool = GetTrustScoreTool()
        result = json.loads(asyncio.run(tool.execute("WALLET")))
        assert result["score"] == 92
        assert result["tier"] == "gold"


class TestDiscoverAgentsTool:
    def test_name(self):
        assert DiscoverAgentsTool().name == "discover_said_agents"

    @patch("nanobot.agent.tools.solana._fetch_json")
    def test_returns_agent_list(self, mock_fetch):
        mock_fetch.return_value = [{"name": "Agent1"}, {"name": "Agent2"}]
        tool = DiscoverAgentsTool()
        result = json.loads(asyncio.run(tool.execute()))
        assert result["count"] == 2


class TestGetNetworkStatsTool:
    def test_name(self):
        assert GetNetworkStatsTool().name == "get_said_stats"

    @patch("nanobot.agent.tools.solana._fetch_json")
    def test_returns_stats(self, mock_fetch):
        mock_fetch.return_value = {"totalAgents": 6674, "verified": 6324}
        tool = GetNetworkStatsTool()
        result = json.loads(asyncio.run(tool.execute()))
        assert result["totalAgents"] == 6674


class TestSubmitFeedbackTool:
    def test_name(self):
        assert SubmitFeedbackTool().name == "submit_said_feedback"

    @patch("nanobot.agent.tools.solana._post_json")
    def test_submits_feedback(self, mock_post):
        mock_post.return_value = {"success": True}
        tool = SubmitFeedbackTool()
        result = json.loads(asyncio.run(tool.execute("WALLET", 5, "Great")))
        assert result["success"] is True


class TestGetLeaderboardTool:
    def test_name(self):
        assert GetLeaderboardTool().name == "get_said_leaderboard"


class TestRegisterAgentTool:
    def test_name(self):
        assert RegisterAgentTool().name == "register_said_agent"


class TestToolCount:
    """Verify we have 10 SAID tools (up from 9 in v1)."""

    def test_ten_tools_available(self):
        from nanobot.agent.tools.solana import SOLANA_TOOLS

        assert len(SOLANA_TOOLS) == 10


class TestGetEnforcementTool:
    def test_name(self):
        tool = GetEnforcementTool()
        assert tool.name == "get_said_enforcement"

    def test_parameters_have_wallet(self):
        tool = GetEnforcementTool()
        params = tool.parameters
        assert "wallet" in params["properties"]
        assert "wallet" in params["required"]

    def test_description_mentions_staking_and_slashing(self):
        tool = GetEnforcementTool()
        desc = tool.description.lower()
        assert "staking" in desc or "stake" in desc
        assert "slash" in desc

    @patch("nanobot.agent.tools.solana._fetch_json")
    def test_returns_staked_agent_data(self, mock_fetch):
        mock_fetch.return_value = {
            "stakedAmount": 5.0,
            "slashed": False,
            "slashCount": 0,
            "enforcementTier": "economic",
            "stakePda": "7Xf3...test",
        }
        tool = GetEnforcementTool()
        result = json.loads(asyncio.run(tool.execute("STAKED")))

        assert result["staked"] == 5.0
        assert result["slashed"] is False
        assert result["slash_count"] == 0
        assert result["enforcement_tier"] == "economic"
        assert "skin-in-the-game" in result["note"]

    @patch("nanobot.agent.tools.solana._fetch_json")
    def test_detects_slashed_agent(self, mock_fetch):
        mock_fetch.return_value = {
            "stakedAmount": 2.0,
            "slashed": True,
            "slashCount": 3,
            "enforcementTier": "economic",
        }
        tool = GetEnforcementTool()
        result = json.loads(asyncio.run(tool.execute("SLASHED")))

        assert result["slashed"] is True
        assert result["slash_count"] == 3
        assert "WARNING" in result
        assert "3x" in result["WARNING"]

    @patch("nanobot.agent.tools.solana._fetch_json")
    def test_returns_none_for_unstaked(self, mock_fetch):
        mock_fetch.return_value = {
            "stakedAmount": 0,
            "slashCount": 0,
            "slashed": False,
        }
        tool = GetEnforcementTool()
        result = json.loads(asyncio.run(tool.execute("UNSTAKED")))

        assert result["staked"] == 0
        assert result["slashed"] is False
        assert result["enforcement_tier"] == "none"
        assert "no economic stake" in result["note"]

    @patch("nanobot.agent.tools.solana._fetch_json")
    def test_returns_default_when_api_returns_none(self, mock_fetch):
        mock_fetch.return_value = None
        tool = GetEnforcementTool()
        result = json.loads(asyncio.run(tool.execute("UNKNOWN")))

        assert result["staked"] == 0
        assert result["slashed"] is False
        assert result["slash_count"] == 0
        assert result["enforcement_tier"] == "none"

    @patch("nanobot.agent.tools.solana._fetch_json")
    def test_derives_slashed_from_slash_count(self, mock_fetch):
        """When slashed field is not present, derive from slashCount."""
        mock_fetch.return_value = {
            "stakedAmount": 1.0,
            "slashCount": 2,
            # Note: no 'slashed' field
        }
        tool = GetEnforcementTool()
        result = json.loads(asyncio.run(tool.execute("DERIVED")))

        assert result["slashed"] is True
        assert result["slash_count"] == 2
