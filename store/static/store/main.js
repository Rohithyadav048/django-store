document.addEventListener("DOMContentLoaded", () => {
    // Navbar shrink effect on scroll
    const navbar = document.getElementById("navbar");
    if (navbar) {
        window.addEventListener("scroll", () => {
            if (window.scrollY > 50) {
                if (navbar.classList) {
                    navbar.classList.add("navbar-shrink", "scrolled");
                }
            } else {
                if (navbar.classList) {
                    navbar.classList.remove("navbar-shrink", "scrolled");
                }
            }
        });
    }

    // Add to Cart Button functionality
    const addToCartBtn = document.getElementById('add-to-cart-btn');
    if (addToCartBtn) {
        addToCartBtn.addEventListener('click', function () {
            const productId = this.getAttribute('data-product-id');

            fetch(`/add-to-cart/${productId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                    'Content-Type': 'application/json',
                },
            })
            .then(response => {
                if (response.ok) {
                    showToast('Product added to cart!');
                } else if (response.status === 403) {
                    showToast('Please login first!');
                } else {
                    showToast('Something went wrong!');
                }
            })
            .catch(error => {
                console.error('Error adding to cart:', error);
                showToast('An error occurred.');
            });
        });
    }

    // Razorpay button logic
    const razorpayButton = document.getElementById('rzp-button');
    if (razorpayButton) {
        razorpayButton.addEventListener('click', function (e) {
            e.preventDefault();

            const options = {
                key: razorpayButton.dataset.key,
                amount: razorpayButton.dataset.amount,
                currency: "INR",
                name: "Your Store Name",
                description: "Order Payment",
                order_id: razorpayButton.dataset.orderId,
                handler: function (response) {
                    fetch('/payment-handler/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCSRFToken(),
                        },
                        body: JSON.stringify({
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_signature: response.razorpay_signature,
                        })
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === 'success') {
                            window.location.href = '/payment-success/';
                        } else {
                            showToast('Payment failed: ' + (data.reason || 'Unknown error'));
                        }
                    })
                    .catch(err => {
                        console.error('Payment error:', err);
                        showToast('Payment processing error.');
                    });
                },
                prefill: {
                    name: razorpayButton.dataset.name,
                    email: razorpayButton.dataset.email
                },
                theme: {
                    color: "#3399cc"
                }
            };

            const rzp = new Razorpay(options);
            rzp.open();
        });
    }
});

// Helper to get CSRF token from cookies
function getCSRFToken() {
    let csrfToken = null;
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        if (cookie.trim().startsWith('csrftoken=')) {
            csrfToken = cookie.trim().substring('csrftoken='.length);
            break;
        }
    }
    return csrfToken;
}

// Display temporary toast message
function showToast(message) {
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) return;

    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-bg-success border-0 show mb-2';
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.classList.remove('show');
        toast.remove();
    }, 3000);
}
