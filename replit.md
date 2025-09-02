# Rust Shop Backend

## Overview

The Rust Shop Backend is a Flask-based web service designed to handle purchase transactions for a Rust game shop. The application provides an API endpoint for processing purchase data and integrates with Discord webhooks to send real-time purchase notifications. It includes a web interface for testing API functionality and monitoring system health.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
The application uses Flask as the web framework, chosen for its simplicity and lightweight nature. Flask provides the core routing, request handling, and template rendering capabilities. The application is structured with a modular approach using separate files for the main application logic and entry point.

### Web Interface
The frontend consists of a single-page application using HTML templates rendered by Flask. The interface uses Bootstrap for styling with a custom dark theme and provides a testing interface for the purchase API. The design implements a modern glass-morphism aesthetic with gradients and transparency effects.

### API Design
The application exposes RESTful endpoints including:
- `/health` - System health monitoring endpoint
- `/purchase` - POST endpoint for processing purchase transactions
- `/` - Main web interface for API testing

The API expects JSON payloads and returns structured JSON responses with appropriate HTTP status codes.

### Security and CORS
CORS (Cross-Origin Resource Sharing) is enabled to allow frontend integration from different domains. The application includes security measures like content-type validation and uses environment variables for sensitive configuration.

### Error Handling and Logging
Comprehensive logging is implemented using Python's logging module with DEBUG level for development. The application includes structured error responses and validation for incoming requests.

## External Dependencies

### Discord Integration
The primary external integration is Discord webhooks for purchase notifications. The webhook URL is configured via the `DISCORD_WEBHOOK_URL` environment variable, allowing the system to send formatted purchase messages to Discord channels.

### Frontend Libraries
- Bootstrap (via CDN) for responsive UI components and dark theme
- Font Awesome for iconography
- Custom CSS for enhanced styling and effects

### Python Dependencies
- Flask - Web framework
- Flask-CORS - Cross-origin resource sharing support
- Werkzeug - WSGI utilities and proxy fix middleware
- Requests - HTTP library for external API calls

### Environment Configuration
The application relies on environment variables for configuration:
- `SESSION_SECRET` - Flask session security
- `DISCORD_WEBHOOK_URL` - Discord webhook endpoint
- `PORT` - Server port configuration (handled by hosting platform)