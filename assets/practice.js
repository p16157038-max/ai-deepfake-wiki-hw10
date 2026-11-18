/* The renderer supplies all teaching text and resolved citations. */
(() => {
  "use strict";
  const source = document.querySelector("#practice-data");
  const panel = document.querySelector("#practice-panel");
  const select = document.querySelector("#practice-select");
  if (!source || !panel || !select) return;
  const cases = JSON.parse(source.textContent);
  const attempted = new Set();
  let current = cases[0];

  function updateProgress() {
    const progress = document.querySelector("#practice-progress");
    progress.textContent = `已練習 ${attempted.size} / ${cases.length}`;
    progress.dataset.attempted = String(attempted.size);
    progress.dataset.total = String(cases.length);
    document.querySelectorAll("[data-practice-case]").forEach((button) => {
      const active = button.dataset.practiceCase === current.id;
      if (active) button.setAttribute("aria-current", "true");
      else button.removeAttribute("aria-current");
      button.querySelector(".case-attempted").hidden = !attempted.has(button.dataset.practiceCase);
    });
  }

  function updateHash(id) {
    if (window.location.hash === `#case=${id}`) return;
    try { window.history.replaceState(null, "", `#case=${id}`); }
    catch (_) { window.location.hash = `case=${id}`; }
  }

  function requestedCase() {
    const value = window.location.hash.slice(1);
    return new URLSearchParams(value).get("case") || value;
  }

  function clearAnswer({ focus = false } = {}) {
    panel.querySelectorAll(".practice-option").forEach((button) => {
      button.setAttribute("aria-pressed", "false");
      button.classList.remove("is-correct", "is-wrong");
    });
    panel.querySelectorAll(".selected-choice").forEach((label) => { label.hidden = true; });
    const feedback = panel.querySelector("#practice-feedback");
    feedback.hidden = true;
    feedback.removeAttribute("data-result");
    panel.querySelector("#practice-lesson").hidden = true;
    const reason = panel.querySelector("#practice-reason");
    if (reason) reason.value = "";
    panel.querySelectorAll(".reason-reference").forEach((details) => { details.open = false; });
    if (focus) panel.querySelector(".practice-option")?.focus({ preventScroll: true });
  }

  function showCase(id, { focus = false, hash = true } = {}) {
    const item = cases.find((candidate) => candidate.id === id) || cases[0];
    current = item;
    select.value = current.id;
    panel.innerHTML = current.html;
    updateProgress();
    if (hash) updateHash(current.id);
    if (focus) panel.querySelector("#practice-case-title")?.focus({ preventScroll: true });
  }

  panel.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button || !panel.contains(button)) return;
    if (button.matches("[data-practice-reset]")) {
      clearAnswer({ focus: true });
      return;
    }
    if (button.matches("[data-practice-next]")) {
      const next = (cases.indexOf(current) + 1) % cases.length;
      showCase(cases[next].id, { focus: true });
      panel.scrollIntoView({ block: "start", behavior: "instant" });
      return;
    }
    if (!button.matches(".practice-option")) return;
    clearAnswer();
    const option = current.options[Number(button.dataset.optionIndex)];
    button.classList.add(option.correct ? "is-correct" : "is-wrong");
    button.setAttribute("aria-pressed", "true");
    const feedback = panel.querySelector("#practice-feedback");
    feedback.dataset.result = option.correct ? "correct" : "wrong";
    feedback.querySelector(".feedback-icon").textContent = option.correct ? "✓" : "↳";
    feedback.querySelector(".feedback-title").textContent = option.correct ? "這個第一步更合適。" : "這一步先緩一緩，看看原因。";
    feedback.querySelector(".feedback-text").textContent = option.feedback;
    feedback.hidden = false;
    panel.querySelector("#practice-lesson").hidden = false;
    panel.querySelector(`[data-choice-index="${button.dataset.optionIndex}"] .selected-choice`).hidden = false;
    attempted.add(current.id);
    updateProgress();
    feedback.focus({ preventScroll: true });
    feedback.scrollIntoView({ block: "start", behavior: "instant" });
  });
  select.addEventListener("change", () => showCase(select.value));
  document.querySelectorAll("[data-practice-case]").forEach((button) => {
    button.addEventListener("click", () => {
      showCase(button.dataset.practiceCase, { focus: true });
      if (window.matchMedia("(max-width: 800px)").matches) panel.scrollIntoView({ block: "start", behavior: "instant" });
    });
  });
  window.addEventListener("hashchange", () => showCase(requestedCase(), { hash: false }));
  showCase(requestedCase());
})();
