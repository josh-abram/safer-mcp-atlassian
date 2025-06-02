"""Module for Jira comment operations."""

import logging
from typing import Any

from ..utils import parse_date
from .client import JiraClient

logger = logging.getLogger("mcp-jira")


class CommentsMixin(JiraClient):
    """Mixin for Jira comment operations."""

    def get_issue_comments(
        self, issue_key: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Get comments for a specific issue.

        Args:
            issue_key: The issue key (e.g. 'PROJ-123')
            limit: Maximum number of comments to return

        Returns:
            List of comments with author, creation date, and content

        Raises:
            Exception: If there is an error getting comments
        """
        try:
            comments = self.jira.issue_get_comments(issue_key)

            if not isinstance(comments, dict):
                msg = f"Unexpected return value type from `jira.issue_get_comments`: {type(comments)}"
                logger.error(msg)
                raise TypeError(msg)

            processed_comments = []
            for comment in comments.get("comments", [])[:limit]:
                processed_comment = {
                    "id": comment.get("id"),
                    "body": self._clean_text(comment.get("body", "")),
                    "created": str(parse_date(comment.get("created"))),
                    "updated": str(parse_date(comment.get("updated"))),
                    "author": comment.get("author", {}).get("displayName", "Unknown"),
                }
                processed_comments.append(processed_comment)

            return processed_comments
        except Exception as e:
            logger.error(f"Error getting comments for issue {issue_key}: {str(e)}")
            raise Exception(f"Error getting comments: {str(e)}") from e

    def add_comment(self, issue_key: str, comment: str, visibility: str | None = None) -> dict[str, Any]:
        """
        Add a comment to an issue.

        Args:
            issue_key: The issue key (e.g. 'PROJ-123')
            comment: Comment text to add (in Markdown format)
            visibility: Comment visibility ('public' or 'internal'). If None, uses global force_internal_comments setting.

        Returns:
            The created comment details

        Raises:
            Exception: If there is an error adding the comment
        """
        try:
            # Convert Markdown to Jira's markup format
            jira_formatted_comment = self._markdown_to_jira(comment)

            # Determine if comment should be internal
            # When force_internal_comments is True, ALL comments must be internal
            if self.config.force_internal_comments:
                should_be_internal = True
            elif visibility is None:
                # No explicit visibility specified and no forcing, default to public
                should_be_internal = False
            elif visibility.lower() == "internal":
                should_be_internal = True
            elif visibility.lower() == "public":
                should_be_internal = False
            else:
                # Invalid visibility value, default to internal
                should_be_internal = True

            # Check if we need to make internal comments
            if should_be_internal:
                # Use REST API directly to add properties for internal comments
                comment_data = {
                    "body": jira_formatted_comment,
                    "properties": [
                        {
                            "key": "sd.public.comment",
                            "value": {"internal": True}
                        }
                    ]
                }
                
                # Make direct REST API call
                base_url = self.jira.resource_url("issue")
                url = f"{base_url}/{issue_key}/comment"
                result = self.jira.post(url, json=comment_data)
            else:
                # Use the standard method for public comments
                result = self.jira.issue_add_comment(issue_key, jira_formatted_comment)

            if not isinstance(result, dict):
                msg = f"Unexpected return value type from comment API: {type(result)}"
                logger.error(msg)
                raise TypeError(msg)

            return {
                "id": result.get("id"),
                "body": self._clean_text(result.get("body", "")),
                "created": str(parse_date(result.get("created"))),
                "author": result.get("author", {}).get("displayName", "Unknown"),
            }
        except Exception as e:
            logger.error(f"Error adding comment to issue {issue_key}: {str(e)}")
            raise Exception(f"Error adding comment: {str(e)}") from e

    def _markdown_to_jira(self, markdown_text: str) -> str:
        """
        Convert Markdown syntax to Jira markup syntax.

        This method uses the TextPreprocessor implementation for consistent
        conversion between Markdown and Jira markup.

        Args:
            markdown_text: Text in Markdown format

        Returns:
            Text in Jira markup format
        """
        if not markdown_text:
            return ""

        # Use the existing preprocessor
        try:
            return self.preprocessor.markdown_to_jira(markdown_text)
        except Exception as e:
            logger.warning(f"Error converting markdown to Jira format: {str(e)}")
            # Return the original text if conversion fails
            return markdown_text
