const listingsEl = document.querySelector("#listings");
const emptyStateEl = document.querySelector("#emptyState");
const errorBoxEl = document.querySelector("#errorBox");
const statusTextEl = document.querySelector("#statusText");
const countTextEl = document.querySelector("#countText");
const checkedTextEl = document.querySelector("#checkedText");
const searchInput = document.querySelector("#searchInput");
const tradeFilter = document.querySelector("#tradeFilter");

let allListings = [];

function text(value) {
  return value || "-";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function matchesFilters(listing) {
  const query = searchInput.value.trim().toLowerCase();
  const trade = tradeFilter.value;
  const haystack = [
    listing.name,
    listing.price_text,
    listing.area,
    listing.floor,
    listing.direction,
    listing.realtor,
  ]
    .join(" ")
    .toLowerCase();

  if (trade && listing.trade_type !== trade) return false;
  return !query || haystack.includes(query);
}

function render() {
  const visible = allListings.filter(matchesFilters);
  listingsEl.innerHTML = visible
    .map(
      (listing) => `
        <article class="listing">
          <div>
            <div class="meta">
              <span class="pill">${escapeHtml(text(listing.trade_type))}</span>
            </div>
            <h2>${escapeHtml(text(listing.name))}</h2>
            <div class="meta">
              <span>면적 ${escapeHtml(text(listing.area))}</span>
              <span>층 ${escapeHtml(text(listing.floor))}</span>
              <span>방향 ${escapeHtml(text(listing.direction))}</span>
              <span>중개사 ${escapeHtml(text(listing.realtor))}</span>
              <span>확인일 ${escapeHtml(text(listing.confirmed_at))}</span>
            </div>
          </div>
          <div class="price">
            <strong>${escapeHtml(text(listing.price_text))}</strong>
            <a href="${escapeHtml(listing.link)}" target="_blank" rel="noreferrer">네이버에서 보기</a>
          </div>
        </article>
      `
    )
    .join("");
  emptyStateEl.hidden = visible.length !== 0;
}

async function loadListings() {
  try {
    const response = await fetch(`./listings.json?t=${Date.now()}`, { cache: "no-store" });
    const payload = await response.json();

    checkedTextEl.textContent = payload.checkedAt || "-";
    countTextEl.textContent = String(payload.count ?? 0);

    if (!payload.ok) {
      statusTextEl.textContent = "확인 필요";
      errorBoxEl.hidden = false;
      errorBoxEl.textContent = payload.error || "매물 데이터를 가져오지 못했습니다.";
      allListings = payload.listings || [];
      render();
      return;
    }

    statusTextEl.textContent = "정상";
    errorBoxEl.hidden = true;
    errorBoxEl.textContent = "";
    allListings = payload.listings || [];
    render();
  } catch (error) {
    statusTextEl.textContent = "확인 필요";
    checkedTextEl.textContent = "-";
    countTextEl.textContent = "-";
    errorBoxEl.hidden = false;
    errorBoxEl.textContent = `listings.json을 불러오지 못했습니다: ${error.message}`;
  }
}

searchInput.addEventListener("input", render);
tradeFilter.addEventListener("change", render);
loadListings();
