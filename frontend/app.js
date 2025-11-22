const API_BASE = "http://localhost:8000";
let icons = [];
let categories = [];
let activeCategoryId = null;

const gridEl = document.getElementById("icon-grid");
const searchInput = document.getElementById("search-input");
const resultsCount = document.getElementById("results-count");
const clearSearch = document.getElementById("clear-search");
const filtersPanel = document.getElementById("filters");
const collapseBtn = document.getElementById("collapse-filters");
const tabsEl = document.getElementById("tabs");
const resetFilterBtn = document.getElementById("reset-filter");

function renderGrid(items) {
  gridEl.innerHTML = "";
  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="icon-tile"><img src="${item.image}" alt="${item.label}" /></div>
      <div class="icon-label">${item.label}</div>
      <div class="icon-meta">${item.category || "—"} · ${item.state || "—"}</div>
      <div class="icon-meta">Price: $${item.price}</div>
    `;
    gridEl.appendChild(card);
  });
  resultsCount.textContent = `${items.length} Items`;
}

function applyFilter() {
  const query = searchInput.value.toLowerCase().trim();
  const filtered = icons.filter((icon) =>
    icon.label.toLowerCase().includes(query)
  );
  renderGrid(filtered);
}

searchInput.addEventListener("input", applyFilter);

clearSearch.addEventListener("click", () => {
  searchInput.value = "";
  applyFilter();
  searchInput.focus();
});

collapseBtn.addEventListener("click", () => {
  filtersPanel.classList.toggle("hidden");
  collapseBtn.textContent = filtersPanel.classList.contains("hidden")
    ? "Show"
    : "Hide";
});

resetFilterBtn.addEventListener("click", () => {
  activeCategoryId = null;
  setActiveTab(null);
  loadItems();
});

function renderTabs(list) {
  tabsEl.innerHTML = "";
  const allBtn = document.createElement("button");
  allBtn.className = "tab" + (activeCategoryId === null ? " active" : "");
  allBtn.textContent = "All";
  allBtn.addEventListener("click", () => {
    activeCategoryId = null;
    setActiveTab(null);
    loadItems();
  });
  tabsEl.appendChild(allBtn);

  list.forEach((cat) => {
    const btn = document.createElement("button");
    btn.className = "tab" + (cat.id === activeCategoryId ? " active" : "");
    btn.textContent = cat.name;
    btn.dataset.id = cat.id;
    btn.addEventListener("click", () => {
      activeCategoryId = cat.id;
      setActiveTab(cat.id);
      loadItems();
    });
    tabsEl.appendChild(btn);
  });
}

function setActiveTab(catId) {
  Array.from(tabsEl.children).forEach((btn) => {
    if (catId === null && btn.textContent === "All") {
      btn.classList.add("active");
    } else if (btn.dataset.id && Number(btn.dataset.id) === catId) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });
}

async function loadItems() {
  try {
    const url =
      activeCategoryId === null
        ? `${API_BASE}/items`
        : `${API_BASE}/items?category_id=${activeCategoryId}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load items");
    const data = await res.json();
    icons = data.map((item) => ({
      id: item.id,
      label: item.name,
      price: item.price,
      category: item.category.name,
      state: item.category.state,
      image: pickImage(item.category.name),
    }));
    renderGrid(icons);
  } catch (err) {
    console.error(err);
    gridEl.innerHTML = `<div style="color:#c00;">Error loading items</div>`;
  }
}

function slugify(name) {
  return name.toLowerCase().replace(/\s+/g, "-");
}

function pickImage(categoryName) {
  const slug = slugify(categoryName);
  return `assets/${slug}/icon.svg`;
}

async function init() {
  try {
    const res = await fetch(`${API_BASE}/categories`);
    if (!res.ok) throw new Error("Failed to load categories");
    categories = await res.json();
    renderTabs(categories);
    await loadItems();
  } catch (err) {
    console.error(err);
    tabsEl.innerHTML = `<span style="color:#c00;">Failed to load categories</span>`;
  }
}

init();
