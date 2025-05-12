from .models import CartItem, Wishlist

def cart_item_count(request):
    """
    Returns the number of items in the user's cart.
    """
    count = 0
    if request.user.is_authenticated:
        count = CartItem.objects.filter(user=request.user).count()
    return {'cart_item_count': count}

def wishlist_count(request):
    """
    Returns the number of items in the user's wishlist.
    """
    count = 0
    if request.user.is_authenticated:
        count = Wishlist.objects.filter(user=request.user).count()
    return {'wishlist_count': count}
