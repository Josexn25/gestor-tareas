const searchInput = document.querySelector("#search");
const taskItems = Array.from(document.querySelectorAll(".task-item"));
const noResults = document.querySelector("#no-results");

function filterTasks() {
  const query = searchInput.value.trim().toLowerCase();
  let visibleCount = 0;

  taskItems.forEach((item) => {
    const content = item.dataset.search.toLowerCase();
    const isVisible = content.includes(query);
    item.classList.toggle("is-hidden", !isVisible);

    if (isVisible) {
      visibleCount += 1;
    }
  });

  if (noResults) {
    noResults.classList.toggle("is-hidden", visibleCount > 0);
  }
}

if (searchInput) {
  searchInput.addEventListener("input", filterTasks);
}
