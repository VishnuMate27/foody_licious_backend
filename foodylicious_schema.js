// Foodylicious Database Setup for MongoDB
// Run this script in MongoDB shell or MongoDB Compass

// Use the foodylicious database
use('foodylicious');

// Drop existing collections if they exist (for clean setup)
db.users.drop();
db.restaurants.drop();
db.items.drop();
db.menu.drop();
db.orders.drop();
db.feedback.drop();

// Create collections with validation schemas

// Users Collection
db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["id", "name", "email", "phone", "address"],
      properties: {
        id: { bsonType: "string" },
        name: { bsonType: "string" },
        email: { 
          bsonType: "string",
          pattern: "^.+@.+\..+$"
        },
        phone: { bsonType: "string" },
        address: {
          bsonType: "object",
          required: ["addressText", "coordinates"],
          properties: {
            addressText: { bsonType: "string" },
            coordinates: {
              bsonType: "object",
              required: ["type", "coordinates"],
              properties: {
                type: { 
                  bsonType: "string",
                  enum: ["Point"]
                },
                coordinates: {
                  bsonType: "array",
                  items: { bsonType: "number" },
                  minItems: 2,
                  maxItems: 2
                }
              }
            }
          }
        },
        orderHistory: {
          bsonType: "array",
          items: { bsonType: "string" }
        }
      }
    }
  }
});

// Restaurants Collection
db.createCollection("restaurants", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["id", "name", "ownerName", "email", "phone", "address"],
      properties: {
        id: { bsonType: "string" },
        name: { bsonType: "string" },
        ownerName: { bsonType: "string" },
        email: { 
          bsonType: "string",
          pattern: "^.+@.+\..+$"
        },
        phone: { bsonType: "string" },
        address: {
          bsonType: "object",
          required: ["addressText", "coordinates"],
          properties: {
            addressText: { bsonType: "string" },
            coordinates: {
              bsonType: "object",
              required: ["type", "coordinates"],
              properties: {
                type: { 
                  bsonType: "string",
                  enum: ["Point"]
                },
                coordinates: {
                  bsonType: "array",
                  items: { bsonType: "number" },
                  minItems: 2,
                  maxItems: 2
                }
              }
            }
          }
        },
        photo: { bsonType: "string" },
        description: { 
          bsonType: "string",
          maxLength: 500
        },
        menuItems: {
          bsonType: "array",
          items: { bsonType: "string" }
        },
        receivedOrders: {
          bsonType: "array",
          items: { bsonType: "string" }
        },
        receivedFeedback: {
          bsonType: "array",
          items: { bsonType: "string" }
        }
      }
    }
  }
});

// Items Collection
db.createCollection("items", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["id", "restaurantId", "name", "price"],
      properties: {
        id: { bsonType: "string" },
        restaurantId: { bsonType: "string" },
        name: { bsonType: "string" },
        price: { bsonType: "number", minimum: 0 },
        image: { bsonType: "string" },
        description: { 
          bsonType: "string",
          maxLength: 500
        },
        ingredients: {
          bsonType: "array",
          items: { bsonType: "string" }
        }
      }
    }
  }
});

// Menu Collection
db.createCollection("menu", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["itemId", "restaurantId", "availableQuantity"],
      properties: {
        itemId: { bsonType: "string" },
        restaurantId: { bsonType: "string" },
        availableQuantity: { bsonType: "number", minimum: 0 }
      }
    }
  }
});

// Orders Collection
db.createCollection("orders", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["id", "items", "totalAmount", "amountBreakup", "orderStatus", "paymentStatus"],
      properties: {
        id: { bsonType: "string" },
        items: { bsonType: "object" },
        totalAmount: { bsonType: "number", minimum: 0 },
        amountBreakup: { bsonType: "object" },
        orderStatus: { 
          bsonType: "string",
          enum: ["Delivered", "Pending"]
        },
        paymentStatus: { 
          bsonType: "string",
          enum: ["Received", "Not Received"]
        }
      }
    }
  }
});

// Feedback Collection
db.createCollection("feedback", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["id", "restaurantId", "rating"],
      properties: {
        id: { bsonType: "string" },
        restaurantId: { bsonType: "string" },
        rating: { 
          bsonType: "number",
          minimum: 1,
          maximum: 5
        },
        description: { 
          bsonType: "string",
          maxLength: 500
        }
      }
    }
  }
});

// Create indexes for better performance
db.users.createIndex({ "id": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "phone": 1 });

db.restaurants.createIndex({ "id": 1 }, { unique: true });
db.restaurants.createIndex({ "email": 1 }, { unique: true });
db.restaurants.createIndex({ "name": 1 });
// Create 2dsphere index for geospatial queries (after data insertion)
db.restaurants.createIndex({ "address.coordinates": "2dsphere" });
db.users.createIndex({ "address.coordinates": "2dsphere" });

db.items.createIndex({ "id": 1 }, { unique: true });
db.items.createIndex({ "restaurantId": 1 });
db.items.createIndex({ "name": 1 });
db.items.createIndex({ "price": 1 });

db.menu.createIndex({ "itemId": 1 }, { unique: true });
db.menu.createIndex({ "restaurantId": 1 });

db.orders.createIndex({ "id": 1 }, { unique: true });
db.orders.createIndex({ "orderStatus": 1 });
db.orders.createIndex({ "paymentStatus": 1 });

db.feedback.createIndex({ "id": 1 }, { unique: true });
db.feedback.createIndex({ "restaurantId": 1 });
db.feedback.createIndex({ "rating": 1 });

// Insert sample data

// Sample Users
db.users.insertMany([
  {
    id: "user_001",
    name: "Rajesh Kumar",
    email: "rajesh.kumar@email.com",
    phone: "+91-9876543210",
    address: {
      addressText: "Vasant Vihar, New Delhi, 110057",
      coordinates: {
        type: "Point",
        coordinates: [77.1570, 28.5562] // [longitude, latitude] - GeoJSON format
      }
    },
    orderHistory: ["order_001", "order_003"]
  },
  {
    id: "user_002",
    name: "Priya Sharma",
    email: "priya.sharma@email.com",
    phone: "+91-9876543211",
    address: {
      addressText: "Koregaon Park, Pune, 411001",
      coordinates: {
        type: "Point",
        coordinates: [73.8958, 18.5362] // [longitude, latitude] - GeoJSON format
      }
    },
    orderHistory: ["order_002"]
  },
  {
    id: "user_003",
    name: "Amit Patel",
    email: "amit.patel@email.com",
    phone: "+91-9876543212",
    address: {
      addressText: "Sadar Nagpur, Maharashtra, 440001",
      coordinates: {
        type: "Point",
        coordinates: [79.0882, 21.1458] // [longitude, latitude] - GeoJSON format
      }
    },
    orderHistory: []
  }
]);

// Sample Restaurants
db.restaurants.insertMany([
  {
    id: "rest_001",
    name: "Spice Garden",
    ownerName: "Suresh Gupta",
    email: "spicegarden@restaurant.com",
    phone: "+91-9876543213",
    address: {
      addressText: "MG Road, Pune, 411001",
      coordinates: {
        type: "Point",
        coordinates: [73.8567, 18.5204] // [longitude, latitude] - GeoJSON format
      }
    },
    photo: "https://example.com/spice-garden.jpg",
    description: "Authentic Indian cuisine with traditional spices and flavors. We serve the best North Indian and South Indian dishes with fresh ingredients.",
    menuItems: ["item_001", "item_002", "item_003"],
    receivedOrders: ["order_001", "order_002"],
    receivedFeedback: ["feedback_001", "feedback_002"]
  },
  {
    id: "rest_002",
    name: "Pizza Corner",
    ownerName: "Marco Rossi",
    email: "pizzacorner@restaurant.com",
    phone: "+91-9876543214",
    address: {
      addressText: "Connaught Place, New Delhi, 110001",
      coordinates: {
        type: "Point",
        coordinates: [77.2167, 28.6315] // [longitude, latitude] - GeoJSON format
      }
    },
    photo: "https://example.com/pizza-corner.jpg",
    description: "Fresh wood-fired pizzas with authentic Italian taste. We use only the finest ingredients imported from Italy for an authentic experience.",
    menuItems: ["item_004", "item_005"],
    receivedOrders: ["order_003"],
    receivedFeedback: ["feedback_003"]
  }
]);

// Sample Items
db.items.insertMany([
  {
    id: "item_001",
    restaurantId: "rest_001",
    name: "Butter Chicken",
    price: 320,
    image: "https://example.com/butter-chicken.jpg",
    description: "Creamy and rich butter chicken with tender pieces of chicken in a tomato-based sauce with aromatic spices.",
    ingredients: ["Chicken", "Tomato", "Cream", "Butter", "Garam Masala", "Ginger", "Garlic"]
  },
  {
    id: "item_002",
    restaurantId: "rest_001",
    name: "Paneer Tikka",
    price: 280,
    image: "https://example.com/paneer-tikka.jpg",
    description: "Grilled cottage cheese marinated in yogurt and spices, served with mint chutney.",
    ingredients: ["Paneer", "Yogurt", "Bell Peppers", "Onion", "Mint", "Spices"]
  },
  {
    id: "item_003",
    restaurantId: "rest_001",
    name: "Biryani",
    price: 350,
    image: "https://example.com/biryani.jpg",
    description: "Fragrant basmati rice cooked with aromatic spices and tender meat or vegetables.",
    ingredients: ["Basmati Rice", "Chicken/Mutton", "Saffron", "Onion", "Yogurt", "Spices"]
  },
  {
    id: "item_004",
    restaurantId: "rest_002",
    name: "Margherita Pizza",
    price: 450,
    image: "https://example.com/margherita.jpg",
    description: "Classic Italian pizza with fresh mozzarella, tomato sauce, and basil leaves.",
    ingredients: ["Pizza Dough", "Mozzarella", "Tomato Sauce", "Fresh Basil", "Olive Oil"]
  },
  {
    id: "item_005",
    restaurantId: "rest_002",
    name: "Pepperoni Pizza",
    price: 520,
    image: "https://example.com/pepperoni.jpg",
    description: "Delicious pizza topped with spicy pepperoni and melted cheese.",
    ingredients: ["Pizza Dough", "Mozzarella", "Pepperoni", "Tomato Sauce"]
  }
]);

// Sample Menu
db.menu.insertMany([
  { itemId: "item_001", restaurantId: "rest_001", availableQuantity: 25 },
  { itemId: "item_002", restaurantId: "rest_001", availableQuantity: 30 },
  { itemId: "item_003", restaurantId: "rest_001", availableQuantity: 20 },
  { itemId: "item_004", restaurantId: "rest_002", availableQuantity: 40 },
  { itemId: "item_005", restaurantId: "rest_002", availableQuantity: 35 }
]);

// Sample Orders
db.orders.insertMany([
  {
    id: "order_001",
    items: {
      "rest_001": [
        { itemId: "item_001", quantity: 2 },
        { itemId: "item_002", quantity: 1 }
      ]
    },
    totalAmount: 920,
    amountBreakup: {
      "rest_001": 920
    },
    orderStatus: "Delivered",
    paymentStatus: "Received"
  },
  {
    id: "order_002",
    items: {
      "rest_001": [
        { itemId: "item_003", quantity: 1 }
      ]
    },
    totalAmount: 350,
    amountBreakup: {
      "rest_001": 350
    },
    orderStatus: "Pending",
    paymentStatus: "Not Received"
  },
  {
    id: "order_003",
    items: {
      "rest_002": [
        { itemId: "item_004", quantity: 1 },
        { itemId: "item_005", quantity: 1 }
      ]
    },
    totalAmount: 970,
    amountBreakup: {
      "rest_002": 970
    },
    orderStatus: "Delivered",
    paymentStatus: "Received"
  }
]);

// Sample Feedback
db.feedback.insertMany([
  {
    id: "feedback_001",
    restaurantId: "rest_001",
    rating: 4.5,
    description: "Excellent food quality and taste. The butter chicken was amazing. Fast delivery and hot food."
  },
  {
    id: "feedback_002",
    restaurantId: "rest_001",
    rating: 4.0,
    description: "Good food but the quantity could be better. Overall satisfied with the service and taste."
  },
  {
    id: "feedback_003",
    restaurantId: "rest_002",
    rating: 5.0,
    description: "Best pizza in town! Authentic Italian taste and perfect cheese blend. Highly recommended."
  }
]);

console.log("Foodylicious database setup completed successfully!");
console.log("Collections created with validation schemas and indexes");
console.log("Sample data inserted for all collections");

// Verification queries
console.log("\n=== Database Verification ===");
console.log("Users count:", db.users.countDocuments());
console.log("Restaurants count:", db.restaurants.countDocuments());
console.log("Items count:", db.items.countDocuments());
console.log("Menu items count:", db.menu.countDocuments());
console.log("Orders count:", db.orders.countDocuments());
console.log("Feedback count:", db.feedback.countDocuments());