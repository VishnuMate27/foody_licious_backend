### API Endpoints Overview

#### Authentication
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/logout
- GET /api/v1/auth/verify

#### Users
- GET /api/v1/users/profile
- PUT /api/v1/users/profile
- GET /api/v1/users/order-history

#### Restaurants
- GET /api/v1/restaurants
- GET /api/v1/restaurants/:id
- POST /api/v1/restaurants (owner only)
- PUT /api/v1/restaurants/:id (owner only)
- GET /api/v1/restaurants/nearby

#### Items & Menu
- GET /api/v1/restaurants/:id/menu
- POST /api/v1/restaurants/:id/items (owner only)
- PUT /api/v1/items/:id (owner only)
- DELETE /api/v1/items/:id (owner only)

#### Orders
- POST /api/v1/orders
- GET /api/v1/orders/:id
- PUT /api/v1/orders/:id/status (restaurant owner only)
- GET /api/v1/orders/restaurant/:restaurantId (owner only)

#### Feedback
- POST /api/v1/feedback
- GET /api/v1/restaurants/:id/feedback
```