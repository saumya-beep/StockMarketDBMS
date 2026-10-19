
document.addEventListener("DOMContentLoaded", function () {
    // Market Watch: search, sector filter, and sorting
    const searchInput = document.getElementById("stockSearch");
    const sectorFilter = document.getElementById("sectorFilter");
    const stockSort = document.getElementById("stockSort");

    const stockTable = document.querySelector(".table-wrap tbody");
    const stockRows = stockTable
        ? Array.from(stockTable.querySelectorAll("[data-stock-row]"))
        : [];
        
const resultCount = document.getElementById("stockResultCount");
const clearFiltersButton = document.getElementById("clearStockFilters");
const tableBody = document.getElementById("stockTableBody");

let noResultsRow = null;


if (clearFiltersButton) {
    clearFiltersButton.addEventListener("click", function () {
        if (searchInput) searchInput.value = "";
        if (sectorFilter) sectorFilter.value = "";
        if (stockSort) stockSort.value = "symbol-asc";

        updateMarketWatch();
    });
}


    function updateMarketWatch() {
        const query = searchInput
            ? searchInput.value.toLowerCase().trim()
            : "";

        const selectedSector = sectorFilter
            ? sectorFilter.value.toLowerCase()
            : "";

        const sortOption = stockSort
            ? stockSort.value
            : "symbol-asc";

        // Apply search and sector filtering.
        stockRows.forEach(function (row) {
            const symbol = row.dataset.symbol || "";
            const company = row.dataset.company || "";
            const sector = row.dataset.sector || "other";

            const matchesSearch =
                symbol.includes(query) || company.includes(query) || sector.includes(query);

            const matchesSector =
                !selectedSector || sector === selectedSector;

            row.style.display =
                matchesSearch && matchesSector ? "" : "none";
        });

        // Sort the existing rows without changing their form actions.
        const visibleRows = stockRows
            .filter(function (row) {
                return row.style.display !== "none";
            });

        visibleRows.sort(function (a, b) {
            const symbolA = a.dataset.symbol || "";
            const symbolB = b.dataset.symbol || "";
            const sectorA = a.dataset.sector || "other";
            const sectorB = b.dataset.sector || "other";
            const priceA = Number(a.dataset.price || 0);
            const priceB = Number(b.dataset.price || 0);

            switch (sortOption) {
                case "symbol-desc":
                    return symbolB.localeCompare(symbolA);

                case "price-asc":
                    return priceA - priceB;

                case "price-desc":
                    return priceB - priceA;

                case "sector-asc":
                    return (
                        sectorA.localeCompare(sectorB) ||
                        symbolA.localeCompare(symbolB)
                    );

                case "symbol-asc":
                default:
                    return symbolA.localeCompare(symbolB);
            }
        });

        // Reorder only stock rows. Other table messages remain untouched.
        visibleRows.forEach(function (row) {
            stockTable.appendChild(row);
        });

        // Keep hidden rows in the table so later filters can restore them.
        stockRows
            .filter(function (row) {
                return row.style.display === "none";
            })
            .forEach(function (row) {
                stockTable.appendChild(row);
            });
            
// Update the visible stock count.
const visibleCount = stockRows.filter(function (row) {
    return row.style.display !== "none";
}).length;

if (resultCount) {
    resultCount.textContent =
        "Showing " + visibleCount + " of " +
        stockRows.length + " stocks";
}

// Show or remove the no-results message.
if (visibleCount === 0 && tableBody) {
    if (!noResultsRow) {
        noResultsRow = document.createElement("tr");

        const cell = document.createElement("td");
        cell.colSpan = 4;
        cell.className = "empty-state";
        cell.textContent =
            "No stocks match your filters. Try another search or sector.";

        noResultsRow.appendChild(cell);
    }

    tableBody.appendChild(noResultsRow);
} else if (noResultsRow) {
    noResultsRow.remove();
    noResultsRow = null;
}

    }

    if (searchInput) {
        searchInput.addEventListener("input", updateMarketWatch);
    }

    if (sectorFilter) {
        sectorFilter.addEventListener("change", updateMarketWatch);
    }

    if (stockSort) {
        stockSort.addEventListener("change", updateMarketWatch);
    }

    updateMarketWatch();

    // Confirm trades before submitting, for forms using data-trade-form.
    document.querySelectorAll("form[data-trade-form]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const action = form.querySelector('[name="order_type"]');
            const quantity = form.querySelector('[name="quantity"]');

            if (!action || !quantity) {
                return;
            }

            const type = action.value.toUpperCase();
            const qty = Number(quantity.value);

            if (!Number.isInteger(qty) || qty <= 0) {
                event.preventDefault();
                alert("Please enter a valid positive whole-number quantity.");
                return;
            }

            if (!window.confirm(
                "Confirm " + type + " order for " + qty + " shares?"
            )) {
                event.preventDefault();
            }
        });
    });

    // Automatically dismiss flash messages after five seconds.
    document.querySelectorAll("[data-auto-dismiss]").forEach(function (message) {
        window.setTimeout(function () {
            message.style.transition = "opacity 0.4s ease";
            message.style.opacity = "0";

            window.setTimeout(function () {
                message.remove();
            }, 450);
        }, 5000);
    });
});

// Retain the reusable filter helper for other pages.
function filterTable(inputId, rowSelector) {
    const input = document.getElementById(inputId);

    if (!input) {
        return;
    }

    input.addEventListener("input", function () {
        const query = input.value.toLowerCase().trim();

        document.querySelectorAll(rowSelector).forEach(function (row) {
            row.style.display =
                row.textContent.toLowerCase().includes(query) ? "" : "none";
        });
    });
}

