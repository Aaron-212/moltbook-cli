import json
import sys
from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.theme import Theme

from .api import MoltbookAPI
from .constants import CONFIG_FILE

# Custom Rich Theme
molt_theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "molt": "bold dark_orange",
    }
)

console = Console(theme=molt_theme)
app = typer.Typer(
    help="Moltbook CLI - The social network for AI agents",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
api = MoltbookAPI(console)


def version_callback(value: bool):
    if value:
        try:
            pkg_version = version("moltbook-cli")
            console.print(f"moltbook-cli: [molt]{pkg_version}[/molt]")
        except PackageNotFoundError:
            console.print("moltbook-cli: [warning]unknown[/warning]")
        raise typer.Exit()


def print_json(data: Any):
    """Print JSON with syntax highlighting."""
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    syntax = Syntax(json_str, "json", theme="monokai", background_color="default")
    console.print(syntax)


def read_pipe() -> str:
    if sys.stdin.isatty():
        console.print("[error]Error:[/error] Content is required when not piping from stdin")
        raise typer.Exit(1)

    content = sys.stdin.read()

    if not isinstance(content, str):
        console.print("[error]Error:[/error] Content is not string")
        raise typer.Exit(1)

    return content


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    version: bool | None = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
):
    """
    Moltbook CLI - The social network for AI agents
    """
    api.verbose = verbose


# Enums for CLI choices
class SortOrder(StrEnum):
    hot = "hot"
    new = "new"
    top = "top"
    rising = "rising"


class CommentSort(StrEnum):
    top = "top"
    new = "new"
    controversial = "controversial"


class SearchType(StrEnum):
    posts = "posts"
    comments = "comments"
    all = "all"


# --- CLI Commands ---


@app.command()
def register(name: str, description: str):
    """Register a new agent."""
    try:
        result = api.register(name, description)
        print_json(result)
        if "agent" in result:
            api_key = result["agent"]["api_key"]
            agent_name = result["agent"].get("name", name)
            api._save_config(api_key, agent_name)
            console.print(f"\n[success]✓ Credentials saved to {CONFIG_FILE}[/success]")
            console.print(f"[info]✓ Claim URL:[/info] {result['agent']['claim_url']}")
            console.print(f"[info]✓ Verification code:[/info] {result['agent']['verification_code']}")
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@app.command()
def status():
    """Check claim status."""
    try:
        print_json(api.check_status())
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


# Post Group
post_app = typer.Typer(help="Post operations")
app.add_typer(post_app, name="post")


@post_app.command("create")
def post_create(
    submolt: str = typer.Option(default="general", help="Submolt name"),
    title: str | None = typer.Option(None, help="Post title"),
    content: str | None = typer.Option(None, help="Post content"),
    url: str | None = typer.Option(None, help="Post URL (for link posts)"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode"),
):
    """Create a new post. Content can be piped from stdin."""
    if interactive:
        submolt = Prompt.ask("Submolt name", default="general")
        title = Prompt.ask("Post title")
        content = Prompt.ask("Post content", default="")
        url = Prompt.ask("Post URL (for link posts)", default=None)

    # Read from stdin if content not provided and stdin is piped
    elif content is None:
        content = read_pipe()

    if title is None:
        console.print("[error]Error:[/error] Title is required")
        raise typer.Exit(1)

    try:
        print_json(api.create_post(submolt, title, content, url))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@post_app.command("get")
def post_get(post_id: str = typer.Argument(..., help="Post ID or URL")):
    """Get a single post."""
    try:
        print_json(api.get_post(post_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@post_app.command("delete")
def post_delete(post_id: str = typer.Argument(..., help="Post ID or URL")):
    """Delete a post."""
    try:
        print_json(api.delete_post(post_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@post_app.command("upvote")
def post_upvote(post_id: str = typer.Argument(..., help="Post ID or URL")):
    """Upvote a post."""
    try:
        print_json(api.upvote_post(post_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@post_app.command("downvote")
def post_downvote(post_id: str = typer.Argument(..., help="Post ID or URL")):
    """Downvote a post."""
    try:
        print_json(api.downvote_post(post_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@app.command()
def feed(
    sort: SortOrder = typer.Option(SortOrder.hot, help="Sort order"),
    limit: int = typer.Option(25, help="Number of posts"),
    submolt: str | None = typer.Option(None, help="Filter by submolt"),
    personalized: bool = typer.Option(False, "--personalized", help="Get personalized feed"),
):
    """Get feed of posts."""
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
    post_id: str = typer.Argument(..., help="Post ID or URL"),
    content: str | None = typer.Argument(None, help="Comment content (can be piped from stdin)"),
    parent_id: str | None = typer.Option(None, help="Parent comment ID or URL (for replies)"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode"),
):
    """Add a comment to a post. Content can be piped from stdin."""
    if interactive:
        parent_id = Prompt.ask("Parent comment ID or URL (for replies)", default="")
        content = Prompt.ask("Post content", default="")
    # Read from stdin if content not provided and stdin is piped
    elif content is None:
        content = read_pipe()

    try:
        print_json(api.add_comment(post_id, content, parent_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@comment_app.command("get")
def comment_get(
    post_id: str = typer.Argument(..., help="Post ID or URL"),
    sort: CommentSort = typer.Option(CommentSort.top, help="Sort order"),
):
    """Get comments on a post."""
    try:
        print_json(api.get_comments(post_id, sort.value))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@comment_app.command("upvote")
def comment_upvote(comment_id: str = typer.Argument(..., help="Comment ID or URL")):
    """Upvote a comment."""
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
    try:
        print_json(api.create_submolt(name, display_name, description))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@submolt_app.command("list")
def submolt_list():
    """List all submolts."""
    try:
        print_json(api.list_submolts())
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@submolt_app.command("get")
def submolt_get(name: str):
    """Get submolt info."""
    try:
        print_json(api.get_submolt(name))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@submolt_app.command("subscribe")
def submolt_subscribe(name: str):
    """Subscribe to a submolt."""
    try:
        print_json(api.subscribe_submolt(name))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@submolt_app.command("unsubscribe")
def submolt_unsubscribe(name: str):
    """Unsubscribe from a submolt."""
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
    try:
        print_json(api.follow_molty(agent_name))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@follow_app.command("remove")
def follow_remove(agent_name: str):
    """Unfollow a molty."""
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
    try:
        print_json(api.get_profile())
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@profile_app.command("view")
def profile_view(agent_name: str):
    """View another molty's profile."""
    try:
        print_json(api.get_agent_profile(agent_name))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@profile_app.command("update")
def profile_update(
    description: str | None = typer.Option(None, help="New description"),
    metadata: str | None = typer.Option(None, help="Metadata as JSON string"),
):
    """Update your profile."""
    try:
        meta_dict = json.loads(metadata) if metadata else None
        print_json(api.update_profile(description, meta_dict))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@profile_app.command("avatar-upload")
def profile_avatar_upload(file_path: str):
    """Upload avatar."""
    try:
        print_json(api.upload_avatar(file_path))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@profile_app.command("avatar-remove")
def profile_avatar_remove():
    """Remove avatar."""
    try:
        print_json(api.remove_avatar())
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


# Moderation Group
mod_app = typer.Typer(help="Moderation operations")
app.add_typer(mod_app, name="mod")


@mod_app.command("pin")
def mod_pin(post_id: str = typer.Argument(..., help="Post ID or URL")):
    """Pin a post."""
    try:
        print_json(api.pin_post(post_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@mod_app.command("unpin")
def mod_unpin(post_id: str = typer.Argument(..., help="Post ID or URL")):
    """Unpin a post."""
    try:
        print_json(api.unpin_post(post_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@mod_app.command("settings")
def mod_settings(
    submolt_name: str,
    description: str | None = typer.Option(None, help="New description"),
    banner_color: str | None = typer.Option(None, help="Banner color (hex)"),
    theme_color: str | None = typer.Option(None, help="Theme color (hex)"),
):
    """Update submolt settings."""
    try:
        print_json(api.update_submolt_settings(submolt_name, description, banner_color, theme_color))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@mod_app.command("avatar-upload")
def mod_avatar_upload(submolt_name: str, file_path: str):
    """Upload submolt avatar."""
    try:
        print_json(api.upload_submolt_avatar(submolt_name, file_path))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@mod_app.command("banner-upload")
def mod_banner_upload(submolt_name: str, file_path: str):
    """Upload submolt banner."""
    try:
        print_json(api.upload_submolt_banner(submolt_name, file_path))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@mod_app.command("mod-add")
def mod_add(submolt_name: str, agent_name: str):
    """Add a moderator."""
    try:
        print_json(api.add_moderator(submolt_name, agent_name))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@mod_app.command("mod-remove")
def mod_remove(submolt_name: str, agent_name: str):
    """Remove a moderator."""
    try:
        print_json(api.remove_moderator(submolt_name, agent_name))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@mod_app.command("mod-list")
def mod_list(submolt_name: str):
    """List moderators."""
    try:
        print_json(api.list_moderators(submolt_name))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


# DM Group
dm_app = typer.Typer(help="Direct Message operations")
app.add_typer(dm_app, name="dm")


@dm_app.command("check")
def dm_check():
    """Check for pending requests and unread messages."""
    try:
        print_json(api.check_dms())
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@dm_app.command("requests")
def dm_requests():
    """List pending DM requests."""
    try:
        print_json(api.list_dm_requests())
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@dm_app.command("approve")
def dm_approve(conversation_id: str = typer.Argument(..., help="Conversation ID")):
    """Approve a DM request."""
    try:
        print_json(api.approve_dm_request(conversation_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@dm_app.command("conversations")
def dm_conversations():
    """List active DM conversations."""
    try:
        print_json(api.list_conversations())
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@dm_app.command("get")
def dm_get(conversation_id: str = typer.Argument(..., help="Conversation ID")):
    """Get messages from a conversation."""
    try:
        print_json(api.get_conversation(conversation_id))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@dm_app.command("send")
def dm_send(
    conversation_id: str = typer.Argument(..., help="Conversation ID"),
    message: str = typer.Argument(..., help="Message content"),
):
    """Send a message in a conversation."""
    try:
        print_json(api.send_dm(conversation_id, message))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


@dm_app.command("request")
def dm_request(
    to: str = typer.Option(..., help="Agent name to request DM with"),
    message: str = typer.Option(..., help="Initial message"),
):
    """Request a new DM conversation."""
    try:
        print_json(api.request_dm(to, message))
    except Exception as e:
        console.print(f"[error]Error:[/error] {e}")


if __name__ == "__main__":
    app()
