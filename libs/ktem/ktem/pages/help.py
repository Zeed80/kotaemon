from pathlib import Path

import gradio as gr
import requests
from theflow.settings import settings

from flowsettings_config import config

KH_DEMO_MODE = getattr(settings, "KH_DEMO_MODE", False)
HF_SPACE_URL = config("HF_SPACE_URL", default="")


def get_remote_doc(url: str) -> str:
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return res.text
    except Exception as e:
        print(f"Failed to fetch document from {url}: {e}")
        return (
            "**Error:** Unable to load content. "
            "Please check your network connection."
        )


def download_changelogs(release_url: str) -> str:
    try:
        res = requests.get(release_url, timeout=10)
        res.raise_for_status()
        changelogs = res.json().get("body", "")
        return changelogs
    except Exception as e:
        print(f"Failed to fetch changelogs from {release_url}: {e}")
        return (
            "**Error:** Unable to load changelogs. "
            "Please check your network connection."
        )


class HelpPage:
    def __init__(
        self,
        app,
        doc_dir: str = settings.KH_DOC_DIR,
        remote_content_url: str = "https://raw.githubusercontent.com/Zeed80/kotaemon",
        app_version: str | None = settings.KH_APP_VERSION,
        changelogs_cache_dir: str | Path = (
            Path(settings.KH_APP_DATA_DIR) / "changelogs"
        ),
    ):
        self._app = app
        self.doc_dir = Path(doc_dir)
        self.remote_content_url = remote_content_url
        self.app_version = app_version
        self.changelogs_cache_dir = Path(changelogs_cache_dir)

        self.changelogs_cache_dir.mkdir(parents=True, exist_ok=True)

        about_md_dir = self.doc_dir / "about.md"
        if about_md_dir.exists():
            with (self.doc_dir / "about.md").open(encoding="utf-8") as fi:
                about_md = fi.read()
        else:  # fetch from remote
            about_md = get_remote_doc(
                f"{self.remote_content_url}/v{self.app_version}/docs/about.md"
            )
        if about_md:
            with gr.Accordion("About"):
                if self.app_version:
                    about_md = f"Version: {self.app_version}\n\n{about_md}"
                gr.Markdown(about_md)

        if KH_DEMO_MODE:
            with gr.Accordion("Create Your Own Space"):
                gr.Markdown(
                    "This is a demo with limited functionality. "
                    "Use **Create space** button to install Kotaemon "
                    "in your own space with all features "
                    "(including upload and manage your private "
                    "documents securely)."
                )
                gr.Button(
                    value="Create Your Own Space",
                    link=HF_SPACE_URL,
                    variant="primary",
                    size="lg",
                )

        user_guide_md_dir = self.doc_dir / "usage.md"
        if user_guide_md_dir.exists():
            with (self.doc_dir / "usage.md").open(encoding="utf-8") as fi:
                user_guide_md = fi.read()
        else:  # fetch from remote
            user_guide_md = get_remote_doc(
                f"{self.remote_content_url}/v{self.app_version}/docs/usage.md"
            )
        if user_guide_md:
            with gr.Accordion("User Guide", open=not KH_DEMO_MODE):
                gr.Markdown(user_guide_md)

        # Пропускаем загрузку changelogs для local/vlocal — такого тега нет на GitHub
        _ver = (self.app_version or "").strip().lower()
        _skip_changelog = _ver in ("local", "vlocal") or "local" in _ver
        if self.app_version and not _skip_changelog:
            # try retrieve from cache
            changelogs = ""

            if (self.changelogs_cache_dir / f"{self.app_version}.md").exists():
                with open(self.changelogs_cache_dir / f"{self.app_version}.md") as fi:
                    changelogs = fi.read()
            else:
                release_url_base = (
                    "https://api.github.com/repos/Zeed80/kotaemon/releases"
                )
                changelogs = download_changelogs(
                    release_url=f"{release_url_base}/tags/v{self.app_version}"
                )

                # cache the changelogs only on success (avoid caching error messages)
                if changelogs and not changelogs.startswith("**Error:**"):
                    if not self.changelogs_cache_dir.exists():
                        self.changelogs_cache_dir.mkdir(parents=True, exist_ok=True)
                    with open(
                        self.changelogs_cache_dir / f"{self.app_version}.md", "w"
                    ) as fi:
                        fi.write(changelogs)

            if changelogs:
                with gr.Accordion(f"Changelogs (v{self.app_version})"):
                    gr.Markdown(changelogs)
