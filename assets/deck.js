/* Navigation and quiz state only. All teaching text comes from approved JSON. */
(() => {
  "use strict";
  const slides = Array.from(document.querySelectorAll(".slide"));
  if (!slides.length) return;
  const previous = document.querySelector("[data-deck-prev]");
  const next = document.querySelector("[data-deck-next]");
  const counter = document.querySelector("[data-page-count]");
  const status = document.querySelector("[data-deck-status]");
  const progress = document.querySelector(".progress-track");
  const fill = document.querySelector(".progress-fill");
  const baseTitle = document.title;
  let current = 0;

  const fromHash = () => {
    let hash;
    try { hash = decodeURIComponent(window.location.hash.slice(1)); }
    catch (_) { return 0; }
    const params = new URLSearchParams(hash);
    const candidate = params.get("slide") || hash;
    const found = slides.findIndex((slide) => slide.id === candidate);
    if (found >= 0) return found;
    const page = params.get("page");
    if (page && /^\d+$/u.test(page)) return Math.min(slides.length - 1, Math.max(0, Number(page) - 1));
    return 0;
  };

  const show = (requested, { hash = true, focus = false } = {}) => {
    current = Math.max(0, Math.min(slides.length - 1, requested));
    slides.forEach((slide, index) => {
      const active = index === current;
      slide.hidden = !active;
      slide.setAttribute("aria-hidden", String(!active));
    });
    if (previous) previous.disabled = current === 0;
    if (next) next.disabled = current === slides.length - 1;
    if (counter) counter.textContent = `${current + 1} / ${slides.length}`;
    if (progress) progress.setAttribute("aria-valuenow", String(current + 1));
    if (fill) fill.style.width = `${((current + 1) / slides.length) * 100}%`;
    if (status) status.textContent = `第 ${current + 1} 頁，共 ${slides.length} 頁：${slides[current].querySelector(".slide-title")?.textContent || ""}`;
    document.title = `${baseTitle}｜${current + 1} / ${slides.length}`;
    if (hash && window.location.hash !== `#${slides[current].id}`) {
      try { window.history.replaceState(null, "", `#${slides[current].id}`); }
      catch (_) { window.location.hash = slides[current].id; }
    }
    if (focus) {
      slides[current].querySelector(".slide-title")?.focus({ preventScroll: true });
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    }
  };

  previous?.addEventListener("click", () => show(current - 1, { focus: true }));
  next?.addEventListener("click", () => show(current + 1, { focus: true }));
  window.addEventListener("hashchange", () => show(fromHash(), { hash: false }));
  document.querySelector("[data-deck-print]")?.addEventListener("click", () => window.print());
  document.addEventListener("keydown", (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey || event.defaultPrevented) return;
    const target = event.target;
    if (target instanceof Element && (target.closest("input,textarea,select,[contenteditable='true']") || target.closest("summary"))) return;
    let destination;
    if (event.key === "ArrowRight" || event.key === "PageDown") destination = current + 1;
    else if (event.key === "ArrowLeft" || event.key === "PageUp") destination = current - 1;
    else if (event.key === "Home") destination = 0;
    else if (event.key === "End") destination = slides.length - 1;
    else return;
    event.preventDefault();
    show(destination, { focus: true });
  });

  document.querySelectorAll("[data-quiz]").forEach((quiz) => {
    const options = Array.from(quiz.querySelectorAll("[data-quiz-option]"));
    const feedback = quiz.querySelector(".quiz-feedback");
    const clear = () => {
      options.forEach((option) => {
        option.classList.remove("is-correct", "is-wrong");
        option.setAttribute("aria-pressed", "false");
      });
      if (feedback) {
        feedback.hidden = true;
        feedback.textContent = "";
        feedback.removeAttribute("data-result");
      }
    };
    options.forEach((option) => option.addEventListener("click", () => {
      clear();
      const correct = option.dataset.correct === "true";
      option.classList.add(correct ? "is-correct" : "is-wrong");
      option.setAttribute("aria-pressed", "true");
      if (feedback) {
        const explanation = option.dataset.feedback || "";
        feedback.textContent = `${correct ? "答對了。" : "再想一下。"}${explanation}`;
        feedback.dataset.result = correct ? "correct" : "wrong";
        feedback.hidden = false;
      }
    }));
    quiz.querySelector("[data-quiz-reset]")?.addEventListener("click", () => {
      clear();
      options[0]?.focus({ preventScroll: true });
    });
  });
  show(fromHash());
})();
