# Testing Favorites & Recently Viewed

## ✅ Migration Applied Successfully

The migration has been created and applied:
- `favorites/migrations/0001_initial.py` created
- Tables created:
  - `favorites_favoritelisting`
  - `favorites_recentlyviewedlisting`

## Testing the API Endpoints

### 1. Test Favorites (requires authentication)

```bash
# Get your auth token first
curl -X POST http://localhost:8080/api/v1/auth/otp/request \
  -H "Content-Type: application/json" \
  -d '{"phone": "+998901234567"}'

# Verify OTP (you'll receive the code)
curl -X POST http://localhost:8080/api/v1/auth/otp/verify \
  -H "Content-Type: application/json" \
  -d '{"phone": "+998901234567", "code": "123456"}'

# Save the access token from response
TOKEN="your_access_token_here"

# List favorites (should be empty initially)
curl http://localhost:8080/api/v1/favorites \
  -H "Authorization: Bearer $TOKEN"

# Toggle favorite for listing ID 1
curl -X POST http://localhost:8080/api/v1/favorites/1/toggle \
  -H "Authorization: Bearer $TOKEN"

# List favorites again (should show the listing)
curl http://localhost:8080/api/v1/favorites \
  -H "Authorization: Bearer $TOKEN"

# Remove favorite
curl -X DELETE http://localhost:8080/api/v1/favorites/1 \
  -H "Authorization: Bearer $TOKEN"
```

### 2. Test Recently Viewed (works without auth using session)

```bash
# Track a view (creates a session)
curl -X POST http://localhost:8080/api/v1/recently-viewed/1 \
  -c cookies.txt

# List recently viewed (using same session)
curl http://localhost:8080/api/v1/recently-viewed \
  -b cookies.txt

# Track another view
curl -X POST http://localhost:8080/api/v1/recently-viewed/2 \
  -b cookies.txt

# List again
curl http://localhost:8080/api/v1/recently-viewed \
  -b cookies.txt

# Clear history
curl -X DELETE http://localhost:8080/api/v1/recently-viewed/clear \
  -b cookies.txt
```

### 3. Test Search with Filters

```bash
# Basic search
curl "http://localhost:8080/api/v1/search/listings?q=phone"

# Search with price filter
curl "http://localhost:8080/api/v1/search/listings?min_price=1000&max_price=5000"

# Search with category filter
curl "http://localhost:8080/api/v1/search/listings?category_slug=electronics"

# Search with attribute filter
curl "http://localhost:8080/api/v1/search/listings?attrs.brand=samsung"

# Search with multiple filters
curl "http://localhost:8080/api/v1/search/listings?q=phone&min_price=1000&condition=new&attrs.brand=samsung"
```

## Quick Django Shell Test

```bash
cd server
source venv/bin/activate
python manage.py shell
```

Then in the shell:

```python
from django.contrib.auth import get_user_model
from listings.models import Listing
from favorites.models import FavoriteListing, RecentlyViewedListing

User = get_user_model()

# Create a test user if needed
user, _ = User.objects.get_or_create(username='test')

# Create a test listing if needed
from taxonomy.models import Category, Location
category = Category.objects.first()
location = Location.objects.first()

listing, _ = Listing.objects.get_or_create(
    user=user,
    category=category,
    location=location,
    defaults={'title': 'Test Listing', 'price_amount': 1000}
)

# Test favorites
fav = FavoriteListing.objects.create(user=user, listing=listing)
print(f"Created favorite: {fav}")

# List favorites
print(f"User favorites: {FavoriteListing.objects.filter(user=user).count()}")

# Test recently viewed
recent = RecentlyViewedListing.objects.create(user=user, listing=listing)
print(f"Created recently viewed: {recent}")

# List recently viewed
print(f"Recently viewed: {RecentlyViewedListing.objects.filter(user=user).count()}")

# Clean up
fav.delete()
recent.delete()
print("Test data cleaned up!")
```

## Verify Tables Exist

```bash
cd server
source venv/bin/activate
python manage.py dbshell

# In SQLite shell:
.tables
# Should show: favorites_favoritelisting and favorites_recentlyviewedlisting

.schema favorites_favoritelisting
.schema favorites_recentlyviewedlisting

.exit
```

## Next Steps

1. ✅ Migrations applied
2. ✅ Tables created
3. ✅ API endpoints working
4. Now you can:
   - Test the endpoints with curl or Postman
   - Use the client-side components in your Next.js app
   - Create some test data to see it in action

## Troubleshooting

If you still see "no such table" error:
1. Make sure you're using the correct database (check DATABASES in settings.py)
2. Verify migrations were applied: `python manage.py showmigrations favorites`
3. Check tables exist: `python manage.py dbshell` then `.tables`
4. Restart Django server

The database tables are now ready to use! 🎉
