import logging
from typing import Annotated, List, Optional
from .base_agent import BaseAgent
from ..web_input import get_user_input
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.attribute_tree import AttributeTree

# Set up logging
logger = logging.getLogger(__name__)


class GitHubAPIAnnotation(APIAnnotationBase):
    """Policy annotation for GitHub Issue operations with hierarchy:
    GitHub:Owner -> GitHub:Repo -> GitHub:Issue
    """

    attributes_schema = {
        'GitHub:Owner': {
            'description': 'The owner (user or organization) of the repository',
            'examples': ['microsoft', 'octocat', 'torvalds']
        },
        'GitHub:Repo': {
            'description': 'The repository name under the specified owner',
            'examples': ['vscode', 'hello-world', 'linux']
        },
        'GitHub:Issue': {
            'description': 'A specific issue number within the repository; "*" wildcard when not targeting a specific issue',
            'examples': ['1', '42', '*']
        }
    }

    def __init__(self):
        super().__init__(
            "GitHub",
            {
                'granular_data': [
                    AttributeTree('GitHub:Owner', [
                        AttributeTree('GitHub:Repo', [
                            AttributeTree('GitHub:Issue')
                        ])
                    ])
                ],
                'data_access': [
                    AttributeTree('Read'),
                    AttributeTree('Write'),
                    AttributeTree('Create')
                ]
            },
            self.attributes_schema
        )

    def get_hierarchy(self, endpoint_name, kwargs, use_wildcard):
        owner = kwargs.get('owner', '*')
        repo = kwargs.get('repo', '*')
        if endpoint_name in ('update_issue', 'get_issue'):
            issue = kwargs.get('issue_number', '*')
        else:
            # create_issue (new issue not yet numbered) and list_issues (multiple issues)
            issue = '*'

        if use_wildcard:
            owner_part = 'GitHub:Owner(*)'
            repo_part = 'GitHub:Repo(*)'
            issue_part = 'GitHub:Issue(*)'
        else:
            owner_part = f'GitHub:Owner({owner})'
            repo_part = f'GitHub:Repo({repo})'
            issue_part = f'GitHub:Issue({issue})'

        return '::'.join([owner_part, repo_part, issue_part])

    def get_access_level(self, endpoint_name):
        if endpoint_name == 'create_issue':
            return 'Create'
        if endpoint_name == 'update_issue':
            return 'Write'
        return 'Read'

    def get_time_period(self, *args, **kwargs):  # Not used for GitHub issues currently
        return 'Current'

    def generate_attributes(self, kwargs, endpoint_name, wildcard):
        return [{
            'granular_data': self.get_hierarchy(endpoint_name, kwargs, wildcard),
            'data_access': self.get_access_level(endpoint_name)
        }]


class GitHubAPI:
    def __init__(self, policy_system):
        self.annotation = GitHubAPIAnnotation()
        self.policy_system = policy_system

    @GitHubAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @GitHubAPIAnnotation.schema
    def get_attributes_schema(self):
        return self.annotation.attributes_schema

    @GitHubAPIAnnotation.annotate
    def create_issue(self, *args, **kwargs):
        # Placeholder implementation; real implementation would call GitHub API
        return "done"

    @GitHubAPIAnnotation.annotate
    def list_issues(self, *args, **kwargs):
        # Placeholder implementation
        return "done"

    @GitHubAPIAnnotation.annotate
    def update_issue(self, *args, **kwargs):
        # Placeholder implementation
        return "done"

    @GitHubAPIAnnotation.annotate
    def get_issue(self, *args, **kwargs):
        # Placeholder implementation
        return "done"


class GitHubAgent(BaseAgent):
    """GitHub agent for managing repository issues"""

    def __init__(self, model_client, policy_system):
        system_message = (
            "You are a GitHub issues agent. Use the provided tools to create, list, or update issues. "
            "When targeting a specific issue use the update tool. Use list only when you need a collection. "
            "Return 'done' once the task is completed."
        )

        policy_system.register_api(GitHubAPI)
        self.github_api = GitHubAPI(policy_system)

        tools = [
            self.github_create_issue,
            self.github_list_issues,
            self.github_update_issue,
            self.github_get_issue,
            get_user_input
        ]

        super().__init__("GitHub", system_message, tools, model_client)

    # ---------------- Tool Methods ---------------- #
    async def github_create_issue(
        self,
        owner: Annotated[str, "Repository owner"],
        repo: Annotated[str, "Repository name"],
        title: Annotated[str, "Issue title"],
        body: Annotated[Optional[str], "Issue body content"] = None,
        assignees: Annotated[Optional[List[str]], "Usernames to assign"] = None,
        labels: Annotated[Optional[List[str]], "Labels to apply"] = None,
        milestone: Annotated[Optional[int], "Milestone number"] = None,
        type: Annotated[Optional[str], "Issue type"] = None,
    ) -> str:
        """Open a new issue in the specified repository"""
        logger.info(
            "Creating issue owner=%s repo=%s title=%s assignees=%s labels=%s milestone=%s type=%s",
            owner, repo, title, assignees, labels, milestone, type
        )
        return self.github_api.create_issue(
            owner=owner, repo=repo, title=title, body=body,
            assignees=assignees, labels=labels, milestone=milestone, type=type
        )

    async def github_list_issues(
        self,
        owner: Annotated[str, "Repository owner"],
        repo: Annotated[str, "Repository name"],
        state: Annotated[Optional[str], "Filter by state"] = None,
        labels: Annotated[Optional[List[str]], "Filter by labels"] = None,
        since: Annotated[Optional[str], "Filter by date (ISO 8601)"] = None,
        perPage: Annotated[Optional[int], "Results per page (1-100)"] = None,
        after: Annotated[Optional[str], "Cursor for pagination"] = None,
        orderBy: Annotated[Optional[str], "Order issues by field (requires direction)"] = None,
        direction: Annotated[Optional[str], "Order direction (requires orderBy)"] = None,
    ) -> str:
        """List issues for a repository"""
        logger.info(
            "Listing issues owner=%s repo=%s state=%s labels=%s since=%s perPage=%s after=%s orderBy=%s direction=%s",
            owner, repo, state, labels, since, perPage, after, orderBy, direction
        )
        return self.github_api.list_issues(
            owner=owner, repo=repo, state=state, labels=labels, since=since,
            perPage=perPage, after=after, orderBy=orderBy, direction=direction
        )

    async def github_update_issue(
        self,
        owner: Annotated[str, "Repository owner"],
        repo: Annotated[str, "Repository name"],
        issue_number: Annotated[int, "Issue number to update"],
        title: Annotated[Optional[str], "New title" ] = None,
        body: Annotated[Optional[str], "New description" ] = None,
        state: Annotated[Optional[str], "New state" ] = None,
        assignees: Annotated[Optional[List[str]], "New assignees" ] = None,
        labels: Annotated[Optional[List[str]], "New labels" ] = None,
        milestone: Annotated[Optional[int], "New milestone number" ] = None,
        type: Annotated[Optional[str], "New issue type" ] = None,
    ) -> str:
        """Update an existing issue"""
        logger.info(
            "Updating issue owner=%s repo=%s issue_number=%s title=%s state=%s assignees=%s labels=%s milestone=%s type=%s",
            owner, repo, issue_number, title, state, assignees, labels, milestone, type
        )
        return self.github_api.update_issue(
            owner=owner, repo=repo, issue_number=issue_number, title=title, body=body,
            state=state, assignees=assignees, labels=labels, milestone=milestone, type=type
        )

    async def github_get_issue(
        self,
        owner: Annotated[str, "Repository owner"],
        repo: Annotated[str, "Repository name"],
        issue_number: Annotated[int, "The issue number"],
    ) -> str:
        """Get details of a specific issue"""
        logger.info(
            "Getting issue owner=%s repo=%s issue_number=%s",
            owner, repo, issue_number
        )
        return self.github_api.get_issue(owner=owner, repo=repo, issue_number=issue_number)
