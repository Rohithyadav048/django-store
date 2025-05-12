from django.contrib import admin
from .models import (
    Product, Category, ProductVariant,
    CartItem, Wishlist,
    Address, Order, OrderItem,
    Profile, Review,
    Coupon, Shipment,
    StoreProfile, PaymentWebhook
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock', 'is_available', 'category']
    list_filter = ['is_available', 'category']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category', 'description', 'price', 'stock', 'is_available')
        }),
        ('Images', {
            'fields': ('uploaded_image', 'image')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'name', 'price', 'stock']
    list_filter = ['product']
    search_fields = ['product__name', 'name']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'quantity', 'created_at']
    list_filter = ['user']
    search_fields = ['user__username', 'product__name']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    search_fields = ['user__username', 'product__name']


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'address_type', 'city', 'is_default']
    list_filter = ['address_type', 'is_default']
    search_fields = ['user__username', 'full_name', 'city', 'state']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'is_paid', 'created_at']
    list_filter = ['status', 'is_paid', 'created_at']
    search_fields = ['user__username', 'id']
    inlines = [OrderItemInline]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'created_at']
    search_fields = ['user__username', 'phone']


@admin.register(StoreProfile)
class StoreProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']
    search_fields = ['user__username']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']
    list_filter = ['rating']
    search_fields = ['product__name', 'user__username']


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_percent', 'active', 'valid_from', 'valid_to', 'used_count']
    list_filter = ['active']
    search_fields = ['code']


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ['order', 'tracking_number', 'carrier', 'status', 'estimated_delivery']
    list_filter = ['status', 'carrier']
    search_fields = ['order__id', 'tracking_number']


@admin.register(PaymentWebhook)
class PaymentWebhookAdmin(admin.ModelAdmin):
    list_display = ['gateway', 'event_type', 'received_at']
    list_filter = ['gateway', 'event_type']
    search_fields = ['event_type']
    readonly_fields = ['gateway', 'event_type', 'payload', 'received_at']
