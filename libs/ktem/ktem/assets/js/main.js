function run() {
  let main_parent_el = document.getElementById("chat-tab");
  if (!main_parent_el || !main_parent_el.parentNode) return;
  let main_parent = main_parent_el.parentNode;

  if (main_parent.childNodes[0]) {
    main_parent.childNodes[0].classList.add("header-bar");
  }
  main_parent.style = "padding: 0; margin: 0";
  if (main_parent.parentNode) main_parent.parentNode.style = "gap: 0";
  if (main_parent.parentNode && main_parent.parentNode.parentNode) {
    main_parent.parentNode.parentNode.style = "padding: 0";
  }

  // add favicon
  const favicon = document.createElement("link");
  favicon.rel = "icon";
  favicon.type = "image/svg+xml";
  favicon.href = "/favicon.ico";
  document.head.appendChild(favicon);

  // i18n helper: get translation for key, fallback to en then key
  const t = (lang, key) =>
    window.KH_I18N?.[lang]?.[key] || window.KH_I18N?.en?.[key] || key;

  const ariaKeyMap = {
    "toggle-dark-button": "aria.toggle_dark",
    "chat-expand-button": "aria.toggle_chat",
    "info-expand-button": "aria.toggle_info",
    "conversation-rename-button": "aria.rename_conv",
    "conversation-delete-button": "aria.delete_conv",
    "new-conv-button": "aria.new_chat",
  };

  const applyUiLang = (lang) => {
    const L = lang || "en";
    let conv_dropdown = document.querySelector("#conversation-dropdown input");
    if (conv_dropdown)
      conv_dropdown.placeholder = t(L, "chat.browse_conversation");
    for (const [id, key] of Object.entries(ariaKeyMap)) {
      const el = document.getElementById(id);
      if (el) {
        const btn = el.tagName === "BUTTON" ? el : el.querySelector("button");
        if (btn) btn.setAttribute("aria-label", t(L, key));
      }
    }
  };

  applyUiLang("en");

  globalThis.applyUiLang = applyUiLang;

  // move info-expand-button
  let info_expand_button = document.getElementById("info-expand-button");
  let chat_info_panel = document.getElementById("info-expand");
  if (info_expand_button && chat_info_panel && chat_info_panel.childNodes[2]) {
    chat_info_panel.insertBefore(
      info_expand_button,
      chat_info_panel.childNodes[2]
    );
  }

  // move toggle-side-bar button
  let chat_expand_button = document.getElementById("chat-expand-button");
  let chat_column = document.getElementById("main-chat-bot");
  let conv_column = document.getElementById("conv-settings-panel");

  // move settings action buttons (Save, Restart) to tab nav bar
  let setting_tab_nav_bar = document.querySelector("#settings-tab .tab-nav");
  let settings_action_buttons = document.getElementById("settings-action-buttons");
  if (settings_action_buttons && setting_tab_nav_bar) {
    setting_tab_nav_bar.appendChild(settings_action_buttons);
  }

  let default_conv_column_min_width = "min(300px, 100%)";
  if (conv_column) conv_column.style.minWidth = default_conv_column_min_width;

  globalThis.toggleChatColumn = () => {
    if (!conv_column) return;
    let flex_grow = conv_column.style.flexGrow;
    if (flex_grow == "0") {
      conv_column.style.flexGrow = "1";
      conv_column.style.minWidth = default_conv_column_min_width;
    } else {
      conv_column.style.flexGrow = "0";
      conv_column.style.minWidth = "0px";
    }
  };

  if (chat_column && chat_expand_button) {
    chat_column.insertBefore(chat_expand_button, chat_column.firstChild);
  }

  // move use mind-map checkbox
  let mindmap_checkbox = document.getElementById("use-mindmap-checkbox");
  let citation_dropdown = document.getElementById("citation-dropdown");
  let chat_setting_panel = document.getElementById("chat-settings-expand");
  if (mindmap_checkbox && chat_setting_panel && chat_setting_panel.childNodes[2]) {
    chat_setting_panel.insertBefore(
      mindmap_checkbox,
      chat_setting_panel.childNodes[2]
    );
  }
  if (citation_dropdown && mindmap_checkbox && chat_setting_panel) {
    chat_setting_panel.insertBefore(citation_dropdown, mindmap_checkbox);
  }

  // move share conv checkbox
  let report_div = document.querySelector(
    "#report-accordion > div:nth-child(3) > div:nth-child(1)"
  );
  let share_conv_checkbox = document.getElementById("is-public-checkbox");
  if (share_conv_checkbox && report_div) {
    let report_btn = report_div.querySelector("button");
    if (report_btn) report_div.insertBefore(share_conv_checkbox, report_btn);
  }

  // create slider toggle
  const is_public_checkbox = document.getElementById("suggest-chat-checkbox");
  if (is_public_checkbox) {
    const labels = is_public_checkbox.getElementsByTagName("label");
    const spans = is_public_checkbox.getElementsByTagName("span");
    if (labels[0] && spans[0]) {
      const label_element = labels[0];
      const checkbox_span = spans[0];
      const new_div = document.createElement("div");
      label_element.classList.add("switch");
      is_public_checkbox.appendChild(checkbox_span);
      label_element.appendChild(new_div);
    }
  }

  // close (collapsible)
  globalThis.clpseFn = globalThis.closeFn = (id) => {
    var obj = document.getElementById("clpse-btn-" + id);
    if (!obj) return;
    obj.classList.toggle("clpse-active");
    var content = obj.nextElementSibling;
    if (content) {
      if (content.style.display === "none") {
        content.style.display = "block";
      } else {
        content.style.display = "none";
      }
    }
  };

  // store info in local storage
  globalThis.setStorage = (key, value) => {
    localStorage.setItem(key, value);
  };
  globalThis.getStorage = (key, value) => {
    item = localStorage.getItem(key);
    return item ? item : value;
  };
  globalThis.removeFromStorage = (key) => {
    localStorage.removeItem(key);
  };

  // Function to scroll to given citation with ID
  // Sleep function using Promise and setTimeout
  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  globalThis.scrollToCitation = async (event) => {
    event.preventDefault();
    var citationId = event.target.getAttribute("id");
    if (!citationId) return;

    await sleep(100);

    var modal = document.getElementById("pdf-modal");
    var citation = document.querySelector('mark[id="' + citationId + '"]');

    if (modal && modal.style.display == "block" && citation) {
      var detail_elem = citation;
      while (detail_elem && detail_elem.tagName.toLowerCase() != "details") {
        detail_elem = detail_elem.parentElement;
      }
      var pdfLink = detail_elem && detail_elem.getElementsByClassName("pdf-link").item(0);
      if (pdfLink) pdfLink.click();
    } else if (citation) {
      citation.scrollIntoView({ behavior: "smooth" });
    }
  };

  globalThis.fullTextSearch = () => {
    var bot_messages = document.querySelectorAll(
      "div#main-chat-bot div.message-row.bot-row"
    );
    var last_bot_message = bot_messages[bot_messages.length - 1];
    if (!last_bot_message) return;

    if (last_bot_message.classList.contains("text_selection")) {
      return;
    }

    last_bot_message.classList.add("text_selection");

    // Get sentences from evidence div
    var evidences = document.querySelectorAll(
      "#html-info-panel > div:last-child > div > details.evidence div.evidence-content"
    );
    console.log("Indexing evidences", evidences);

    const segmenterEn = new Intl.Segmenter("en", { granularity: "sentence" });
    // Split sentences and save to all_segments list
    var all_segments = [];
    for (var evidence of evidences) {
      // check if <details> tag is open
      if (!evidence.parentElement.open) {
        continue;
      }
      var markmap_div = evidence.querySelector("div.markmap");
      if (markmap_div) {
        continue;
      }

      var evidence_content = evidence.textContent.replace(/[\r\n]+/g, " ");
      sentence_it = segmenterEn.segment(evidence_content)[Symbol.iterator]();
      while ((sentence = sentence_it.next().value)) {
        segment = sentence.segment.trim();
        if (segment) {
          all_segments.push({
            id: all_segments.length,
            text: segment,
          });
        }
      }
    }

    let miniSearch = new MiniSearch({
      fields: ["text"], // fields to index for full-text search
      storeFields: ["text"],
    });

    // Index all documents
    miniSearch.addAll(all_segments);

    last_bot_message.addEventListener("mouseup", () => {
      let selection = window.getSelection().toString();
      let results = miniSearch.search(selection);

      if (results.length == 0) {
        return;
      }
      let matched_text = results[0].text;
      console.log("query\n", selection, "\nmatched text\n", matched_text);

      var evidences = document.querySelectorAll(
        "#html-info-panel > div:last-child > div > details.evidence div.evidence-content"
      );
      // check if modal is open
      var modal = document.getElementById("pdf-modal");

      // convert all <mark> in evidences to normal text
      evidences.forEach((evidence) => {
        evidence.querySelectorAll("mark").forEach((mark) => {
          mark.outerHTML = mark.innerText;
        });
      });

      // highlight matched_text in evidences
      for (var evidence of evidences) {
        var evidence_content = evidence.textContent.replace(/[\r\n]+/g, " ");
        if (evidence_content.includes(matched_text)) {
          // select all p and li elements
          paragraphs = evidence.querySelectorAll("p, li");
          for (var p of paragraphs) {
            var p_content = p.textContent.replace(/[\r\n]+/g, " ");
            if (p_content.includes(matched_text)) {
              p.innerHTML = p_content.replace(
                matched_text,
                "<mark>" + matched_text + "</mark>"
              );
              console.log("highlighted", matched_text, "in", p);
              if (modal && modal.style.display == "block") {
                var detail_elem = p;
                while (detail_elem && detail_elem.tagName.toLowerCase() != "details") {
                  detail_elem = detail_elem.parentElement;
                }
                var pdfLink = detail_elem && detail_elem.getElementsByClassName("pdf-link").item(0);
                if (pdfLink) pdfLink.click();
              } else {
                p.scrollIntoView({ behavior: "smooth", block: "center" });
              }
              break;
            }
          }
        }
      }
    });
  };

  globalThis.spawnDocument = (content, options) => {
    let opt = {
      window: "",
      closeChild: true,
      childId: "_blank",
    };
    Object.assign(opt, options);
    // minimal error checking
    if (
      content &&
      typeof content.toString == "function" &&
      content.toString().length
    ) {
      let child = window.open("", opt.childId, opt.window);
      child.document.write(content.toString());
      if (opt.closeChild) child.document.close();
      return child;
    }
  };

  globalThis.fillChatInput = (event) => {
    let chatInput = document.querySelector("#chat-input textarea");
    if (!chatInput || !event.target) return;
    chatInput.value = "Explain " + event.target.textContent;
    chatInput.dispatchEvent(new Event("input", { bubbles: true }));
    chatInput.focus();
  };
}
