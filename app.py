import os
import logging
import requests
from flask import Flask, request, jsonify, render_template, redirect
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import paypalrestsdk

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Enable CORS for frontend integration
CORS(app)

# Get Discord webhook URL from environment variables
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")

# Configure PayPal SDK
paypalrestsdk.configure({
    "mode": "sandbox",  # Change to "live" for production
    "client_id": os.environ.get("PAYPAL_CLIENT_ID", ""),
    "client_secret": os.environ.get("PAYPAL_CLIENT_SECRET", "")
})

# Product catalog with prices and descriptions
PRODUCTS = {
    "Mod": {
        "price": 3.00,
        "description": "Get Fly, Larger Anti-Raid Zone, Teleport and Mod Kits"
    },
    "Mod+": {
        "price": 7.00,
        "description": "Get Fly, XL Anti-Raid Zone, Teleport Players and Admin Kits w/Command Access"
    },
    "Hardcore VIP 1 Month": {
        "price": 3.00,
        "description": "VIP Kit and Rank for 1 month"
    },
    "Hardcore VIP Perma": {
        "price": 30.00,
        "description": "VIP Kit and Rank with a server Tag"
    },
    "Ultra Server Rank Package": {
        "price": 50.00,
        "description": "Mod+ on Oxide Build-A-Base, Perma Hardcore VIP, Ultra Tag, 3 Custom Tag Roll Tokens, 2 Custom Tag Token"
    }
}

@app.route('/')
def index():
    """Render the main shop page"""
    return render_template('index.html', products=PRODUCTS)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "message": "The Scrap Shop is running"
    })

@app.route('/purchase', methods=['POST'])
def handle_purchase():
    """Handle purchase requests and send notifications to Discord"""
    try:
        # Validate content type
        if not request.is_json:
            return jsonify({
                "error": "Content-Type must be application/json"
            }), 400

        # Get request data
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'item', 'price']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "required_fields": required_fields
            }), 400

        username = data['username'].strip()
        item = data['item'].strip()
        price = data['price']

        # Validate field values
        if not username:
            return jsonify({"error": "Username cannot be empty"}), 400
        
        if not item:
            return jsonify({"error": "Item cannot be empty"}), 400
        
        try:
            price = float(price)
            if price < 0:
                return jsonify({"error": "Price cannot be negative"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Price must be a valid number"}), 400

        # Check if Discord webhook is configured
        if not DISCORD_WEBHOOK:
            logger.warning("Discord webhook URL not configured")
            return jsonify({
                "error": "Discord webhook not configured",
                "message": "Please set DISCORD_WEBHOOK_URL environment variable"
            }), 500

        # Create Discord message
        discord_message = {
            "content": f"🛒 **Purchase Made!**\n👤 **Username:** {username}\n📦 **Item:** {item}\n💰 **Price:** ${price:.2f}"
        }

        # Send to Discord webhook
        try:
            response = requests.post(
                DISCORD_WEBHOOK,
                json=discord_message,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"Purchase notification sent successfully for {username} - {item} - ${price:.2f}")
                return jsonify({
                    "status": "success",
                    "message": "Purchase recorded and Discord notification sent!",
                    "data": {
                        "username": username,
                        "item": item,
                        "price": price
                    }
                })
            else:
                logger.error(f"Discord webhook failed with status {response.status_code}: {response.text}")
                return jsonify({
                    "error": "Failed to send Discord notification",
                    "message": f"Discord API returned status {response.status_code}"
                }), 500
                
        except requests.exceptions.Timeout:
            logger.error("Discord webhook request timed out")
            return jsonify({
                "error": "Discord notification timeout",
                "message": "The Discord webhook request timed out"
            }), 500
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Discord webhook request failed: {str(e)}")
            return jsonify({
                "error": "Failed to send Discord notification",
                "message": "Could not connect to Discord webhook"
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error in purchase handler: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred while processing the purchase"
        }), 500

@app.route('/create-payment', methods=['POST'])
def create_payment():
    """Create PayPal payment"""
    try:
        data = request.get_json()
        product_name = data.get('product')
        username = data.get('username', 'Anonymous')
        
        if not product_name or product_name not in PRODUCTS:
            return jsonify({"error": "Invalid product"}), 400
        
        product = PRODUCTS[product_name]
        
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": f"{request.url_root}execute-payment",
                "cancel_url": f"{request.url_root}cancel-payment"
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": product_name,
                        "sku": product_name.lower().replace(' ', '_'),
                        "price": str(product['price']),
                        "currency": "USD",
                        "quantity": 1,
                        "description": product['description']
                    }]
                },
                "amount": {
                    "total": str(product['price']),
                    "currency": "USD"
                },
                "description": f"{product_name} purchase for {username}",
                "custom": f"{username}|{product_name}"  # Store username and product for later
            }]
        })
        
        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    return jsonify({"approval_url": link.href})
        else:
            logger.error(f"PayPal payment creation failed: {payment.error}")
            return jsonify({"error": "Payment creation failed"}), 500
            
    except Exception as e:
        logger.error(f"Payment creation error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/execute-payment')
def execute_payment():
    """Execute PayPal payment after approval"""
    try:
        payment_id = request.args.get('paymentId')
        payer_id = request.args.get('PayerID')
        
        if not payment_id or not payer_id:
            return "Payment execution failed: Missing payment information", 400
            
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if payment.execute({"payer_id": payer_id}):
            # Payment successful - extract custom data and send Discord notification
            custom_data = payment.transactions[0].custom
            username, product_name = custom_data.split('|')
            price = float(payment.transactions[0].amount.total)
            
            # Send Discord notification
            if DISCORD_WEBHOOK:
                discord_message = {
                    "content": f"💰 **Payment Successful!**\\n👤 **Username:** {username}\\n📦 **Product:** {product_name}\\n💳 **Amount:** ${price:.2f}\\n🆔 **PayPal Transaction:** {payment.id}"
                }
                try:
                    requests.post(DISCORD_WEBHOOK, json=discord_message, timeout=10)
                except:
                    pass  # Don't fail the payment if Discord fails
            
            return f"""
            <html>
            <head><title>Payment Successful - The Scrap Shop</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #1a1a1a; color: white;">
                <h1 style="color: #28a745;">✅ Payment Successful!</h1>
                <p>Thank you <strong>{username}</strong>!</p>
                <p>Your purchase of <strong>{product_name}</strong> for <strong>${price:.2f}</strong> has been processed.</p>
                <p>You will receive your items in-game shortly.</p>
                <a href="/" style="color: #007bff; text-decoration: none;">← Back to Shop</a>
            </body>
            </html>
            """
        else:
            logger.error(f"PayPal payment execution failed: {payment.error}")
            return "Payment execution failed", 500
            
    except Exception as e:
        logger.error(f"Payment execution error: {str(e)}")
        return "Payment execution error", 500

@app.route('/cancel-payment')
def cancel_payment():
    """Handle cancelled PayPal payment"""
    return """
    <html>
    <head><title>Payment Cancelled - The Scrap Shop</title></head>
    <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #1a1a1a; color: white;">
        <h1 style="color: #ffc107;">⚠️ Payment Cancelled</h1>
        <p>Your payment was cancelled. No charges were made.</p>
        <a href="/" style="color: #007bff; text-decoration: none;">← Back to Shop</a>
    </body>
    </html>
    """

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({
        "error": "Method not allowed",
        "message": "The HTTP method is not allowed for this endpoint"
    }), 405

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500

if __name__ == '__main__':
    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Check if Discord webhook is configured on startup
    if not DISCORD_WEBHOOK:
        logger.warning("⚠️  DISCORD_WEBHOOK_URL environment variable not set!")
        logger.warning("   Purchase notifications will not work until this is configured.")
    else:
        logger.info("✅ Discord webhook configured successfully")
    
    logger.info(f"🚀 Starting The Scrap Shop on port {port}")
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )
