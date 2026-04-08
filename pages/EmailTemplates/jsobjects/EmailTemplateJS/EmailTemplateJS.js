export default {
  generatePlainText() {
    const html = appsmith.store.emailTemplateLiveHtml ||
      (typeof RichTextTemplate.text === "string"
        ? RichTextTemplate.text
        : ((appsmith.store.emailTemplateDraft || {}).html_template || ""));

    let prepared = html;
    prepared = prepared.split("<br />").join("
");
    prepared = prepared.split("<br/>").join("
");
    prepared = prepared.split("<br>").join("
");
    prepared = prepared.split("<hr />").join("
---
");
    prepared = prepared.split("<hr/>").join("
---
");
    prepared = prepared.split("<hr>").join("
---
");
    prepared = prepared.split("</p>").join("</p>

");
    prepared = prepared.split("</div>").join("</div>

");
    prepared = prepared.split("</section>").join("</section>

");
    prepared = prepared.split("</article>").join("</article>

");
    prepared = prepared.split("</blockquote>").join("</blockquote>

");
    prepared = prepared.split("</h1>").join("</h1>

");
    prepared = prepared.split("</h2>").join("</h2>

");
    prepared = prepared.split("</h3>").join("</h3>

");
    prepared = prepared.split("</h4>").join("</h4>

");
    prepared = prepared.split("</h5>").join("</h5>

");
    prepared = prepared.split("</h6>").join("</h6>

");
    prepared = prepared.split("</li>").join("</li>
");
    prepared = prepared.split("</tr>").join("</tr>
");
    prepared = prepared.split("</td>").join("</td>	");
    prepared = prepared.split("</th>").join("</th>	");

    const temp = document.createElement("div");
    temp.innerHTML = prepared;
    Array.from(temp.querySelectorAll("li")).forEach((node) => node.insertAdjacentText("afterbegin", "- "));

    const lines = (temp.textContent || "").split("
");
    const output = [];
    let blankRun = 0;

    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index].trim();
      if (!line) {
        blankRun += 1;
        if (blankRun <= 1) output.push("");
      } else {
        blankRun = 0;
        output.push(line);
      }
    }

    const text = output.join("
").trim();
    storeValue("emailTemplateDraft", {
      ...(appsmith.store.emailTemplateDraft || {}),
      text_template: text,
      html_template: html,
    });
    storeValue("emailTemplateLiveHtml", html);
    resetWidget("TextareaTextTemplate", true);
    resetWidget("TextareaHtmlTemplate", true);
    resetWidget("RichTextPreview", true);
    showAlert("Plain text output updated", "success");
    return text;
  }
}