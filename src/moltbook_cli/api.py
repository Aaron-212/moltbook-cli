import json
from typing import Any

import requests
from rich.console import Console

from .constants import BASE_URL, CONFIG_DIR, CONFIG_FILE


def extract_id(input_str: str) -> str:
    """Extract ID from a URL or return the ID as is."""
    if input_str.startswith("http"):
        for path_segment in ["/post/", "/comment/"]:
            if path_segment in input_str:
                return input_str.split(path_segment)[-1].split("?")[0].split("#")[0].rstrip("/")
    return input_str


class MoltbookAPI:
    """API client for Moltbook."""

    api_key: str | None = None
    session: requests.Session
    _verbose: bool = False
    console: Console

    def __init__(self, console: Console, api_key: str | None = None, verbose: bool = False):
        self.api_key = api_key or self._load_api_key()
        self.session = requests.Session()
        self.console = console
        self.session.headers.update({"User-Agent": "moltbook-cli/0.0.1"})
        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

        # Set verbose last to trigger the property setter if it's True
        self.verbose = verbose

    @property
    def verbose(self) -> bool:
        return self._verbose

    @verbose.setter
    def verbose(self, value: bool):
        old_value = self._verbose
        self._verbose = value
        if value and not old_value:
            if self.api_key:
                masked_key = f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else "****"
                self.console.print(f"[info]Debug: Using API Key: {masked_key}[/info]")
            else:
                self.console.print("[warning]Debug: No API Key found[/warning]")

    def debug(self, message: str):
        """Print a debug message if verbose is enabled."""
        if self.verbose:
            self.console.print(f"[info]Debug: {message}[/info]")

    def _load_api_key(self) -> str | None:
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
            json.dump(config, f, indent=2, ensure_ascii=False)

    def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Make an API request."""
        url = f"{BASE_URL}{endpoint}"

        if "json" in kwargs:
            self.session.headers["Content-Type"] = "application/json"

        self.debug(f"{method} {url}")
        if "json" in kwargs:
            self.debug(f"Payload: {kwargs['json']}")

        # Mask Authorization header in debug output
        headers = dict(self.session.headers)
        if "Authorization" in headers:
            auth = headers["Authorization"]
            if auth.startswith("Bearer"):  # pyright: ignore[reportArgumentType]
                headers["Authorization"] = "****"
        self.debug(f"Headers: {headers}")

        try:
            response = self.session.request(method, url, **kwargs)
            self.debug(f"Response Status: {response.status_code}")
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
                    self.debug(f"Raw Error Response: {e.response.text}")
                    raise Exception(f"Request failed with status {e.response.status_code}") from e
            raise Exception(f"Request failed: {e}") from e

    # Registration
    def register(self, name: str, description: str) -> dict[str, Any]:
        return self._request("POST", "/agents/register", json={"name": name, "description": description})

    def check_status(self) -> dict[str, Any]:
        return self._request("GET", "/agents/status")

    # Posts
    def create_post(
        self,
        submolt: str,
        title: str,
        content: str | None = None,
        url: str | None = None,
    ) -> dict[str, Any]:
        data = {"submolt": submolt, "title": title}
        if content:
            data["content"] = content
        if url:
            data["url"] = url
        return self._request("POST", "/posts", json=data)

    def get_feed(self, sort: str = "hot", limit: int = 25, submolt: str | None = None) -> dict[str, Any]:
        params = {"sort": sort, "limit": limit}
        if submolt:
            params["submolt"] = submolt
        return self._request("GET", "/posts", params=params)

    def get_post(self, post_id: str) -> dict[str, Any]:
        post_id = extract_id(post_id)
        return self._request("GET", f"/posts/{post_id}")

    def delete_post(self, post_id: str) -> dict[str, Any]:
        post_id = extract_id(post_id)
        return self._request("DELETE", f"/posts/{post_id}")

    # Comments
    def add_comment(self, post_id: str, content: str, parent_id: str | None = None) -> dict[str, Any]:
        post_id = extract_id(post_id)
        data = {"content": content}
        if parent_id:
            data["parent_id"] = extract_id(parent_id)
        return self._request("POST", f"/posts/{post_id}/comments", json=data)

    def get_comments(self, post_id: str, sort: str = "top") -> dict[str, Any]:
        post_id = extract_id(post_id)
        return self._request("GET", f"/posts/{post_id}/comments", params={"sort": sort})

    # Voting
    def upvote_post(self, post_id: str) -> dict[str, Any]:
        post_id = extract_id(post_id)
        return self._request("POST", f"/posts/{post_id}/upvote")

    def downvote_post(self, post_id: str) -> dict[str, Any]:
        post_id = extract_id(post_id)
        return self._request("POST", f"/posts/{post_id}/downvote")

    def upvote_comment(self, comment_id: str) -> dict[str, Any]:
        comment_id = extract_id(comment_id)
        return self._request("POST", f"/comments/{comment_id}/upvote")

    # Submolts
    def create_submolt(self, name: str, display_name: str, description: str) -> dict[str, Any]:
        data = {"name": name, "display_name": display_name, "description": description}
        return self._request("POST", "/submolts", json=data)

    def list_submolts(self) -> dict[str, Any]:
        return self._request("GET", "/submolts")

    def get_submolt(self, name: str) -> dict[str, Any]:
        return self._request("GET", f"/submolts/{name}")

    def subscribe_submolt(self, name: str) -> dict[str, Any]:
        return self._request("POST", f"/submolts/{name}/subscribe")

    def unsubscribe_submolt(self, name: str) -> dict[str, Any]:
        return self._request("DELETE", f"/submolts/{name}/subscribe")

    # Following
    def follow_molty(self, agent_name: str) -> dict[str, Any]:
        return self._request("POST", f"/agents/{agent_name}/follow")

    def unfollow_molty(self, agent_name: str) -> dict[str, Any]:
        return self._request("DELETE", f"/agents/{agent_name}/follow")

    # Feed
    def get_personalized_feed(self, sort: str = "hot", limit: int = 25) -> dict[str, Any]:
        return self._request("GET", "/feed", params={"sort": sort, "limit": limit})

    # Search
    def search(self, query: str, search_type: str = "all", limit: int = 20) -> dict[str, Any]:
        params = {"q": query, "type": search_type, "limit": limit}
        return self._request("GET", "/search", params=params)

    # Profile
    def get_profile(self) -> dict[str, Any]:
        return self._request("GET", "/agents/me")

    def get_agent_profile(self, agent_name: str) -> dict[str, Any]:
        return self._request("GET", "/agents/profile", params={"name": agent_name})

    def update_profile(self, description: str | None = None, metadata: str | None = None) -> dict[str, Any]:
        data = {}
        if description:
            data["description"] = description
        if metadata:
            data["metadata"] = metadata
        return self._request("PATCH", "/agents/me", json=data)

    def upload_avatar(self, file_path: str) -> dict[str, Any]:
        with open(file_path, "rb") as f:
            return self._request("POST", "/agents/me/avatar", files={"file": f})

    def remove_avatar(self) -> dict[str, Any]:
        return self._request("DELETE", "/agents/me/avatar")

    # Moderation
    def pin_post(self, post_id: str) -> dict[str, Any]:
        post_id = extract_id(post_id)
        return self._request("POST", f"/posts/{post_id}/pin")

    def unpin_post(self, post_id: str) -> dict[str, Any]:
        post_id = extract_id(post_id)
        return self._request("DELETE", f"/posts/{post_id}/pin")

    def update_submolt_settings(
        self,
        submolt_name: str,
        description: str | None = None,
        banner_color: str | None = None,
        theme_color: str | None = None,
    ) -> dict[str, Any]:
        data = {}
        if description:
            data["description"] = description
        if banner_color:
            data["banner_color"] = banner_color
        if theme_color:
            data["theme_color"] = theme_color
        return self._request("PATCH", f"/submolts/{submolt_name}/settings", json=data)

    def upload_submolt_avatar(self, submolt_name: str, file_path: str) -> dict[str, Any]:
        with open(file_path, "rb") as f:
            return self._request(
                "POST",
                f"/submolts/{submolt_name}/settings",
                files={"file": f},
                data={"type": "avatar"},
            )

    def upload_submolt_banner(self, submolt_name: str, file_path: str) -> dict[str, Any]:
        with open(file_path, "rb") as f:
            return self._request(
                "POST",
                f"/submolts/{submolt_name}/settings",
                files={"file": f},
                data={"type": "banner"},
            )

    def add_moderator(self, submolt_name: str, agent_name: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/submolts/{submolt_name}/moderators",
            json={"agent_name": agent_name, "role": "moderator"},
        )

    def remove_moderator(self, submolt_name: str, agent_name: str) -> dict[str, Any]:
        return self._request(
            "DELETE",
            f"/submolts/{submolt_name}/moderators",
            json={"agent_name": agent_name},
        )

    def list_moderators(self, submolt_name: str) -> dict[str, Any]:
        return self._request("GET", f"/submolts/{submolt_name}/moderators")

    # DMs
    def check_dms(self) -> dict[str, Any]:
        return self._request("GET", "/agents/dm/check")

    def list_dm_requests(self) -> dict[str, Any]:
        return self._request("GET", "/agents/dm/requests")

    def approve_dm_request(self, conversation_id: str) -> dict[str, Any]:
        return self._request("POST", f"/agents/dm/requests/{conversation_id}/approve")

    def list_conversations(self) -> dict[str, Any]:
        return self._request("GET", "/agents/dm/conversations")

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        return self._request("GET", f"/agents/dm/conversations/{conversation_id}")

    def send_dm(self, conversation_id: str, message: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/agents/dm/conversations/{conversation_id}/send",
            json={"message": message},
        )

    def request_dm(self, to_agent: str, message: str) -> dict[str, Any]:
        return self._request("POST", "/agents/dm/request", json={"to": to_agent, "message": message})
