const items = window.GALLERY_ITEMS || [];

const questions = [
  {
    title: "Which composition feels closest?",
    options: [
      { label: "Circle or wreath", tags: ["circle", "wreath", "round", "elegant"], swatch: "#b98931" },
      { label: "Arch or window", tags: ["arch", "architectural", "classic", "formal"], swatch: "#c99b42" },
      { label: "S-curve or infinity", tags: ["s-curve", "infinity", "flowing", "modern"], swatch: "#0d6b68" },
      { label: "Rectangle or framed panel", tags: ["rectangle", "framed", "classic", "formal"], swatch: "#69405f" },
      { label: "Heart or symbolic shape", tags: ["heart", "symbolic", "romantic"], swatch: "#a8494f" },
    ],
  },
  {
    title: "What should the artwork feel like?",
    options: [
      { label: "Garden and botanical", tags: ["botanical", "flowers", "garden", "wreath"], swatch: "#548c64" },
      { label: "Regal and illuminated", tags: ["regal", "gold", "crown", "ornate"], swatch: "#b98931" },
      { label: "Modern and expressive", tags: ["modern", "abstract", "vibrant", "asymmetric"], swatch: "#2e618b" },
      { label: "Classic and formal", tags: ["classic", "formal", "geometric", "architectural"], swatch: "#2f4246" },
      { label: "Romantic and personal", tags: ["romantic", "heart", "roses", "soft"], swatch: "#b85a62" },
    ],
  },
  {
    title: "Which color direction is right?",
    options: [
      { label: "Vibrant jewel tones", tags: ["vibrant", "jewel", "colorful", "bold"], swatch: "#1f75a8" },
      { label: "Soft watercolor", tags: ["soft", "pastel", "elegant"], swatch: "#b8d5ce" },
      { label: "Gold and ivory", tags: ["gold", "classic", "elegant", "minimal"], swatch: "#d3a64e" },
      { label: "Blue, teal, and green", tags: ["blue", "teal", "green", "water"], swatch: "#0f7c83" },
      { label: "Rose, red, and purple", tags: ["roses", "red", "purple", "romantic"], swatch: "#93445e" },
    ],
  },
  {
    title: "Which motifs should stand out?",
    options: [
      { label: "Flowers, vines, or trees", tags: ["flowers", "botanical", "tree", "branches", "wildflowers"], swatch: "#6c9b57" },
      { label: "Rings, hearts, or infinity", tags: ["rings", "heart", "infinity", "symbolic"], swatch: "#ba7159" },
      { label: "Hamsa or Judaica symbols", tags: ["hamsa", "judaica", "symbolic"], swatch: "#62708c" },
      { label: "Geometry or architecture", tags: ["geometric", "architectural", "arch", "formal"], swatch: "#3b5f66" },
      { label: "Birds, peacocks, or landscape", tags: ["birds", "peacock", "landscape", "sun", "water"], swatch: "#2e618b" },
    ],
  },
];

const filters = [
  { label: "All", tag: "all" },
  { label: "Botanical", tag: "botanical" },
  { label: "Circle", tag: "circle" },
  { label: "Arch", tag: "arch" },
  { label: "S-curve", tag: "s-curve" },
  { label: "Hamsa", tag: "hamsa" },
  { label: "Heart", tag: "heart" },
  { label: "Gold", tag: "gold" },
  { label: "Blue", tag: "blue" },
  { label: "Modern", tag: "modern" },
];

const state = {
  step: 0,
  answers: [],
  activeFilter: "all",
};

const els = {
  questionCount: document.querySelector("#question-count"),
  progressBar: document.querySelector("#progress-bar"),
  questionTitle: document.querySelector("#question-title"),
  optionGrid: document.querySelector("#option-grid"),
  backButton: document.querySelector("#back-button"),
  resetButton: document.querySelector("#reset-button"),
  selectionTrail: document.querySelector("#selection-trail"),
  recommendations: document.querySelector("#recommendations"),
  filterRow: document.querySelector("#filter-row"),
  galleryGrid: document.querySelector("#gallery-grid"),
  dialog: document.querySelector("#preview-dialog"),
  previewImage: document.querySelector("#preview-image"),
  previewTitle: document.querySelector("#preview-title"),
  previewDescription: document.querySelector("#preview-description"),
  closePreview: document.querySelector("#close-preview"),
};

function scoreItems() {
  const selectedTags = state.answers.flatMap((answer) => answer.tags);
  return items
    .map((item, index) => {
      const itemTags = new Set(item.tags);
      let score = 0;
      selectedTags.forEach((tag) => {
        if (itemTags.has(tag)) score += 4;
      });
      state.answers.forEach((answer, answerIndex) => {
        if (answer.tags.some((tag) => itemTags.has(tag))) {
          score += questions.length - answerIndex;
        }
      });
      return { item, score, index };
    })
    .sort((a, b) => b.score - a.score || a.index - b.index)
    .map((entry) => entry.item);
}

function topMatches() {
  const ranked = uniqueByFamily(scoreItems());
  if (state.answers.length === 0) {
    return ranked.filter((item) =>
      ["peacock_arch", "botanical_gold_circle", "vivid_heart_swirl", "blue_mandala", "gold_arch"].includes(item.family),
    ).slice(0, 5);
  }
  return ranked.slice(0, 5);
}

function uniqueByFamily(rankedItems) {
  const seen = new Set();
  return rankedItems.filter((item) => {
    if (seen.has(item.family)) return false;
    seen.add(item.family);
    return true;
  });
}

function renderQuestion() {
  const complete = state.step >= questions.length;
  els.questionCount.textContent = complete ? "Shortlist ready" : `Question ${state.step + 1} of ${questions.length}`;
  els.progressBar.style.width = `${Math.round((state.answers.length / questions.length) * 100)}%`;
  els.backButton.disabled = state.answers.length === 0;

  els.optionGrid.innerHTML = "";
  if (complete) {
    els.questionTitle.textContent = "Your style shortlist is ready.";
    const restart = document.createElement("button");
    restart.className = "option-button";
    restart.type = "button";
    restart.innerHTML = `<span class="option-swatch" style="--gold:${questions[0].options[0].swatch}; background:${questions[0].options[0].swatch}"></span><span>Start a new style path</span>`;
    restart.addEventListener("click", resetQuiz);
    els.optionGrid.append(restart);
    return;
  }

  const question = questions[state.step];
  els.questionTitle.textContent = question.title;
  question.options.forEach((option) => {
    const button = document.createElement("button");
    button.className = "option-button";
    button.type = "button";
    button.setAttribute("aria-pressed", "false");
    button.innerHTML = `<span class="option-swatch" style="background:${option.swatch}"></span><span>${option.label}</span>`;
    button.addEventListener("click", () => {
      state.answers[state.step] = option;
      state.step += 1;
      render();
    });
    els.optionGrid.append(button);
  });
}

function renderTrail() {
  els.selectionTrail.innerHTML = "";
  if (state.answers.length === 0) {
    const chip = document.createElement("span");
    chip.className = "trail-chip";
    chip.textContent = "Open to all styles";
    els.selectionTrail.append(chip);
    return;
  }
  state.answers.forEach((answer) => {
    const chip = document.createElement("span");
    chip.className = "trail-chip";
    chip.textContent = answer.label;
    els.selectionTrail.append(chip);
  });
}

function cardMarkup(item, compact = false) {
  const tags = item.tags.slice(0, compact ? 2 : 3).map((tag) => `<span class="tag">${tag}</span>`).join("");
  return `
    <button class="image-button" type="button" data-preview="${item.id}">
      <img src="${item.src}" alt="${item.title}">
    </button>
    <div class="${compact ? "match-copy" : "gallery-copy"}">
      <h3>${item.title}</h3>
      <p>${item.description}</p>
      <div class="tag-list">${tags}</div>
    </div>
  `;
}

function renderRecommendations() {
  els.recommendations.innerHTML = "";
  topMatches().forEach((item) => {
    const article = document.createElement("article");
    article.className = "match-card";
    article.innerHTML = cardMarkup(item, true);
    els.recommendations.append(article);
  });
}

function renderFilters() {
  els.filterRow.innerHTML = "";
  filters.forEach((filter) => {
    const button = document.createElement("button");
    button.className = `filter-chip${state.activeFilter === filter.tag ? " is-active" : ""}`;
    button.type = "button";
    button.textContent = filter.label;
    button.addEventListener("click", () => {
      state.activeFilter = filter.tag;
      renderGallery();
      renderFilters();
    });
    els.filterRow.append(button);
  });
}

function renderGallery() {
  els.galleryGrid.innerHTML = "";
  const visible = state.activeFilter === "all"
    ? items
    : items.filter((item) => item.tags.includes(state.activeFilter));
  visible.forEach((item) => {
    const article = document.createElement("article");
    article.className = "gallery-card";
    article.innerHTML = cardMarkup(item);
    els.galleryGrid.append(article);
  });
}

function openPreview(itemId) {
  const item = items.find((entry) => entry.id === itemId);
  if (!item) return;
  els.previewImage.src = item.src;
  els.previewImage.alt = item.title;
  els.previewTitle.textContent = item.title;
  els.previewDescription.textContent = item.description;
  if (typeof els.dialog.showModal === "function") {
    els.dialog.showModal();
  }
}

function resetQuiz() {
  state.step = 0;
  state.answers = [];
  render();
}

function goBack() {
  if (state.answers.length === 0) return;
  state.answers.pop();
  state.step = state.answers.length;
  render();
}

function bindEvents() {
  els.backButton.addEventListener("click", goBack);
  els.resetButton.addEventListener("click", resetQuiz);
  els.closePreview.addEventListener("click", () => els.dialog.close());
  els.dialog.addEventListener("click", (event) => {
    if (event.target === els.dialog) els.dialog.close();
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-preview]");
    if (!button) return;
    openPreview(button.dataset.preview);
  });
}

function render() {
  renderQuestion();
  renderTrail();
  renderRecommendations();
}

bindEvents();
renderFilters();
renderGallery();
render();
