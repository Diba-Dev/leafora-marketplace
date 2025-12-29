// -----------------------------
// Frontend Login State
// -----------------------------


// Load navbar & footer
function loadComponent(id, file) {
    fetch(file)
        .then(res => res.text())
        .then(data => {
            document.getElementById(id).innerHTML = data;
            updateAuthButton(); // important
        });
}


// -----------------------------
// Live Price Range Update
// -----------------------------

document.addEventListener("DOMContentLoaded", () => {
    const priceRange = document.getElementById("priceRange");
    const priceValue = document.getElementById("priceValue");

    if (priceRange && priceValue) {
        // Initial display
        priceValue.textContent = priceRange.value + " BDT";

        // Update on slider move
        priceRange.addEventListener("input", () => {
            priceValue.textContent = priceRange.value + " BDT";
        });
    }
});


// -----------------------------
// Open Receipt on Order Click
// -----------------------------
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".order-row").forEach(row => {
        row.addEventListener("click", () => {
            const receiptURL = row.dataset.receipt;
            if (receiptURL) {
                window.location.href = receiptURL;
            }
        });
    });
});



// -----------------------------
// Contact Form Dummy Submit
// -----------------------------
const contactForm = document.getElementById("contactForm");
if (contactForm) {
    contactForm.addEventListener("submit", (e) => {
        e.preventDefault();
        alert("Message sent! (frontend only)");
        contactForm.reset();
    });
}

// -----------------------------
// Admin Actions: Promote / Delete
// -----------------------------
document.querySelectorAll(".promote-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        alert("User promoted to Admin! (frontend only)");
    });
});

document.querySelectorAll(".delete-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        if (confirm("Are you sure you want to delete?")) {
            alert("Deleted successfully! (frontend only)");
        }
    });
});

// -----------------------------
// User Table Filter
// -----------------------------
const userSearch = document.getElementById("userSearch");
if (userSearch) {
    userSearch.addEventListener("input", () => {
        const filter = userSearch.value.toLowerCase();
        document.querySelectorAll(".admin-table tbody tr").forEach(row => {
            const text = row.innerText.toLowerCase();
            row.style.display = text.includes(filter) ? "" : "none";
        });
    });
}

// -----------------------------
// Book Table Filter
// -----------------------------
const bookSearch = document.getElementById("bookSearch");
if (bookSearch) {
    bookSearch.addEventListener("input", () => {
        const filter = bookSearch.value.toLowerCase();
        document.querySelectorAll("#booksTable tbody tr").forEach(row => {
            const text = row.innerText.toLowerCase();
            row.style.display = text.includes(filter) ? "" : "none";
        });
    });
}


// -----------------------------
// Flash Message Auto Dismiss
// -----------------------------
document.addEventListener("DOMContentLoaded", () => {
    const flashes = document.querySelectorAll(".flash");

    flashes.forEach(flash => {
        setTimeout(() => {
            flash.style.opacity = "0";
            flash.style.transform = "translateX(40px)";
            flash.style.transition = "all 0.4s ease";

            setTimeout(() => {
                flash.remove();
            }, 400);
        }, 1500); // visible for 1.5 seconds
    });
});


document.addEventListener("DOMContentLoaded", () => {
    const filterForm = document.getElementById("filterForm");
    const booksGrid = document.getElementById("booksGrid");

    if (filterForm && booksGrid) {
        filterForm.addEventListener("submit", (e) => {
            e.preventDefault();

            const formData = new FormData(filterForm);
            const queryString = new URLSearchParams(formData).toString();

            fetch("/books_ajax?" + queryString)
                .then(res => res.text())
                .then(html => {
                    booksGrid.innerHTML = html;
                })
                .catch(err => console.error(err));
        });
    }
});
