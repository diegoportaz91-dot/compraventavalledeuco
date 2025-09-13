// Main JavaScript for MarketplaceVUco
document.addEventListener("DOMContentLoaded", function () {
    // Initialize offer modal functionality
    initializeOfferModal();

    // Initialize smooth scrolling for anchor links
    initializeSmoothScrolling();

    // Initialize lazy loading for images
    initializeLazyLoading();

    // Initialize tooltips if any
    initializeTooltips();

    // Initialize search and filter functionality
    initializeSearchAndFilters();
    
    // Initialize delete vehicle functionality
    initializeDeleteVehicle();
    
    // Initialize approve request functionality
    initializeApproveRequest();
});

// Offer Modal Functionality
function initializeOfferModal() {
    const offerModal = document.getElementById("offerModal");
    if (!offerModal) return;

    const modal = new bootstrap.Modal(offerModal);
    const offerButtons = document.querySelectorAll(".offer-btn");
    const sendOfferBtn = document.getElementById("sendOfferBtn");
    const offerAmountInput = document.getElementById("offerAmount");
    const vehicleTitleSpan = document.getElementById("offerVehicleTitle");
    const vehiclePriceSpan = document.getElementById("offerVehiclePrice");

    let currentVehicleId = null;

    // Handle offer button clicks
    offerButtons.forEach((button) => {
        button.addEventListener("click", function () {
            currentVehicleId = this.dataset.vehicleId;
            const vehicleTitle = this.dataset.vehicleTitle;
            const vehiclePrice = parseInt(this.dataset.vehiclePrice);

            // Update modal content
            vehicleTitleSpan.textContent = vehicleTitle;
            vehiclePriceSpan.textContent = formatPrice(vehiclePrice) + " ARS";

            // Clear previous offer amount
            offerAmountInput.value = "";

            // Show modal
            modal.show();
        });
    });

    // Handle send offer button
    if (sendOfferBtn) {
        sendOfferBtn.addEventListener("click", function () {
            const offerAmount = parseInt(offerAmountInput.value);

            if (!offerAmount || offerAmount <= 0) {
                alert("Por favor ingresa una oferta válida");
                return;
            }

            if (!currentVehicleId) {
                alert("Error: No se pudo identificar el vehículo");
                return;
            }

            // Add loading state
            this.classList.add("loading");
            this.disabled = true;

            // Redirect to track click with offer amount
            const trackUrl = `/track_click/${currentVehicleId}/offer?offer=${offerAmount}`;
            window.open(trackUrl, "_blank");

            // Close modal after a short delay
            setTimeout(() => {
                modal.hide();
                this.classList.remove("loading");
                this.disabled = false;
            }, 1000);
        });
    }

    // Handle Enter key in offer amount input
    if (offerAmountInput) {
        offerAmountInput.addEventListener("keypress", function (e) {
            if (e.key === "Enter") {
                sendOfferBtn.click();
            }
        });

        // Format offer amount as user types
        offerAmountInput.addEventListener("input", function () {
            const value = this.value.replace(/\D/g, ""); // Remove non-digits
            if (value) {
                this.value = value;
            }
        });
    }
}

// Format price function
function formatPrice(price) {
    return "$" + price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

// Smooth scrolling for anchor links
function initializeSmoothScrolling() {
    const links = document.querySelectorAll('a[href^="#"]');

    links.forEach((link) => {
        link.addEventListener("click", function (e) {
            const targetId = this.getAttribute("href");
            const targetElement = document.querySelector(targetId);

            if (targetElement) {
                e.preventDefault();
                targetElement.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                });
            }
        });
    });
}

// Lazy loading for images
function initializeLazyLoading() {
    const images = document.querySelectorAll("img[data-src]");

    if ("IntersectionObserver" in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute("data-src");
                    imageObserver.unobserve(img);
                }
            });
        });

        images.forEach((img) => imageObserver.observe(img));
    } else {
        // Fallback for browsers without IntersectionObserver
        images.forEach((img) => {
            img.src = img.dataset.src;
            img.removeAttribute("data-src");
        });
    }
}

// Initialize tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]'),
    );
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Handle image loading errors
function handleImageError(img) {
    img.src = "/static/placeholder-car.png";
}

// Global error handler for images
document.addEventListener(
    "error",
    function (e) {
        if (e.target.tagName === "IMG") {
            handleImageError(e.target);
        }
    },
    true,
);

// Add loading states to buttons
document.addEventListener("click", function (e) {
    if (
        e.target.matches(".btn[href]") &&
        !e.target.matches('.btn[href^="#"]')
    ) {
        e.target.classList.add("loading");

        // Remove loading state after navigation
        setTimeout(() => {
            e.target.classList.remove("loading");
        }, 2000);
    }
});

// Auto-hide alerts after 5 seconds (disabled for permanent banner)
document.addEventListener("DOMContentLoaded", function () {
    const alerts = document.querySelectorAll(
        ".alert:not(.alert-permanent):not(.advertisement-banner-permanent)",
    );

    alerts.forEach((alert) => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Form validation enhancement
document.addEventListener("DOMContentLoaded", function () {
    const forms = document.querySelectorAll(".needs-validation");

    forms.forEach((form) => {
        form.addEventListener("submit", function (e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();

                // Focus on first invalid field
                const firstInvalid = form.querySelector(":invalid");
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            }

            form.classList.add("was-validated");
        });
    });
});

// Statistics auto-refresh for admin dashboard
function refreshStats() {
    if (window.location.pathname === "/admin") {
        // Only refresh if on admin dashboard
        setTimeout(() => {
            window.location.reload();
        }, 300000); // Refresh every 5 minutes
    }
}

// Initialize stats refresh if on admin page
document.addEventListener("DOMContentLoaded", function () {
    if (window.location.pathname === "/admin") {
        refreshStats();
    }
});

// Mobile menu handling
document.addEventListener("DOMContentLoaded", function () {
    const navbarToggler = document.querySelector(".navbar-toggler");
    const navbarCollapse = document.querySelector(".navbar-collapse");

    if (navbarToggler && navbarCollapse) {
        // Close mobile menu when clicking on a link
        navbarCollapse.addEventListener("click", function (e) {
            if (e.target.matches(".nav-link")) {
                const bsCollapse = new bootstrap.Collapse(navbarCollapse, {
                    toggle: false,
                });
                bsCollapse.hide();
            }
        });
    }
});

// Search and Filter Functionality
function initializeSearchAndFilters() {
    const searchForm = document.getElementById("searchForm");
    const filterForm = document.getElementById("filterForm");
    const searchInput = document.getElementById("searchInput");
    const clearFiltersBtn = document.getElementById("clearFilters");

    // Handle search form submission
    if (searchForm) {
        searchForm.addEventListener("submit", function (e) {
            e.preventDefault();
            const searchValue = searchInput.value.trim();
            if (searchValue) {
                // Add search parameter to URL and submit
                const url = new URL(window.location);
                url.searchParams.set("search", searchValue);
                window.location.href = url.toString();
            } else {
                // Clear search if empty
                const url = new URL(window.location);
                url.searchParams.delete("search");
                window.location.href = url.toString();
            }
        });
    }

    // Handle filter form submission
    if (filterForm) {
        filterForm.addEventListener("submit", function (e) {
            e.preventDefault();
            applyFilters();
        });

        // Remove auto-apply on filter changes - now only applies on form submit
        // Filters will only be applied when user clicks "Filtrar" button
    }

    // Handle clear filters button
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener("click", function () {
            clearAllFilters();
        });
    }

    // Handle Enter key in search input
    if (searchInput) {
        searchInput.addEventListener("keypress", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                searchForm.dispatchEvent(new Event("submit"));
            }
        });
    }
}

function applyFilters() {
    const form = document.getElementById("filterForm");
    if (!form) return;

    const formData = new FormData(form);
    const url = new URL(window.location);

    // Clear existing filter parameters
    const filterParams = [
        "search",
        "price_min",
        "price_max",
        "brand",
        "year_min",
        "year_max",
        "location",
        "fuel_type",
        "transmission",
        "km_min",
        "km_max",
    ];
    filterParams.forEach((param) => url.searchParams.delete(param));

    // Add search parameter if exists
    const searchInput = document.getElementById("searchInput");
    if (searchInput && searchInput.value.trim()) {
        url.searchParams.set("search", searchInput.value.trim());
    }

    // Process price range
    const priceRange = formData.get("price_range");
    if (priceRange) {
        const [min, max] = priceRange.split("-").map(Number);
        if (min > 0) url.searchParams.set("price_min", min);
        if (max < 999999999) url.searchParams.set("price_max", max);
    }

    // Process year range
    const yearRange = formData.get("year_range");
    if (yearRange) {
        const [min, max] = yearRange.split("-").map(Number);
        if (min > 0) url.searchParams.set("year_min", min);
        if (max < 9999) url.searchParams.set("year_max", max);
    }

    // Process km range
    const kmRange = formData.get("km_range");
    if (kmRange) {
        const [min, max] = kmRange.split("-").map(Number);
        if (min > 0) url.searchParams.set("km_min", min);
        if (max < 999999999) url.searchParams.set("km_max", max);
    }

    // Add other filters
    const otherFilters = ["brand", "location", "fuel_type", "transmission"];
    otherFilters.forEach((filter) => {
        const value = formData.get(filter);
        if (value) {
            url.searchParams.set(filter, value);
        }
    });

    // Navigate to filtered URL
    window.location.href = url.toString();
}

function clearAllFilters() {
    const url = new URL(window.location);

    // Clear all filter parameters
    const filterParams = [
        "search",
        "price_min",
        "price_max",
        "brand",
        "year_min",
        "year_max",
        "location",
        "fuel_type",
        "transmission",
        "km_min",
        "km_max",
    ];
    filterParams.forEach((param) => url.searchParams.delete(param));

    // Reset form
    const form = document.getElementById("filterForm");
    if (form) {
        form.reset();
    }

    const searchInput = document.getElementById("searchInput");
    if (searchInput) {
        searchInput.value = "";
    }

    // Navigate to clean URL
    window.location.href = url.toString();
}

// Real-time search suggestions (optional enhancement)
function initializeSearchSuggestions() {
    const searchInput = document.getElementById("searchInput");
    if (!searchInput) return;

    let searchTimeout;

    searchInput.addEventListener("input", function () {
        clearTimeout(searchTimeout);
        const query = this.value.trim();

        if (query.length < 2) return;

        searchTimeout = setTimeout(() => {
            fetch(`/api/search?q=${encodeURIComponent(query)}`)
                .then((response) => response.json())
                .then((data) => {
                    // Handle search suggestions if needed
                    console.log("Search results:", data);
                })
                .catch((error) => {
                    console.error("Search error:", error);
                });
        }, 300);
    });
}

// Delete Vehicle Functionality
function initializeDeleteVehicle() {
    // Initialize delete vehicle functionality if elements exist
    if (document.getElementById('deleteVehicleModal')) {
        const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', function() {
                const vehicleId = this.getAttribute('data-vehicle-id');
                if (vehicleId) {
                    deleteVehicle(vehicleId);
                }
            });
        }
    }
}

// Global function for confirming vehicle deletion
function confirmDeleteVehicle(vehicleId, vehicleName) {
    console.log('confirmDeleteVehicle called with:', vehicleId, vehicleName);
    
    const vehicleNameSpan = document.getElementById('vehicleToDelete');
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    const modal = document.getElementById('deleteVehicleModal');
    
    if (vehicleNameSpan && confirmBtn && modal) {
        vehicleNameSpan.textContent = vehicleName;
        confirmBtn.setAttribute('data-vehicle-id', vehicleId);
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    } else {
        console.error('Delete modal elements not found');
    }
}

// Function to delete vehicle
function deleteVehicle(vehicleId) {
    console.log('deleteVehicle called with:', vehicleId);
    fetch(`/admin/delete-vehicle/${vehicleId}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-success alert-dismissible fade show position-fixed';
            alertDiv.style.top = '20px';
            alertDiv.style.right = '20px';
            alertDiv.style.zIndex = '9999';
            alertDiv.innerHTML = `
                <i class="fas fa-check me-2"></i>Vehículo eliminado correctamente
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.body.appendChild(alertDiv);
            
            // Auto remove after 3 seconds
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 3000);
            
            // Close modal and reload page
            const modal = document.getElementById('deleteVehicleModal');
            if (modal) {
                const bootstrapModal = bootstrap.Modal.getInstance(modal);
                if (bootstrapModal) {
                    bootstrapModal.hide();
                }
            }
            
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            alert('Error al eliminar el vehículo: ' + (data.error || 'Error desconocido'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error al eliminar el vehículo');
    });
}

// Approve Request Functionality
function initializeApproveRequest() {
    const approveButtons = document.querySelectorAll('.approve-btn');
    
    approveButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get data from button attributes
            const requestId = this.getAttribute('data-id') || this.getAttribute('data-request-id');
            const requestTitle = this.getAttribute('data-title') || this.getAttribute('data-request-title');
            const publicationType = this.getAttribute('data-type') || this.getAttribute('data-publication-type');
            
            if (!requestId) {
                alert('Error: No se pudo identificar la solicitud');
                return;
            }
            
            // Show confirmation dialog
            const confirmMessage = `¿Estás seguro de que deseas aprobar la solicitud "${requestTitle}"?`;
            
            if (confirm(confirmMessage)) {
                // Add loading state
                this.disabled = true;
                this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Procesando...';
                
                // Determine duration based on publication type
                let duration = 1; // Default 1 month
                if (publicationType === 'premium') {
                    duration = 3; // 3 months for premium
                }
                
                // Make the approval request
                const approveUrl = `/admin/procesar-solicitud/${requestId}/approve?duration=${duration}`;
                
                console.log('Attempting to approve request:', requestId, 'with URL:', approveUrl);
                
                // Use window.location instead of fetch for GET requests with redirects
                window.location.href = approveUrl;
            }
        });
    });
}
