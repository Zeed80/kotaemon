"""Общие JavaScript-сниппеты для Gradio UI."""

chat_input_focus_js = """
function() {
    let chatInput = document.querySelector("#chat-input textarea");
    chatInput.focus();
}
"""

chat_input_focus_js_with_submit = """
function() {
    let chatInput = document.querySelector("#chat-input textarea");
    let chatInputSubmit = document.querySelector("#chat-input button.submit-button");
    chatInputSubmit.click();
    chatInput.focus();
}
"""
