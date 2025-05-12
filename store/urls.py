from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ---------------- Home & Authentication ----------------
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='store/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('otp-verify/', views.otp_verify_view, name='otp_verify'),
    path('password-reset/', views.custom_password_reset_view, name='password_reset'),

    # ---------------- Product ----------------
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/review/', views.submit_review, name='submit_review'),
    path('products/', views.product_list, name='product_list'),

    # ---------------- Cart ----------------
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),

    # ---------------- Checkout & Payment ----------------
    path('checkout/', views.checkout_view, name='checkout'),
    path('payment/', views.payment_initiate, name='payment_initiate'),
    path('payment-handler/', views.payment_handler, name='payment_handler'),
    path('payment/webhook/', views.razorpay_webhook, name='razorpay_webhook'),
    path('payment-success/', views.payment_success, name='payment_success'),

    # ---------------- Orders ----------------
    path('orders/', views.my_orders, name='my_orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),

    # ---------------- Profile ----------------
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),

    # ---------------- Wishlist ----------------
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),

    # ---------------- Utilities ----------------
    path('invoice/<int:order_id>/', views.download_invoice, name='download_invoice'),
    path('upload-products/', views.upload_products_csv, name='upload_products_csv'),
]
