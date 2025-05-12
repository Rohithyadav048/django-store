from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.template.loader import get_template
from django.core.mail import send_mail
from django.utils import timezone
from django.core.files.base import ContentFile
from django.db import transaction
from .forms import ReviewForm, AddressForm, ProfileForm, CSVUploadForm

from xhtml2pdf import pisa
from io import BytesIO
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP
import csv
import json
import hmac
import hashlib
import razorpay
import os
import requests
import logging

from .models import (
    Product, CartItem, Address, Order, OrderItem, Wishlist,Profile,Category, Review,
    Coupon, Shipment, ProductVariant
)
from .utils import send_order_confirmation_email

# Initialize logger

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
logger = logging.getLogger(__name__)

# ------------- Home & Authentication Views -------------

def home(request):
    products = Product.objects.all()
    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query)
    return render(request, 'store/home.html', {'products': products})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully. You can now log in.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreationForm()
    return render(request, 'store/register.html', {'form': form})

def custom_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')

def otp_verify_view(request):
    if request.method == 'POST':
        otp = request.POST.get('otp')
        username = request.POST.get('username')
        if otp == '1234':
            user = User.objects.filter(username=username).first()
            if user:
                login(request, user)
                messages.success(request, "OTP verified. Logged in successfully.")
                return redirect('payment')
            return HttpResponse("User not found", status=404)
        return HttpResponse("Invalid OTP", status=400)
    return render(request, 'store/otp_verify.html', {'username': request.GET.get('username')})

def custom_password_reset_view(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(
                request=request,
                use_https=True,
                from_email="your-email@example.com",
                subject_template_name="registration/password_reset_subject.txt",
                email_template_name="registration/password_reset_email.html",
            )
            return HttpResponse("Password reset email sent!")
    else:
        form = PasswordResetForm()
    return render(request, "registration/password_reset_form.html", {"form": form})

# ------------- Product Views -------------

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists() if request.user.is_authenticated else False
    variants = ProductVariant.objects.filter(product=product)
    return render(request, 'store/product_detail.html', {
        'product': product,
        'in_wishlist': in_wishlist,
        'variants': variants
    })

@login_required
def upload_products_csv(request):
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            decoded = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded)

            if not reader.fieldnames or 'name' not in reader.fieldnames:
                messages.error(request, "Invalid CSV format. 'name' field is required.")
                return redirect('upload_products_csv')

            products = []
            for row in reader:
                category, _ = Category.objects.get_or_create(name=row.get('category', 'Uncategorized'))
                base_slug = slugify(row['name'])
                slug = base_slug
                counter = 1
                while Product.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                product = Product(
                    name=row['name'],
                    price = Decimal(row.get('price', '0').strip() or '0'),
                    description=row.get('description', ''),
                    category=category,
                    stock=int(row.get('stock', 0)),
                    is_available=row.get('is_available', '').lower() == 'true',
                    slug=slug,
                )

                image_url = row.get('image', '').strip()
                if image_url:
                    try:
                        response = requests.get(image_url, timeout=10)
                        if response.status_code == 200 and 'image' in response.headers['Content-Type']:
                            image_name = os.path.basename(image_url.split("?")[0])
                            product.image.save(image_name, ContentFile(response.content), save=False)
                        else:
                            logger.error(f"Invalid image URL (non-image content): {image_url}")
                            messages.warning(request, f"Invalid image URL for {row['name']}. Skipping image download.")
                    except Exception as e:
                        logger.error(f"Image download failed for {image_url}: {e}")
                        messages.warning(request, f"Failed to download image for {row['name']}.")

                products.append(product)

            try:
                Product.objects.bulk_create(products)
                messages.success(request, "Products uploaded successfully.")
            except Exception as e:
                logger.error(f"Error while bulk creating products: {e}")
                messages.error(request, "An error occurred while uploading products. Please try again.")

            return redirect('home')
    else:
        form = CSVUploadForm()

    return render(request, 'store/upload_csv.html', {'form': form})


def product_list(request):
    query = request.GET.get('q')
    category_id = request.GET.get('category')

    products = Product.objects.all()

    if query:
        products = products.filter(name__icontains=query)

    if category_id:
        products = products.filter(category_id=category_id)

    categories = Category.objects.all()
    return render(request, 'store/product_list.html', {
        'products': products,
        'categories': categories
    })

# ------------- Cart Views -------------

@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)
    if not created:
        cart_item.quantity += quantity
    cart_item.save()
    messages.success(request, "Item added to cart.")
    return redirect('cart')

@login_required
def cart_view(request):
    cart_items = CartItem.objects.filter(user=request.user).select_related('product')
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total': total,
        'cart_empty': not cart_items.exists()
    })

@login_required
@require_POST
def update_cart(request):
    cart_items = CartItem.objects.filter(user=request.user)
    for item in cart_items:
        quantity = int(request.POST.get(f'quantity_{item.id}', 1))
        item.quantity = max(1, quantity)
        item.save()
    messages.info(request, "Cart updated.")
    return redirect('cart')

@login_required
def remove_from_cart(request, item_id):
    get_object_or_404(CartItem, id=item_id, user=request.user).delete()
    messages.success(request, "Item removed from cart.")
    return redirect('cart')

@login_required
def buy_now(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    request.session['buy_now_item'] = {
        'product_id': product.id,
        'price': str(product.price),
        'quantity': 1
    }
    return redirect('checkout')

# ------------- Checkout Views -------------

@login_required
def checkout_view(request):
    buy_now_item = request.session.get('buy_now_item')
    cart_items = []
    total = Decimal('0.00')

    if buy_now_item:
        # "Buy Now" flow
        product = get_object_or_404(Product, id=buy_now_item['product_id'])
        quantity = int(buy_now_item['quantity'])
        price = Decimal(str(buy_now_item['price']))
        total = price * quantity
        cart_items = [{
            'product': product,
            'quantity': quantity,
            'price': price
        }]
    else:
        # Normal cart checkout
        cart_items = CartItem.objects.filter(user=request.user)
        total = sum(
            Decimal(str(item.product.price)) * item.quantity for item in cart_items
        ) or Decimal('0.00')

    # Round total to 2 decimal places
    total = total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    form = AddressForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        if not cart_items:
            messages.error(request, "Your cart is empty.")
            return redirect('cart')

        if total < Decimal('1.00'):
            messages.error(request, "Minimum order amount must be ₹1.00.")
            return render(request, 'store/checkout.html', {
                'items': cart_items,
                'total': total,
                'form': form
            })

        # Save shipping address
        address = form.save(commit=False)
        address.user = request.user
        address.address_type = 'shipping'
        address.save()

        # Create new order
        order = Order.objects.create(
            user=request.user,
            shipping_address=address,
            total_price=total
        )

        # Create order items
        if buy_now_item:
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity
            )
            del request.session['buy_now_item']  # Clear buy now session
        else:
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity
                )
            CartItem.objects.filter(user=request.user).delete()  # Clear cart

        # Save order ID to session for use in payment
        request.session['order_id'] = order.id

        return redirect('payment_initiate')

    return render(request, 'store/checkout.html', {
        'items': cart_items,
        'total': total,
        'form': form
    })

# ------------- Order Views -------------

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/my_orders.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = order.items.select_related('product')
    shipment = Shipment.objects.filter(order=order).first()
    return render(request, 'store/order_detail.html', {
        'order': order,
        'items': items,
        'total_price': order.total_price,
        'shipment': shipment
    })

@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    template = get_template('store/invoice_template.html')
    html = template.render({'order': order, 'user': request.user})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response

# ------------- Profile Views -------------
@login_required
def profile_view(request):
    return render(request, 'store/profile.html')

@login_required
def profile_edit(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('profile')
    return render(request, 'store/profile_edit.html')

# ------------- Wishlist -------------

@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, 'store/wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.get_or_create(user=request.user, product=product)
    messages.success(request, "Added to wishlist.")
    return redirect('product_detail', slug=product.slug)

@login_required
def remove_from_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.filter(user=request.user, product=product).delete()
    messages.info(request, "Removed from wishlist.")
    return redirect('product_detail', slug=product.slug)



# ------------- Review -------------

@login_required
def submit_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, "Review submitted.")
            return redirect('product_detail', slug=product.slug)
    else:
        form = ReviewForm()
    return render(request, 'store/submit_review.html', {'form': form, 'product': product})

# ------------- Coupon Application -------------

@login_required
def apply_coupon(request):
    code = request.POST.get('coupon_code')
    try:
        coupon = Coupon.objects.get(code__iexact=code, active=True)
        request.session['coupon_id'] = coupon.id
        messages.success(request, f"Coupon '{coupon.code}' applied successfully!")
    except Coupon.DoesNotExist:
        messages.error(request, "Invalid coupon code.")
    return redirect('cart')


# ------------------- Initiate Payment View -------------------
@login_required
def payment_initiate(request):
    try:
        order_id = request.session.get('order_id')
        if not order_id:
            messages.error(request, "No active order found. Please try checking out again.")
            return redirect('cart')

        order = get_object_or_404(Order, id=order_id, user=request.user, is_paid=False)

        if not order.items.exists():
            messages.error(request, "Your order has no items.")
            return redirect('cart')

        # Ensure the total price is accurate
        order.update_total_price()

        # Convert amount to paise
        amount = int((order.total_price * Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

        if amount < 100:
            logger.warning(f"Order amount too low for Razorpay: ₹{order.total_price} → {amount} paise")
            messages.error(request, "Order total must be at least ₹1.00 to proceed with payment.")
            return redirect('cart')

        # Create Razorpay order
        razorpay_order = razorpay_client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": '1'
        })

        # Save Razorpay order ID to the Order model
        order.razorpay_order_id = razorpay_order['id']
        order.save()

        context = {
            "razorpay_order_id": razorpay_order['id'],
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "amount": amount,  # in paise for Razorpay
            "amount_rupees": float(order.total_price),  # for display
            "user": request.user
        }

        return render(request, 'store/payment.html', context)

    except Exception as e:
        logger.error(f"Error initiating payment: {e}")
        messages.error(request, "Something went wrong while initiating the payment. Please try again.")
        return redirect('cart')

# ------------------- Payment Handler View -------------------
@csrf_exempt
def payment_handler(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            razorpay_payment_id = data.get('razorpay_payment_id')
            razorpay_order_id = data.get('razorpay_order_id')
            razorpay_signature = data.get('razorpay_signature')

            logger.info(f"Received Razorpay data: Order ID: {razorpay_order_id}, Payment ID: {razorpay_payment_id}")

            if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
                logger.error("Missing Razorpay parameters.")
                return JsonResponse({'status': 'error', 'message': 'Incomplete payment details.'}, status=400)

            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }

            razorpay_client.utility.verify_payment_signature(params_dict)

            order = Order.objects.filter(razorpay_order_id=razorpay_order_id).first()
            if not order:
                logger.error(f"No order found with Razorpay Order ID: {razorpay_order_id}")
                return JsonResponse({'status': 'error', 'message': 'Order not found.'}, status=404)

            if order.is_paid:
                return JsonResponse({'status': 'success', 'message': 'Order already marked as paid.'})

            # ✅ Mark as paid
            order.is_paid = True
            order.status = 'paid'
            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_signature = razorpay_signature
            order.save()

            # ✅ Clear user's cart
            CartItem.objects.filter(user=order.user).delete()

            return JsonResponse({'status': 'success'})

        except razorpay.errors.SignatureVerificationError as e:
            logger.error(f"Signature verification failed: {e}")
            return JsonResponse({'status': 'error', 'message': 'Invalid signature'}, status=400)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

        except Exception as e:
            logger.error(f"Payment handler error: {e}")
            return JsonResponse({'status': 'error', 'message': 'Internal error'}, status=500)

    return HttpResponseBadRequest("Invalid request method")

# ------------------- Payment Success Page -------------------
@login_required
def payment_success(request):
    return render(request, 'store/payment_success.html')

# ------------------- Razorpay Webhook -------------------
@csrf_exempt
def razorpay_webhook(request):
    if request.method == 'POST':
        data = request.body
        try:
            signature = request.headers.get('X-Razorpay-Signature')
            secret = settings.RAZORPAY_WEBHOOK_SECRET  # Ensure this is set in your settings

            expected_signature = hmac.new(
                key=bytes(secret, 'utf-8'),
                msg=data,
                digestmod=hashlib.sha256
            ).hexdigest()

            if hmac.compare_digest(expected_signature, signature):
                payload = json.loads(data)
                event = payload.get('event')

                if event == 'payment.captured':
                    razorpay_order_id = payload['payload']['payment']['entity']['order_id']
                    payment_id = payload['payload']['payment']['entity']['id']

                    order = Order.objects.filter(razorpay_order_id=razorpay_order_id).first()
                    if order and not order.is_paid:
                        order.is_paid = True
                        order.status = 'paid'
                        order.razorpay_payment_id = payment_id
                        order.save()
                        CartItem.objects.filter(user=order.user).delete()

                        logger.info(f"Payment captured via webhook for Order {order.id}")
                    return JsonResponse({'status': 'ok'})
                else:
                    logger.info(f"Ignored event: {event}")
                    return JsonResponse({'status': 'ignored', 'event': event})
            else:
                logger.warning("Invalid webhook signature")
                return JsonResponse({'status': 'error', 'message': 'Invalid signature'}, status=400)

        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return JsonResponse({'status': 'error', 'message': 'Webhook processing failed'}, status=500)
    return HttpResponseBadRequest("Invalid request method")


# ------------- Admin Utility -------------

@login_required
def shipment_tracking_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    shipment = Shipment.objects.filter(order=order).first()
    if not shipment:
        messages.error(request, "No shipment information available.")
        return redirect('order_detail', order_id=order_id)
    
    return render(request, 'store/shipment_tracking.html', {
        'shipment': shipment,
        'order': order,
    })
