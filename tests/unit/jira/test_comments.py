"""Tests for the Jira Comments mixin."""

from unittest.mock import MagicMock, Mock

import pytest

from mcp_atlassian.jira.comments import CommentsMixin


class TestCommentsMixin:
    """Tests for the CommentsMixin class."""

    @pytest.fixture
    def comments_mixin(self, jira_client):
        """Create a CommentsMixin instance with mocked dependencies."""
        mixin = CommentsMixin(config=jira_client.config)
        mixin.jira = jira_client.jira

        # Set up a mock preprocessor with markdown_to_jira method
        mixin.preprocessor = Mock()
        mixin.preprocessor.markdown_to_jira = Mock(
            return_value="*This* is _Jira_ formatted"
        )

        # Mock the clean_text method
        mixin._clean_text = Mock(side_effect=lambda x: x)

        return mixin

    def test_get_issue_comments_basic(self, comments_mixin):
        """Test get_issue_comments with basic data."""
        # Setup mock response
        comments_mixin.jira.issue_get_comments.return_value = {
            "comments": [
                {
                    "id": "10001",
                    "body": "This is a comment",
                    "created": "2024-01-01T10:00:00.000+0000",
                    "updated": "2024-01-01T11:00:00.000+0000",
                    "author": {"displayName": "John Doe"},
                }
            ]
        }

        # Call the method
        result = comments_mixin.get_issue_comments("TEST-123")

        # Verify
        comments_mixin.jira.issue_get_comments.assert_called_once_with("TEST-123")
        assert len(result) == 1
        assert result[0]["id"] == "10001"
        assert result[0]["body"] == "This is a comment"
        assert result[0]["created"] == "2024-01-01 10:00:00+00:00"  # Parsed date
        assert result[0]["author"] == "John Doe"

    def test_get_issue_comments_with_limit(self, comments_mixin):
        """Test get_issue_comments with limit parameter."""
        # Setup mock response with multiple comments
        comments_mixin.jira.issue_get_comments.return_value = {
            "comments": [
                {
                    "id": "10001",
                    "body": "First comment",
                    "created": "2024-01-01T10:00:00.000+0000",
                    "author": {"displayName": "John Doe"},
                },
                {
                    "id": "10002",
                    "body": "Second comment",
                    "created": "2024-01-02T10:00:00.000+0000",
                    "author": {"displayName": "Jane Smith"},
                },
                {
                    "id": "10003",
                    "body": "Third comment",
                    "created": "2024-01-03T10:00:00.000+0000",
                    "author": {"displayName": "Bob Johnson"},
                },
            ]
        }

        # Call the method with limit=2
        result = comments_mixin.get_issue_comments("TEST-123", limit=2)

        # Verify
        comments_mixin.jira.issue_get_comments.assert_called_once_with("TEST-123")
        assert len(result) == 2  # Only 2 comments should be returned
        assert result[0]["id"] == "10001"
        assert result[1]["id"] == "10002"
        # Third comment shouldn't be included due to limit

    def test_get_issue_comments_with_missing_fields(self, comments_mixin):
        """Test get_issue_comments with missing fields in the response."""
        # Setup mock response with missing fields
        comments_mixin.jira.issue_get_comments.return_value = {
            "comments": [
                {
                    "id": "10001",
                    # Missing body field
                    "created": "2024-01-01T10:00:00.000+0000",
                    # Missing author field
                },
                {
                    # Missing id field
                    "body": "Second comment",
                    # Missing created field
                    "author": {},  # Empty author object
                },
                {
                    "id": "10003",
                    "body": "Third comment",
                    "created": "2024-01-03T10:00:00.000+0000",
                    "author": {"name": "user123"},  # Using name instead of displayName
                },
            ]
        }

        # Call the method
        result = comments_mixin.get_issue_comments("TEST-123")

        # Verify
        assert len(result) == 3
        assert result[0]["id"] == "10001"
        assert result[0]["body"] == ""  # Should default to empty string
        assert result[0]["author"] == "Unknown"  # Should default to Unknown

        assert (
            "id" not in result[1] or not result[1]["id"]
        )  # Should be missing or empty
        assert result[1]["author"] == "Unknown"  # Should default to Unknown

        assert (
            result[2]["author"] == "Unknown"
        )  # Should use Unknown when only name is available

    def test_get_issue_comments_with_empty_response(self, comments_mixin):
        """Test get_issue_comments with an empty response."""
        # Setup mock response with no comments
        comments_mixin.jira.issue_get_comments.return_value = {"comments": []}

        # Call the method
        result = comments_mixin.get_issue_comments("TEST-123")

        # Verify
        assert len(result) == 0  # Should return an empty list

    def test_get_issue_comments_with_error(self, comments_mixin):
        """Test get_issue_comments with an error response."""
        # Setup mock to raise exception
        comments_mixin.jira.issue_get_comments.side_effect = Exception("API Error")

        # Verify it raises the wrapped exception
        with pytest.raises(Exception, match="Error getting comments"):
            comments_mixin.get_issue_comments("TEST-123")

    def test_add_comment_basic(self, comments_mixin):
        """Test add_comment with basic data."""
        # Setup mock response
        comments_mixin.jira.issue_add_comment.return_value = {
            "id": "10001",
            "body": "This is a comment",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        }

        # Call the method
        result = comments_mixin.add_comment("TEST-123", "Test comment")

        # Verify
        comments_mixin.preprocessor.markdown_to_jira.assert_called_once_with(
            "Test comment"
        )
        comments_mixin.jira.issue_add_comment.assert_called_once_with(
            "TEST-123", "*This* is _Jira_ formatted"
        )
        assert result["id"] == "10001"
        assert result["body"] == "This is a comment"
        assert result["created"] == "2024-01-01 10:00:00+00:00"  # Parsed date
        assert result["author"] == "John Doe"

    def test_add_comment_with_markdown_conversion(self, comments_mixin):
        """Test add_comment with markdown conversion."""
        # Setup mock response
        comments_mixin.jira.issue_add_comment.return_value = {
            "id": "10001",
            "body": "*This* is _Jira_ formatted",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        }

        # Create a complex markdown comment
        markdown_comment = """
        # Heading 1

        This is a paragraph with **bold** and *italic* text.

        - List item 1
        - List item 2

        ```python
        def hello():
            print("Hello world")
        ```
        """

        # Call the method
        result = comments_mixin.add_comment("TEST-123", markdown_comment)

        # Verify
        comments_mixin.preprocessor.markdown_to_jira.assert_called_once_with(
            markdown_comment
        )
        comments_mixin.jira.issue_add_comment.assert_called_once_with(
            "TEST-123", "*This* is _Jira_ formatted"
        )
        assert result["body"] == "*This* is _Jira_ formatted"

    def test_add_comment_with_empty_comment(self, comments_mixin):
        """Test add_comment with an empty comment."""
        # Setup mock response
        comments_mixin.jira.issue_add_comment.return_value = {
            "id": "10001",
            "body": "",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        }

        # Call the method with empty comment
        result = comments_mixin.add_comment("TEST-123", "")

        # Verify - for empty comments, markdown_to_jira should NOT be called as per implementation
        comments_mixin.preprocessor.markdown_to_jira.assert_not_called()
        comments_mixin.jira.issue_add_comment.assert_called_once_with("TEST-123", "")
        assert result["body"] == ""

    def test_add_comment_with_error(self, comments_mixin):
        """Test add_comment with an error response."""
        # Setup mock to raise exception
        comments_mixin.jira.issue_add_comment.side_effect = Exception("API Error")

        # Verify it raises the wrapped exception
        with pytest.raises(Exception, match="Error adding comment"):
            comments_mixin.add_comment("TEST-123", "Test comment")

    def test_markdown_to_jira(self, comments_mixin):
        """Test markdown to Jira conversion."""
        # Setup - need to replace the mock entirely
        comments_mixin.preprocessor.markdown_to_jira = MagicMock(
            return_value="Jira text"
        )

        # Call the method
        result = comments_mixin._markdown_to_jira("Markdown text")

        # Verify
        assert result == "Jira text"
        comments_mixin.preprocessor.markdown_to_jira.assert_called_once_with(
            "Markdown text"
        )

    def test_markdown_to_jira_with_empty_text(self, comments_mixin):
        """Test _markdown_to_jira with empty text."""
        result = comments_mixin._markdown_to_jira("")
        assert result == ""

    def test_add_comment_with_force_internal_comments_enabled(self, comments_mixin):
        """Test add_comment with force_internal_comments enabled."""
        # Enable force_internal_comments
        comments_mixin.config.force_internal_comments = True
        
        # Setup mock response for direct REST API call
        comments_mixin.jira.resource_url = Mock(return_value="https://test.atlassian.net/rest/api/2/issue")
        comments_mixin.jira.post = Mock(return_value={
            "id": "10001",
            "body": "This is an internal comment",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        })

        # Call the method without visibility parameter (should use global setting)
        result = comments_mixin.add_comment("TEST-123", "Test internal comment")

        # Verify that the direct REST API was called with internal properties
        comments_mixin.jira.resource_url.assert_called_once_with("issue")
        comments_mixin.jira.post.assert_called_once_with(
            "https://test.atlassian.net/rest/api/2/issue/TEST-123/comment",
            json={
                "body": "*This* is _Jira_ formatted",
                "properties": [
                    {
                        "key": "sd.public.comment",
                        "value": {"internal": True}
                    }
                ]
            }
        )
        
        # Verify that the standard issue_add_comment was NOT called
        comments_mixin.jira.issue_add_comment.assert_not_called()
        
        # Verify the result
        assert result["id"] == "10001"
        assert result["body"] == "This is an internal comment"
        assert result["author"] == "John Doe"

    def test_add_comment_with_force_internal_comments_disabled(self, comments_mixin):
        """Test add_comment with force_internal_comments disabled (default behavior)."""
        # Ensure force_internal_comments is disabled
        comments_mixin.config.force_internal_comments = False
        
        # Setup mock response for standard method
        comments_mixin.jira.issue_add_comment.return_value = {
            "id": "10001",
            "body": "This is a public comment",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        }

        # Call the method
        result = comments_mixin.add_comment("TEST-123", "Test public comment")

        # Verify that the standard method was called
        comments_mixin.jira.issue_add_comment.assert_called_once_with(
            "TEST-123", "*This* is _Jira_ formatted"
        )
        
        # Verify that the direct REST API was NOT called
        if hasattr(comments_mixin.jira, 'post'):
            comments_mixin.jira.post.assert_not_called()
        
        # Verify the result
        assert result["id"] == "10001"
        assert result["body"] == "This is a public comment"
        assert result["author"] == "John Doe"

    def test_add_comment_with_explicit_internal_visibility(self, comments_mixin):
        """Test add_comment with explicit internal visibility parameter."""
        # Ensure force_internal_comments is disabled to test explicit parameter
        comments_mixin.config.force_internal_comments = False
        
        # Setup mock response for direct REST API call
        comments_mixin.jira.resource_url = Mock(return_value="https://test.atlassian.net/rest/api/2/issue")
        comments_mixin.jira.post = Mock(return_value={
            "id": "10001",
            "body": "This is an explicitly internal comment",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        })

        # Call the method with explicit internal visibility
        result = comments_mixin.add_comment("TEST-123", "Test internal comment", visibility="internal")

        # Verify that the direct REST API was called with internal properties
        comments_mixin.jira.resource_url.assert_called_once_with("issue")
        comments_mixin.jira.post.assert_called_once_with(
            "https://test.atlassian.net/rest/api/2/issue/TEST-123/comment",
            json={
                "body": "*This* is _Jira_ formatted",
                "properties": [
                    {
                        "key": "sd.public.comment",
                        "value": {"internal": True}
                    }
                ]
            }
        )
        
        # Verify that the standard issue_add_comment was NOT called
        comments_mixin.jira.issue_add_comment.assert_not_called()
        
        # Verify the result
        assert result["id"] == "10001"
        assert result["body"] == "This is an explicitly internal comment"
        assert result["author"] == "John Doe"

    def test_add_comment_with_explicit_public_visibility(self, comments_mixin):
        """Test add_comment with explicit public visibility parameter."""
        # Enable force_internal_comments to test that explicit public overrides it
        comments_mixin.config.force_internal_comments = True
        
        # Setup mock response for standard method
        comments_mixin.jira.issue_add_comment.return_value = {
            "id": "10001",
            "body": "This is an explicitly public comment",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        }

        # Call the method with explicit public visibility
        result = comments_mixin.add_comment("TEST-123", "Test public comment", visibility="public")

        # Verify that the standard method was called (not the internal API)
        comments_mixin.jira.issue_add_comment.assert_called_once_with(
            "TEST-123", "*This* is _Jira_ formatted"
        )
        
        # Verify the result
        assert result["id"] == "10001"
        assert result["body"] == "This is an explicitly public comment"
        assert result["author"] == "John Doe"

    def test_add_comment_with_case_insensitive_visibility(self, comments_mixin):
        """Test add_comment with case-insensitive visibility parameter."""
        # Ensure force_internal_comments is disabled
        comments_mixin.config.force_internal_comments = False
        
        # Setup mock response for direct REST API call
        comments_mixin.jira.resource_url = Mock(return_value="https://test.atlassian.net/rest/api/2/issue")
        comments_mixin.jira.post = Mock(return_value={
            "id": "10001",
            "body": "This is an internal comment",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        })

        # Call the method with uppercase internal visibility
        result = comments_mixin.add_comment("TEST-123", "Test internal comment", visibility="INTERNAL")

        # Verify that the direct REST API was called with internal properties
        comments_mixin.jira.resource_url.assert_called_once_with("issue")
        comments_mixin.jira.post.assert_called_once_with(
            "https://test.atlassian.net/rest/api/2/issue/TEST-123/comment",
            json={
                "body": "*This* is _Jira_ formatted",
                "properties": [
                    {
                        "key": "sd.public.comment",
                        "value": {"internal": True}
                    }
                ]
            }
        )
        
        # Verify the result
        assert result["id"] == "10001"
        assert result["body"] == "This is an internal comment"
        assert result["author"] == "John Doe"

    def test_add_comment_with_force_internal_and_explicit_public_override(self, comments_mixin):
        """Test that force_internal_comments setting cannot be overridden by explicit public visibility."""
        # Enable force_internal_comments
        comments_mixin.config.force_internal_comments = True
        
        # Setup mock response for direct REST API call (internal comment)
        comments_mixin.jira.resource_url = Mock(return_value="https://test.atlassian.net/rest/api/2/issue")
        comments_mixin.jira.post = Mock(return_value={
            "id": "10001",
            "body": "This is forced to be internal despite explicit public request",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        })

        # Call the method with explicit public visibility (should be ignored due to force setting)
        result = comments_mixin.add_comment("TEST-123", "Test public comment", visibility="public")

        # Verify that the direct REST API was called with internal properties (force overrides explicit public)
        comments_mixin.jira.resource_url.assert_called_once_with("issue")
        comments_mixin.jira.post.assert_called_once_with(
            "https://test.atlassian.net/rest/api/2/issue/TEST-123/comment",
            json={
                "body": "*This* is _Jira_ formatted",
                "properties": [
                    {
                        "key": "sd.public.comment",
                        "value": {"internal": True}
                    }
                ]
            }
        )
        
        # Verify that the standard issue_add_comment was NOT called
        comments_mixin.jira.issue_add_comment.assert_not_called()
        
        # Verify the result
        assert result["id"] == "10001"
        assert result["body"] == "This is forced to be internal despite explicit public request"
        assert result["author"] == "John Doe"

    def test_add_comment_with_none_visibility_respects_global_setting(self, comments_mixin):
        """Test that visibility=None respects the global force_internal_comments setting."""
        # Enable force_internal_comments
        comments_mixin.config.force_internal_comments = True
        
        # Setup mock response for direct REST API call
        comments_mixin.jira.resource_url = Mock(return_value="https://test.atlassian.net/rest/api/2/issue")
        comments_mixin.jira.post = Mock(return_value={
            "id": "10001",
            "body": "This should be internal due to global setting",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        })

        # Call the method with explicit None visibility
        result = comments_mixin.add_comment("TEST-123", "Test comment", visibility=None)

        # Verify that the direct REST API was called with internal properties
        comments_mixin.jira.resource_url.assert_called_once_with("issue")
        comments_mixin.jira.post.assert_called_once_with(
            "https://test.atlassian.net/rest/api/2/issue/TEST-123/comment",
            json={
                "body": "*This* is _Jira_ formatted",
                "properties": [
                    {
                        "key": "sd.public.comment",
                        "value": {"internal": True}
                    }
                ]
            }
        )
        
        # Verify that the standard issue_add_comment was NOT called
        comments_mixin.jira.issue_add_comment.assert_not_called()
        
        # Verify the result
        assert result["id"] == "10001"
        assert result["body"] == "This should be internal due to global setting"
        assert result["author"] == "John Doe"
