"""Tests for the Jira Worklog mixin."""

from unittest.mock import MagicMock

import pytest

from mcp_atlassian.jira.worklog import WorklogMixin


class TestWorklogMixin:
    """Tests for the WorklogMixin class."""

    @pytest.fixture
    def worklog_mixin(self, jira_client):
        """Create a WorklogMixin instance with mocked dependencies."""
        mixin = WorklogMixin(config=jira_client.config)
        mixin.jira = jira_client.jira

        # Mock methods that are typically provided by other mixins
        mixin._clean_text = MagicMock(side_effect=lambda text: text if text else "")

        return mixin

    def test_parse_time_spent_with_seconds(self, worklog_mixin):
        """Test parsing time spent with seconds specification."""
        assert worklog_mixin._parse_time_spent("60s") == 60
        assert worklog_mixin._parse_time_spent("3600s") == 3600

    def test_parse_time_spent_with_minutes(self, worklog_mixin):
        """Test parsing time spent with minutes."""
        assert worklog_mixin._parse_time_spent("1m") == 60
        assert worklog_mixin._parse_time_spent("30m") == 1800

    def test_parse_time_spent_with_hours(self, worklog_mixin):
        """Test parsing time spent with hours."""
        assert worklog_mixin._parse_time_spent("1h") == 3600
        assert worklog_mixin._parse_time_spent("2h") == 7200

    def test_parse_time_spent_with_days(self, worklog_mixin):
        """Test parsing time spent with days."""
        assert worklog_mixin._parse_time_spent("1d") == 86400
        assert worklog_mixin._parse_time_spent("2d") == 172800

    def test_parse_time_spent_with_weeks(self, worklog_mixin):
        """Test parsing time spent with weeks."""
        assert worklog_mixin._parse_time_spent("1w") == 604800
        assert worklog_mixin._parse_time_spent("2w") == 1209600

    def test_parse_time_spent_with_mixed_units(self, worklog_mixin):
        """Test parsing time spent with mixed units."""
        assert worklog_mixin._parse_time_spent("1h 30m") == 5400
        assert worklog_mixin._parse_time_spent("1d 6h") == 108000
        assert worklog_mixin._parse_time_spent("1w 2d 3h 4m") == 788640

    def test_parse_time_spent_with_invalid_input(self, worklog_mixin):
        """Test parsing time spent with invalid input."""
        # Should default to 60 seconds
        assert worklog_mixin._parse_time_spent("invalid") == 60

    def test_parse_time_spent_with_numeric_input(self, worklog_mixin):
        """Test parsing time spent with numeric input."""
        assert worklog_mixin._parse_time_spent("60") == 60
        assert worklog_mixin._parse_time_spent("3600") == 3600

    def test_get_worklogs_basic(self, worklog_mixin):
        """Test basic functionality of get_worklogs."""
        # Setup mock response
        mock_result = {
            "worklogs": [
                {
                    "id": "10001",
                    "comment": "Work item 1",
                    "created": "2024-01-01T10:00:00.000+0000",
                    "updated": "2024-01-01T10:30:00.000+0000",
                    "started": "2024-01-01T09:00:00.000+0000",
                    "timeSpent": "1h",
                    "timeSpentSeconds": 3600,
                    "author": {"displayName": "Test User"},
                }
            ]
        }
        worklog_mixin.jira.issue_get_worklog.return_value = mock_result

        # Call the method
        result = worklog_mixin.get_worklogs("TEST-123")

        # Verify
        worklog_mixin.jira.issue_get_worklog.assert_called_once_with("TEST-123")
        assert len(result) == 1
        assert result[0]["id"] == "10001"
        assert result[0]["comment"] == "Work item 1"
        assert result[0]["timeSpent"] == "1h"
        assert result[0]["timeSpentSeconds"] == 3600
        assert result[0]["author"] == "Test User"

    def test_get_worklogs_with_multiple_entries(self, worklog_mixin):
        """Test get_worklogs with multiple worklog entries."""
        # Setup mock response with multiple entries
        mock_result = {
            "worklogs": [
                {
                    "id": "10001",
                    "comment": "Work item 1",
                    "created": "2024-01-01T10:00:00.000+0000",
                    "timeSpent": "1h",
                    "timeSpentSeconds": 3600,
                    "author": {"displayName": "User 1"},
                },
                {
                    "id": "10002",
                    "comment": "Work item 2",
                    "created": "2024-01-02T10:00:00.000+0000",
                    "timeSpent": "2h",
                    "timeSpentSeconds": 7200,
                    "author": {"displayName": "User 2"},
                },
            ]
        }
        worklog_mixin.jira.issue_get_worklog.return_value = mock_result

        # Call the method
        result = worklog_mixin.get_worklogs("TEST-123")

        # Verify
        assert len(result) == 2
        assert result[0]["id"] == "10001"
        assert result[1]["id"] == "10002"
        assert result[0]["timeSpentSeconds"] == 3600
        assert result[1]["timeSpentSeconds"] == 7200

    def test_get_worklogs_with_missing_fields(self, worklog_mixin):
        """Test get_worklogs with missing fields."""
        # Setup mock response with missing fields
        mock_result = {
            "worklogs": [
                {
                    "id": "10001",
                    # Missing comment
                    "created": "2024-01-01T10:00:00.000+0000",
                    # Missing other fields
                }
            ]
        }
        worklog_mixin.jira.issue_get_worklog.return_value = mock_result

        # Call the method
        result = worklog_mixin.get_worklogs("TEST-123")

        # Verify
        assert len(result) == 1
        assert result[0]["id"] == "10001"
        assert result[0]["comment"] == ""
        assert result[0]["timeSpent"] == ""
        assert result[0]["timeSpentSeconds"] == 0
        assert result[0]["author"] == "Unknown"

    def test_get_worklogs_with_empty_response(self, worklog_mixin):
        """Test get_worklogs with empty response."""
        # Setup mock response with no worklogs
        worklog_mixin.jira.issue_get_worklog.return_value = {}

        # Call the method
        result = worklog_mixin.get_worklogs("TEST-123")

        # Verify
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_worklogs_with_error(self, worklog_mixin):
        """Test get_worklogs error handling."""
        # Setup mock to raise exception
        worklog_mixin.jira.issue_get_worklog.side_effect = Exception(
            "Worklog fetch error"
        )

        # Call the method and verify exception
        with pytest.raises(
            Exception, match="Error getting worklogs: Worklog fetch error"
        ):
            worklog_mixin.get_worklogs("TEST-123")
