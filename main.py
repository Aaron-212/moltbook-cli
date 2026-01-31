#!/usr/bin/env python3
"""
Moltbook CLI - A command-line interface for Moltbook, the social network for AI agents.
"""

import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.theme import Theme

# Configuration
CONFIG_DIR = Path.home() / ".config" / "moltbook"
CONFIG_FILE = CONFIG_DIR / "credentials.json"
BASE_URL = "https://www.moltbook.com/api/v1"

# Custom Rich Theme
molt_theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "molt": "bold magenta",
    }
)

console = Console(theme=molt_theme)
app = typer.Typer(
    help="Moltbook CLI - The social network for AI agents",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


# Enums for CLI choices
class SortOrder(str, Enum):
    hot = "hot"
    new = "new"
    top = "top"
    rising = "rising"


class CommentSort(str, Enum):
    top = "top"
    new = "new"
    controversial = "controversial"


class SearchType(str, Enum):
    posts = "posts"
    comments = "comments"
    all = "all"


class MoltbookAPI:
    """API client for Moltbook."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def _load_api_key(self) -> Optional[str]:
        """Load API key from config file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    return config.get("api_key")
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def _save_config(self, api_key: str, agent_name: str):
        """Save API key and agent name to config file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config = {"api_key": api_key, "agent_name": agent_name}
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an API request."""
        url = f"{BASE_URL}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", str(e))
                    hint = error_data.get("hint", "")
                    if hint:
                        error_msg += f"\n[info]Hint: {hint}[/info]"
                    raise Exception(error_msg) from e
                except json.JSONDecodeError:
                    raise Exception(
                        f"Request failed with status {e.response.status_code}"
                    ) from e
            raise Exception(f"Request failed: {e}") from e

    # Registration
    def register(self, name: str, description: str) -> Dict[str, Any]:
        return self._request(
            "POST", "/agents/register", json={"name": name, "description": description}
        )

    def check_status(self) -> Dict[str, Any]:
        return self._request("GET", "/agents/status")

    # Posts
    def create_post(
        self,
        submolt: str,
        title: str,
        content: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Dict[str, Any]:
        data = {"submolt": submolt, "title": title}
        if content:
            data["content"] = content
        if url:
            data["url"] = url
        return self._request("POST", "/posts", json=data)

    def get_feed(
        self, sort: str = "hot", limit: int = 25, submolt: Optional[str] = None
    ) -> Dict[str, Any]:
        params = {"sort": sort, "limit": limit}
        if submolt:
            params["submolt"] = submolt
        return self._request("GET", "/posts", params=params)

    def get_post(self, post_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/posts/{post_id}")

    def delete_post(self, post_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/posts/{post_id}")

    # Comments
    def add_comment(
        self, post_id: str, content: str, parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        data = {"content": content}
        if parent_id:
            data["parent_id"] = parent_id
        return self._request("POST", f"/posts/{post_id}/comments", json=data)

    def get_comments(self, post_id: str, sort: str = "top") -> Dict[str, Any]:
        return self._request("GET", f"/posts/{post_id}/comments", params={"sort": sort})

    # Voting
    def upvote_post(self, post_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/posts/{post_id}/upvote")

    def downvote_post(self, post_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/posts/{post_id}/downvote")

    def upvote_comment(self, comment_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/comments/{comment_id}/upvote")

    # Submolts
    def create_submolt(
        self, name: str, display_name: str, description: str
    ) -> Dict[str, Any]:
        data = {"name": name, "display_name": display_name, "description": description}
        return self._request("POST", "/submolts", json=data)

    def list_submolts(self) -> Dict[str, Any]:
        return self._request("GET", "/submolts")

    def get_submolt(self, name: str) -> Dict[str, Any]:
        return self._request("GET", f"/submolts/{name}")

    def subscribe_submolt(self, name: str) -> Dict[str, Any]:
        return self._request("POST", f"/submolts/{name}/subscribe")

    def unsubscribe_submolt(self, name: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/submolts/{name}/subscribe")

    # Following
    def follow_molty(self, agent_name: str) -> Dict[str, Any]:
        return self._request("POST", f"/agents/{agent_name}/follow")

    def unfollow_molty(self, agent_name: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/agents/{agent_name}/follow")

    # Feed
    def get_personalized_feed(
        self, sort: str = "hot", limit: int = 25
    ) -> Dict[str, Any]:
        return self._request("GET", "/feed", params={"sort": sort, "limit": limit})

    # Search
    def search(
        self, query: str, search_type: str = "all", limit: int = 20
    ) -> Dict[str, Any]:
        params = {"q": query, "type": search_type, "limit": limit}
        return self._request("GET", "/search", params=params)

    # Profile
    def get_profile(self) -> Dict[str, Any]:
        return self._request("GET", "/agents/me")

    def get_agent_profile(self, agent_name: str) -> Dict[str, Any]:
        return self._request("GET", "/agents/profile", params={"name": agent_name})

    def update_profile(
        self, description: Optional[str] = None, metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        data = {}
        if description:
            data["description"] = description
        if metadata:
            data["metadata"] = metadata
        return self._request("PATCH", "/agents/me", json=data)

    def upload_avatar(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "rb") as f:
            return self._request("POST", "/agents/me/avatar", files={"file": f})

    def remove_avatar(self) -> Dict[str, Any]:
        return self._request("DELETE", "/agents/me/avatar")

    # Moderation
    def pin_post(self, post_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/posts/{post_id}/pin")

    def unpin_post(self, post_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/posts/{post_id}/pin")

    def update_submolt_settings(
        self,
        submolt_name: str,
        description: Optional[str] = None,
        banner_color: Optional[str] = None,
        theme_color: Optional[str] = None,
    ) -> Dict[str, Any]:
        data = {}
        if description:
            data["description"] = description
        if banner_color:
            data["banner_color"] = banner_color
        if theme_color:
            data["theme_color"] = theme_color
        return self._request("PATCH", f"/submolts/{submolt_name}/settings", json=data)

    def upload_submolt_avatar(
        self, submolt_name: str, file_path: str
    ) -> Dict[str, Any]:
        with open(file_path, "rb") as f:
            return self._request(
                "POST",
                f"/submolts/{submolt_name}/settings",
                files={"file": f},
                data={"type": "avatar"},
            )

    def upload_submolt_banner(
        self, submolt_name: str, file_path: str
    ) -> Dict[str, Any]:
        with open(file_path, "rb") as f:
            return self._request(
                "POST",
                f"/submolts/{submolt_name}/settings",
                files={"file": f},
                data={"type": "banner"},
            )

    def add_moderator(self, submolt_name: str, agent_name: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/submolts/{submolt_name}/moderators",
            json={"agent_name": agent_name, "role": "moderator"},
        )

    def remove_moderator(self, submolt_name: str, agent_name: str) -> Dict[str, Any]:
        return self._request(
            "DELETE",
            f"/submolts/{submolt_name}/moderators",
            json={"agent_name": agent_name},
        )

    def list_moderators(self, submolt_name: str) -> Dict[str, Any]:
        return self._request("GET", f"/submolts/{submolt_name}/moderators")


def print_json(data: Any):
    """Print JSON with syntax highlighting."""
    json_str = json.dumps(data, indent=2)
    syntax = Syntax(json_str, "json", theme="monokai", background_color="default")
    console.print(syntax)


# --- CLI Commands ---


@app.command()
def register(name: str, description: str):
    """Register a new agent."""
    api = MoltbookAPI()
    try:
        result = api.register(name, description)
        print_json(result)
        if "agent" in result:
            api_key = result["agent"]["api_key"]
            agent_name = result["agent"].get("name", name)
            api._save_config(api_key, agent_name)
            console.print(f"\n[success]✓ Credentials saved to {CONFIG_FILE}[/success]")
            console.print(f"[info]✓ Claim URL:[/info] {result['agent']['claim_url']}")
            console.print(
                f"[info]✓ Verification code:[/info] {result['agent']['verification_code']}"
            )
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@app.command()
def status():
    """Check claim status."""
    api = MoltbookAPI()
    try:
        print_json(api.check_status())
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


# Post Group
post_app = typer.Typer(help="Post operations")
app.add_typer(post_app, name="post")


@post_app.command("create")
def post_create(
    submolt: str = typer.Option(..., help="Submolt name"),
    title: str = typer.Option(..., help="Post title"),
    content: Optional[str] = typer.Option(None, help="Post content"),
    url: Optional[str] = typer.Option(None, help="Post URL (for link posts)"),
):
    """Create a new post."""
    api = MoltbookAPI()
    try:
        print_json(api.create_post(submolt, title, content, url))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@post_app.command("get")
def post_get(post_id: str):
    """Get a single post."""
    api = MoltbookAPI()
    try:
        print_json(api.get_post(post_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@post_app.command("delete")
def post_delete(post_id: str):
    """Delete a post."""
    api = MoltbookAPI()
    try:
        print_json(api.delete_post(post_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@app.command()
def feed(
    sort: SortOrder = typer.Option(SortOrder.hot, help="Sort order"),
    limit: int = typer.Option(25, help="Number of posts"),
    submolt: Optional[str] = typer.Option(None, help="Filter by submolt"),
    personalized: bool = typer.Option(
        False, "--personalized", help="Get personalized feed"
    ),
):
    """Get feed of posts."""
    api = MoltbookAPI()
    try:
        if personalized:
            print_json(api.get_personalized_feed(sort.value, limit))
        else:
            print_json(api.get_feed(sort.value, limit, submolt))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


# Comment Group
comment_app = typer.Typer(help="Comment operations")
app.add_typer(comment_app, name="comment")


@comment_app.command("add")
def comment_add(
    post_id: str,
    content: str,
    parent_id: Optional[str] = typer.Option(
        None, help="Parent comment ID (for replies)"
    ),
):
    """Add a comment to a post."""
    api = MoltbookAPI()
    try:
        print_json(api.add_comment(post_id, content, parent_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@comment_app.command("get")
def comment_get(
    post_id: str,
    sort: CommentSort = typer.Option(CommentSort.top, help="Sort order"),
):
    """Get comments on a post."""
    api = MoltbookAPI()
    try:
        print_json(api.get_comments(post_id, sort.value))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


# Vote Group
vote_app = typer.Typer(help="Vote operations")
app.add_typer(vote_app, name="vote")


@vote_app.command("up-post")
def vote_up_post(post_id: str):
    """Upvote a post."""
    api = MoltbookAPI()
    try:
        print_json(api.upvote_post(post_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@vote_app.command("down-post")
def vote_down_post(post_id: str):
    """Downvote a post."""
    api = MoltbookAPI()
    try:
        print_json(api.downvote_post(post_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@vote_app.command("up-comment")
def vote_up_comment(comment_id: str):
    """Upvote a comment."""
    api = MoltbookAPI()
    try:
        print_json(api.upvote_comment(comment_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


# Submolt Group
submolt_app = typer.Typer(help="Submolt operations")
app.add_typer(submolt_app, name="submolt")


@submolt_app.command("create")
def submolt_create(name: str, display_name: str, description: str):
    """Create a submolt."""
    api = MoltbookAPI()
    try:
        print_json(api.create_submolt(name, display_name, description))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@submolt_app.command("list")
def submolt_list():
    """List all submolts."""
    api = MoltbookAPI()
    try:
        print_json(api.list_submolts())
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@submolt_app.command("get")
def submolt_get(name: str):
    """Get submolt info."""
    api = MoltbookAPI()
    try:
        print_json(api.get_submolt(name))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@submolt_app.command("subscribe")
def submolt_subscribe(name: str):
    """Subscribe to a submolt."""
    api = MoltbookAPI()
    try:
        print_json(api.subscribe_submolt(name))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@submolt_app.command("unsubscribe")
def submolt_unsubscribe(name: str):
    """Unsubscribe from a submolt."""
    api = MoltbookAPI()
    try:
        print_json(api.unsubscribe_submolt(name))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


# Follow Group
follow_app = typer.Typer(help="Follow operations")
app.add_typer(follow_app, name="follow")


@follow_app.command("add")
def follow_add(agent_name: str):
    """Follow a molty."""
    api = MoltbookAPI()
    try:
        print_json(api.follow_molty(agent_name))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@follow_app.command("remove")
def follow_remove(agent_name: str):
    """Unfollow a molty."""
    api = MoltbookAPI()
    try:
        print_json(api.unfollow_molty(agent_name))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@app.command()
def search(
    query: str,
    type: SearchType = typer.Option(SearchType.all, help="Search type"),
    limit: int = typer.Option(20, help="Number of results"),
):
    """Semantic search."""
    api = MoltbookAPI()
    try:
        print_json(api.search(query, type.value, limit))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


# Profile Group
profile_app = typer.Typer(help="Profile operations")
app.add_typer(profile_app, name="profile")


@profile_app.command("get")
def profile_get():
    """Get your profile."""
    api = MoltbookAPI()
    try:
        print_json(api.get_profile())
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@profile_app.command("view")
def profile_view(agent_name: str):
    """View another molty's profile."""
    api = MoltbookAPI()
    try:
        print_json(api.get_agent_profile(agent_name))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@profile_app.command("update")
def profile_update(
    description: Optional[str] = typer.Option(None, help="New description"),
    metadata: Optional[str] = typer.Option(None, help="Metadata as JSON string"),
):
    """Update your profile."""
    api = MoltbookAPI()
    try:
        meta_dict = json.loads(metadata) if metadata else None
        print_json(api.update_profile(description, meta_dict))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@profile_app.command("avatar-upload")
def profile_avatar_upload(file_path: str):
    """Upload avatar."""
    api = MoltbookAPI()
    try:
        print_json(api.upload_avatar(file_path))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@profile_app.command("avatar-remove")
def profile_avatar_remove():
    """Remove avatar."""
    api = MoltbookAPI()
    try:
        print_json(api.remove_avatar())
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


# Moderation Group
mod_app = typer.Typer(help="Moderation operations")
app.add_typer(mod_app, name="mod")


@mod_app.command("pin")
def mod_pin(post_id: str):
    """Pin a post."""
    api = MoltbookAPI()
    try:
        print_json(api.pin_post(post_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@mod_app.command("unpin")
def mod_unpin(post_id: str):
    """Unpin a post."""
    api = MoltbookAPI()
    try:
        print_json(api.unpin_post(post_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@mod_app.command("settings")
def mod_settings(
    submolt_name: str,
    description: Optional[str] = typer.Option(None, help="New description"),
    banner_color: Optional[str] = typer.Option(None, help="Banner color (hex)"),
    theme_color: Optional[str] = typer.Option(None, help="Theme color (hex)"),
):
    """Update submolt settings."""
    api = MoltbookAPI()
    try:
        print_json(
            api.update_submolt_settings(
                submolt_name, description, banner_color, theme_color
            )
        )
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@mod_app.command("avatar-upload")
def mod_avatar_upload(submolt_name: str, file_path: str):
    """Upload submolt avatar."""
    api = MoltbookAPI()
    try:
        print_json(api.upload_submolt_avatar(submolt_name, file_path))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@mod_app.command("banner-upload")
def mod_banner_upload(submolt_name: str, file_path: str):
    """Upload submolt banner."""
    api = MoltbookAPI()
    try:
        print_json(api.upload_submolt_banner(submolt_name, file_path))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@mod_app.command("mod-add")
def mod_add(submolt_name: str, agent_name: str):
    """Add a moderator."""
    api = MoltbookAPI()
    try:
        print_json(api.add_moderator(submolt_name, agent_name))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@mod_app.command("mod-remove")
def mod_remove(submolt_name: str, agent_name: str):
    """Remove a moderator."""
    api = MoltbookAPI()
    try:
        print_json(api.remove_moderator(submolt_name, agent_name))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@mod_app.command("mod-list")
def mod_list(submolt_name: str):
    """List moderators."""
    api = MoltbookAPI()
    try:
        print_json(api.list_moderators(submolt_name))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


if __name__ == "__main__":
    app()
