-- ===========================================================
-- Maa Express: FULL DATABASE SCHEMA
-- Safe to run in MySQL Workbench
-- ===========================================================

-- (Optional) If database doesn't exist, create it:
-- CREATE DATABASE IF NOT EXISTS maa_express CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE maa_express;

USE maa_express;

-- -----------------------------------------------------------
-- 1) CLEAN UP EXISTING TABLES
-- -----------------------------------------------------------
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS category3_orders;
DROP TABLE IF EXISTS category2_buyer_info;
DROP TABLE IF EXISTS category1_buyer_info;

DROP TABLE IF EXISTS category3_products;
DROP TABLE IF EXISTS category2_listings;
DROP TABLE IF EXISTS category1_listings;

DROP TABLE IF EXISTS user_login_logs;
DROP TABLE IF EXISTS site_visits;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

-- -----------------------------------------------------------
-- 2) USERS
-- -----------------------------------------------------------
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(30),
    password_hash VARCHAR(255) NOT NULL,
    is_admin TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------
-- 3) USER LOGIN LOGS
-- -----------------------------------------------------------
CREATE TABLE user_login_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    ip_address VARCHAR(100),
    user_agent TEXT,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- -----------------------------------------------------------
-- 4) SITE VISITS (analytics)
-- -----------------------------------------------------------
CREATE TABLE site_visits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip_address VARCHAR(100),
    user_agent TEXT,
    page_url VARCHAR(500),
    visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------
-- 5) CATEGORY 1 LISTINGS
--    In-flight Luggage Space + Product Delivery
-- -----------------------------------------------------------
CREATE TABLE category1_listings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,

    -- Listing details
    title VARCHAR(255) NOT NULL,
    description TEXT,

    -- Origin side
    origin VARCHAR(255) NOT NULL,
    origin_airport VARCHAR(10) NOT NULL,              -- e.g. SYD, MEL
    origin_delivery_location VARCHAR(255),
    origin_delivery_postcode VARCHAR(20),

    -- Destination side
    destination VARCHAR(255) NOT NULL,
    destination_airport VARCHAR(10) NOT NULL,
    destination_delivery_location VARCHAR(255),
    destination_delivery_postcode VARCHAR(20),

    -- Flight date
    travel_date DATE NOT NULL,

    -- Pricing
    price DECIMAL(10,2) NOT NULL,
    discount_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    final_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,

    -- Media
    image_url VARCHAR(500),

    -- Admin approval
    admin_status ENUM('pending','approved','rejected') DEFAULT 'pending',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_cat1_user (user_id),
    INDEX idx_cat1_status (admin_status),
    INDEX idx_cat1_date (travel_date)
);

-- -----------------------------------------------------------
-- 6) CATEGORY 1 BUYER INFO
--    Buyer details for luggage space purchase
-- -----------------------------------------------------------
CREATE TABLE category1_buyer_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    listing_id INT NOT NULL,
    buyer_id INT NOT NULL,

    receiver_fullname VARCHAR(255),
    receiver_phone VARCHAR(30),
    receiver_email VARCHAR(255),
    delivery_address TEXT,
    note TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (listing_id) REFERENCES category1_listings(id),
    FOREIGN KEY (buyer_id) REFERENCES users(id),
    INDEX idx_cat1_buyer_listing (listing_id),
    INDEX idx_cat1_buyer_user (buyer_id)
);

-- -----------------------------------------------------------
-- 7) CATEGORY 2 LISTINGS
--    Travel Support / Companionship
-- -----------------------------------------------------------
CREATE TABLE category2_listings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,

    name VARCHAR(255) NOT NULL,
    description TEXT,
    gender ENUM('male','female','other') NOT NULL,

    travel_from VARCHAR(255),
    travel_to VARCHAR(255),
    travel_date DATE,

    price DECIMAL(10,2) NOT NULL,
    discount_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    final_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,

    image_url VARCHAR(500),

    admin_status ENUM('pending','approved','rejected') DEFAULT 'pending',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_cat2_user (user_id),
    INDEX idx_cat2_status (admin_status),
    INDEX idx_cat2_date (travel_date)
);

-- -----------------------------------------------------------
-- 8) CATEGORY 2 BUYER INFO
-- -----------------------------------------------------------
CREATE TABLE category2_buyer_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    listing_id INT NOT NULL,
    buyer_id INT NOT NULL,

    full_name VARCHAR(255),
    phone VARCHAR(30),
    email VARCHAR(255),
    note TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (listing_id) REFERENCES category2_listings(id),
    FOREIGN KEY (buyer_id) REFERENCES users(id),
    INDEX idx_cat2_buyer_listing (listing_id),
    INDEX idx_cat2_buyer_user (buyer_id)
);

-- -----------------------------------------------------------
-- 9) CATEGORY 3 PRODUCTS
--    Authentic Foreign Products Marketplace
-- -----------------------------------------------------------
CREATE TABLE category3_products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,

    product_name VARCHAR(255) NOT NULL,
    product_origin_country VARCHAR(255),
    description TEXT,

    price DECIMAL(10,2) NOT NULL,
    discount_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    final_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,

    authenticity_proof_url VARCHAR(500),  -- e.g. purchase receipt
    image_url VARCHAR(500),

    admin_status ENUM('pending','approved','rejected') DEFAULT 'pending',

    stock INT DEFAULT 1,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_cat3_user (user_id),
    INDEX idx_cat3_status (admin_status)
);

-- -----------------------------------------------------------
-- 10) CATEGORY 3 ORDERS
-- -----------------------------------------------------------
CREATE TABLE category3_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    buyer_id INT NOT NULL,

    quantity INT NOT NULL DEFAULT 1,
    total_amount DECIMAL(10,2) NOT NULL,

    buyer_fullname VARCHAR(255),
    buyer_phone VARCHAR(30),
    buyer_email VARCHAR(255),
    delivery_address TEXT,

    status ENUM('pending','paid','shipped','delivered') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (product_id) REFERENCES category3_products(id),
    FOREIGN KEY (buyer_id) REFERENCES users(id),
    INDEX idx_cat3_order_product (product_id),
    INDEX idx_cat3_order_buyer (buyer_id),
    INDEX idx_cat3_order_status (status)
);
