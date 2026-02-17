import gradio as gr
from sqlmodel import Session, select

from ktem.app import BasePage
from ktem.db.models import User, engine
from ktem.embeddings.ui import EmbeddingManagement
from ktem.i18n import get_text
from ktem.index.ui import IndexManagement
from ktem.llms.ui import LLMManagement
from ktem.pages.resources.document_types import DocumentTypesManagement
from ktem.pages.resources.vlms import VLMsManagement
from ktem.rerankings.ui import RerankingManagement

from .user import UserManagement


class ResourcesTab(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Tab(
            get_text("en", "tab.index_collections")
        ) as self.index_management_tab:
            self.index_management = IndexManagement(self._app)

        with gr.Tab(get_text("en", "tab.llms")) as self.llm_management_tab:
            self.llm_management = LLMManagement(self._app)

        with gr.Tab(get_text("en", "tab.vlms")) as self.vlms_tab:
            self.vlms_management = VLMsManagement(self._app)

        with gr.Tab(get_text("en", "tab.embeddings")) as self.emb_management_tab:
            self.emb_management = EmbeddingManagement(self._app)

        with gr.Tab(get_text("en", "tab.rerankings")) as self.rerank_management_tab:
            self.rerank_management = RerankingManagement(self._app)

        with gr.Tab(
            get_text("en", "tab.document_types", default="Document Types")
        ) as self.document_types_tab:
            self.document_types_management = DocumentTypesManagement(self._app)

        if self._app.f_user_management:
            with gr.Tab(
                get_text("en", "tab.users"), visible=False
            ) as self.user_management_tab:
                self.user_management = UserManagement(self._app)

    def on_register_events(self):
        if hasattr(self._app, "lang_dropdown") and self._app.lang_dropdown is not None:
            outputs = [
                self.index_management_tab,
                self.llm_management_tab,
                self.vlms_tab,
                self.emb_management_tab,
                self.rerank_management_tab,
                self.document_types_tab,
            ]
            keys = [
                "tab.index_collections",
                "tab.llms",
                "tab.vlms",
                "tab.embeddings",
                "tab.rerankings",
                "tab.document_types",
            ]
            if self._app.f_user_management:
                outputs.append(self.user_management_tab)
                keys.append("tab.users")

            self._app.lang_dropdown.change(
                fn=lambda lang: [gr.update(label=get_text(lang, k)) for k in keys],
                inputs=[self._app.lang_dropdown],
                outputs=outputs,
                show_progress="hidden",
            )

    def on_subscribe_public_events(self):
        if self._app.f_user_management:
            self._app.subscribe_event(
                name="onSignIn",
                definition={
                    "fn": self.toggle_user_management,
                    "inputs": [self._app.user_id],
                    "outputs": [self.user_management_tab],
                    "show_progress": "hidden",
                },
            )

            self._app.subscribe_event(
                name="onSignOut",
                definition={
                    "fn": self.toggle_user_management,
                    "inputs": [self._app.user_id],
                    "outputs": [self.user_management_tab],
                    "show_progress": "hidden",
                },
            )

    def toggle_user_management(self, user_id):
        """Show/hide the user management, depending on the user's role"""
        with Session(engine) as session:
            user = session.exec(select(User).where(User.id == user_id)).first()
            if user and user.admin:
                return gr.update(visible=True)

            return gr.update(visible=False)
