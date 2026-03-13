# Import Logistics Backend API Documentation

**Version:** 1.0.0  
**Base URL:** `http://localhost:8000/api/v1`  
**Authentication:** JWT Bearer Token  

## 📋 Table of Contents

- [Authentication](#authentication)
- [Users](#users)
- [Containers](#containers)
- [Items](#items)
- [Expenses](#expenses)
- [Pricing](#pricing)
- [Tracking](#tracking)
- [Reports](#reports)
- [Error Handling](#error-handling)
- [Data Models](#data-models)

## 🔐 Authentication

### Login
```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded
```

**Request Body:**
```
username=admin&password=changethis
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 604800,
  "user": {
    "id": 1,
    "email": "admin@example.com",
    "username": "admin",
    "first_name": "Super",
    "last_name": "Admin",
    "role": "admin",
    "is_active": true,
    "is_superuser": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

### Register
```http
POST /auth/register
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "newuser",
  "first_name": "John",
  "last_name": "Doe",
  "password": "securepassword",
  "role": "clerk"
}
```

**Response:** Same as login response

---

## 👥 Users

### Get Current User
```http
GET /users/me
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": 1,
  "email": "admin@example.com",
  "username": "admin",
  "first_name": "Super",
  "last_name": "Admin",
  "role": "admin",
  "is_active": true,
  "is_superuser": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Get All Users (Admin Only)
```http
GET /users?skip=0&limit=50
Authorization: Bearer {token}
```

**Query Parameters:**
- `skip` (int): Number of records to skip (default: 0)
- `limit` (int): Number of records to return (default: 50, max: 100)

**Response:**
```json
{
  "items": [...],
  "total": 25,
  "page": 1,
  "per_page": 50,
  "pages": 1
}
```

### Create User (Admin Only)
```http
POST /users
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "clerk@example.com",
  "username": "clerk1",
  "first_name": "Jane",
  "last_name": "Smith",
  "password": "password123",
  "role": "clerk",
  "is_active": true
}
```

### Update User
```http
PUT /users/me
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "first_name": "Updated",
  "last_name": "Name",
  "email": "updated@example.com"
}
```

---

## 📦 Containers

### Create Container
```http
POST /containers
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "CONT-2024-001",
  "container_type": "40ft",
  "msc_container_number": "MSCU123456789",
  "allocation_method": "weight_based",
  "notes": "Electronics and appliances"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "CONT-2024-001",
  "container_type": "40ft",
  "msc_container_number": "MSCU123456789",
  "allocation_method": "weight_based",
  "owner_id": 1,
  "is_sealed": false,
  "is_shipped": false,
  "allocation_override": false,
  "notes": "Electronics and appliances",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

### Get Containers
```http
GET /containers?skip=0&limit=50&container_type=40ft&is_shipped=false
Authorization: Bearer {token}
```

**Query Parameters:**
- `skip` (int): Pagination offset
- `limit` (int): Number of records
- `owner_id` (int): Filter by owner
- `container_type` (str): Filter by type (20ft, 40ft)
- `is_shipped` (bool): Filter by shipping status

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "CONT-2024-001",
      "container_type": "40ft",
      "msc_container_number": "MSCU123456789",
      "allocation_method": "weight_based",
      "owner_id": 1,
      "is_sealed": false,
      "is_shipped": false,
      "allocation_override": false,
      "notes": "Electronics and appliances",
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-01T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 50,
  "pages": 1
}
```

### Get Container Details
```http
GET /containers/{container_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": 1,
  "name": "CONT-2024-001",
  "container_type": "40ft",
  "msc_container_number": "MSCU123456789",
  "allocation_method": "weight_based",
  "owner_id": 1,
  "is_sealed": false,
  "is_shipped": false,
  "allocation_override": false,
  "notes": "Electronics and appliances",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z",
  "items": [...],
  "expenses": [...],
  "total_expenses": 5000.0,
  "total_weight": 15000.5,
  "total_value": 25000.0
}
```

### Update Container
```http
PUT /containers/{container_id}
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "CONT-2024-001-UPDATED",
  "msc_container_number": "MSCU987654321",
  "notes": "Updated notes"
}
```

### Seal Container
```http
POST /containers/{container_id}/seal
Authorization: Bearer {token}
```

**Response:**
```json
{
  "message": "Container sealed successfully"
}
```

### Allocate Costs
```http
POST /containers/{container_id}/allocate-costs?allocation_method=weight_based
Authorization: Bearer {token}
```

**Query Parameters:**
- `allocation_method` (str): "weight_based" or "value_based" (optional)

**Response:**
```json
{
  "method": "weight_based",
  "total_expenses": 5000.0,
  "total_weight": 15000.5,
  "items": [
    {
      "item_id": 1,
      "weight_ratio": 0.2,
      "allocated_cost": 1000.0,
      "landed_cost": 1500.0
    }
  ]
}
```

### Delete Container
```http
DELETE /containers/{container_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "message": "Container deleted successfully"
}
```

---

## 📋 Items

### Create Item
```http
POST /items
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "container_id": 1,
  "name": "Samsung 55\" QLED TV",
  "description": "4K Smart TV with HDR",
  "category": "electronics",
  "condition": "new",
  "purchase_price": 800.0,
  "purchase_currency": "USD",
  "purchase_date": "2024-01-15",
  "weight": 25.5,
  "volume": 0.15
}
```

**Response:**
```json
{
  "id": 1,
  "container_id": 1,
  "name": "Samsung 55\" QLED TV",
  "description": "4K Smart TV with HDR",
  "category": "electronics",
  "condition": "new",
  "purchase_price": 800.0,
  "purchase_currency": "USD",
  "purchase_date": "2024-01-15",
  "fx_rate_to_usd": 1.0,
  "purchase_price_usd": 800.0,
  "weight": 25.5,
  "volume": 0.15,
  "allocated_cost": 0.0,
  "landed_cost": 0.0,
  "recommended_price": null,
  "selling_price": null,
  "sold": false,
  "sold_date": null,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

### Get Items
```http
GET /items?skip=0&limit=50&container_id=1&category=electronics&sold=false
Authorization: Bearer {token}
```

**Query Parameters:**
- `skip` (int): Pagination offset
- `limit` (int): Number of records
- `container_id` (int): Filter by container
- `category` (str): Filter by category
- `condition` (str): Filter by condition
- `sold` (bool): Filter by sold status

### Get Item Details
```http
GET /items/{item_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": 1,
  "container_id": 1,
  "name": "Samsung 55\" QLED TV",
  "description": "4K Smart TV with HDR",
  "category": "electronics",
  "condition": "new",
  "purchase_price": 800.0,
  "purchase_currency": "USD",
  "purchase_date": "2024-01-15",
  "fx_rate_to_usd": 1.0,
  "purchase_price_usd": 800.0,
  "weight": 25.5,
  "volume": 0.15,
  "allocated_cost": 100.0,
  "landed_cost": 900.0,
  "recommended_price": 1200.0,
  "selling_price": null,
  "sold": false,
  "sold_date": null,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z",
  "price_records": [...],
  "profit_margin": 0.33,
  "profit_amount": 300.0
}
```

### Update Item
```http
PUT /items/{item_id}
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Samsung 55\" QLED TV - Updated",
  "selling_price": 1150.0
}
```

### Mark Item as Sold
```http
POST /items/{item_id}/mark-sold
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "selling_price": 1150.0,
  "sold_date": "2024-02-01"
}
```

**Response:**
```json
{
  "message": "Item marked as sold",
  "item": {...}
}
```

### Delete Item
```http
DELETE /items/{item_id}
Authorization: Bearer {token}
```

---

## 💰 Expenses

### Create Expense
```http
POST /expenses
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "container_id": 1,
  "expense_type": "shipping_fee",
  "amount": 2000.0,
  "currency": "USD",
  "description": "Ocean freight from Hamburg to Lagos"
}
```

**Response:**
```json
{
  "id": 1,
  "container_id": 1,
  "expense_type": "shipping_fee",
  "amount": 2000.0,
  "currency": "USD",
  "description": "Ocean freight from Hamburg to Lagos",
  "fx_rate_to_usd": 1.0,
  "amount_usd": 2000.0,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

### Get Container Expenses
```http
GET /expenses/container/{container_id}
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "id": 1,
    "container_id": 1,
    "expense_type": "shipping_fee",
    "amount": 2000.0,
    "currency": "USD",
    "description": "Ocean freight from Hamburg to Lagos",
    "fx_rate_to_usd": 1.0,
    "amount_usd": 2000.0,
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z"
  }
]
```

### Update Expense
```http
PUT /expenses/{expense_id}
Authorization: Bearer {token}
Content-Type: application/json
```

### Delete Expense
```http
DELETE /expenses/{expense_id}
Authorization: Bearer {token}
```

---

## 💡 Pricing

### Generate Pricing Recommendations
```http
POST /pricing/generate/{item_id}
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "include_cost_based": true,
  "include_market_pricing": true,
  "include_last_sold": true,
  "profit_margin": 0.25,
  "sources": ["jiji", "ebay"]
}
```

**Response:**
```json
{
  "item_id": 1,
  "cost_based_price": 1125.0,
  "market_prices": [
    {
      "source": "jiji",
      "price": 1200.0,
      "currency": "USD",
      "url": "https://jiji.ng/...",
      "confidence": 0.8,
      "found_at": "2024-01-15T12:00:00Z"
    }
  ],
  "last_sold_price": 1100.0,
  "recommended_price": 1150.0,
  "profit_margin": 0.28,
  "generated_at": "2024-01-15T12:00:00Z"
}
```

### Create Manual Price Record
```http
POST /pricing/record
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "item_id": 1,
  "method": "cost_based",
  "price": 1200.0,
  "currency": "USD",
  "margin_percentage": 0.33,
  "notes": "Manual pricing override"
}
```

### Get Item Price History
```http
GET /pricing/item/{item_id}
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "id": 1,
    "item_id": 1,
    "user_id": 1,
    "method": "cost_based",
    "source": null,
    "price": 1200.0,
    "currency": "USD",
    "source_url": null,
    "confidence_score": null,
    "margin_percentage": 0.33,
    "notes": "Manual pricing override",
    "is_active": true,
    "created_at": "2024-01-15T12:00:00Z",
    "updated_at": "2024-01-15T12:00:00Z"
  }
]
```

### Refresh Market Pricing
```http
POST /pricing/refresh-market/{item_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "message": "Market pricing refresh started"
}
```

---

## 🚚 Tracking

### Update Container Tracking
```http
POST /tracking/{container_id}/update
Authorization: Bearer {token}
```

**Response:**
```json
{
  "message": "Tracking update started"
}
```

### Get Tracking History
```http
GET /tracking/{container_id}/history
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "id": 1,
    "container_id": 1,
    "status": "departed",
    "location": "Hamburg Port",
    "vessel_name": "MSC VESSEL 123",
    "voyage_number": "V1234",
    "status_date": "2024-01-20T08:00:00Z",
    "estimated_arrival": "2024-02-15T10:00:00Z",
    "actual_arrival": null,
    "notification_sent": false,
    "created_at": "2024-01-20T09:00:00Z",
    "updated_at": "2024-01-20T09:00:00Z"
  }
]
```

### Get Current Status
```http
GET /tracking/{container_id}/status
Authorization: Bearer {token}
```

**Response:**
```json
{
  "status": "in_transit",
  "location": "Atlantic Ocean",
  "vessel_name": "MSC VESSEL 123",
  "voyage_number": "V1234",
  "status_date": "2024-01-25T12:00:00Z",
  "estimated_arrival": "2024-02-15T10:00:00Z",
  "last_updated": "2024-01-25T12:30:00Z"
}
```

### Update Notification Settings
```http
POST /tracking/{container_id}/notifications
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "enable_notifications": true,
  "notification_interval": 3,
  "email_notifications": true,
  "webhook_url": "https://your-webhook.com/notify"
}
```

---

## 📊 Reports

### Item Profit Report
```http
GET /reports/profit/items?container_id=1&category=electronics&sold_only=false
Authorization: Bearer {token}
```

**Query Parameters:**
- `container_id` (int): Filter by container
- `category` (str): Filter by category  
- `sold_only` (bool): Only sold items

**Response:**
```json
[
  {
    "item_id": 1,
    "item_name": "Samsung 55\" QLED TV",
    "category": "electronics",
    "purchase_price_usd": 800.0,
    "landed_cost": 900.0,
    "selling_price": 1150.0,
    "profit_amount": 250.0,
    "profit_margin": 0.28,
    "sold": true
  }
]
```

### Container Profit Report
```http
GET /reports/profit/containers?owner_id=1
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "container_id": 1,
    "container_name": "CONT-2024-001",
    "total_expenses": 5000.0,
    "total_items": 25,
    "items_sold": 10,
    "total_revenue": 12000.0,
    "total_profit": 3500.0,
    "profit_margin": 0.41
  }
]
```

### Category Profit Report
```http
GET /reports/profit/categories
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "category": "electronics",
    "total_items": 15,
    "items_sold": 8,
    "total_investment": 12000.0,
    "total_revenue": 16000.0,
    "total_profit": 4000.0,
    "average_margin": 0.33
  }
]
```

---

## ⚠️ Error Handling

### Error Response Format
All errors follow this structure:
```json
{
  "detail": "Error message description",
  "error_code": "SPECIFIC_ERROR_CODE",
  "status_code": 400
}
```

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `422` - Unprocessable Entity (validation errors)
- `500` - Internal Server Error

### Common Error Scenarios

**Authentication Required:**
```json
{
  "detail": "Could not validate credentials",
  "status_code": 401
}
```

**Insufficient Permissions:**
```json
{
  "detail": "Not enough permissions",
  "status_code": 403
}
```

**Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "status_code": 422
}
```

**Resource Not Found:**
```json
{
  "detail": "Container not found",
  "status_code": 404
}
```

---

## 📋 Data Models

### User Roles
- `admin` - Full system access
- `manager` - All containers, reports, user oversight
- `clerk` - Own containers only, basic operations
- `viewer` - Read-only access

### Container Types
- `20ft` - 20-foot container
- `40ft` - 40-foot container

### Allocation Methods
- `weight_based` - Distribute costs by item weight
- `value_based` - Distribute costs by item purchase value

### Item Categories
- `electronics` - TVs, phones, computers
- `vehicles` - Cars, motorcycles
- `engines` - Motors and engines
- `appliances` - Kitchen appliances, tools
- `food_items` - Food products, oils
- `laptops` - Laptops and tablets
- `other` - Miscellaneous items

### Item Conditions
- `new` - Brand new items
- `tokunbo` - Foreign used (Nigerian term)
- `used` - Locally used items

### Expense Types
- `loading_fee` - Container loading costs
- `shipping_fee` - Ocean/air freight costs
- `clearing_fee` - Customs clearance
- `offloading_fee` - Container unloading
- `warehouse_fee` - Storage costs
- `security_fee` - Security services
- `extra_fee` - Additional costs

### Tracking Statuses
- `booked` - Container booked
- `gate_in` - Container at port
- `loaded` - Loaded on vessel
- `departed` - Vessel departed
- `in_transit` - In transit
- `arrived` - Arrived at destination
- `discharged` - Unloaded from vessel
- `gate_out` - Left destination port
- `delivered` - Delivered to customer

### Supported Currencies
- `USD` - US Dollar (base currency)
- `EUR` - Euro
- `CZK` - Czech Koruna
- `NGN` - Nigerian Naira

---

## 🔧 Rate Limits

- **Authentication endpoints**: 5 requests per minute
- **CRUD operations**: 100 requests per minute
- **Reports**: 10 requests per minute
- **Bulk operations**: 5 requests per minute

## 📡 WebSocket Events (Future)

The API will support WebSocket connections for real-time updates:

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/tracking');

// Listen for tracking updates
ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Tracking update:', data);
};
```

## 📝 Changelog

### v1.0.0 (Current)
- Initial API release
- Full CRUD operations for all entities
- JWT authentication with RBAC
- Real-time tracking integration
- Comprehensive reporting system
- Multi-currency support with FX tracking

---

**For interactive API documentation, visit: `http://localhost:8000/docs`**