#!/bin/bash

# AI Chat MP Docker Launch Script
# This script makes it easy to run the AI Chat MP application using Docker

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker Desktop first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
    
    print_success "Docker is running"
}

# Function to check if MongoDB is running on host
check_mongodb() {
    if ! command -v mongosh &> /dev/null && ! command -v mongo &> /dev/null; then
        print_warning "MongoDB client not found. Assuming MongoDB is running on port 27017."
        return 0
    fi
    
    # Try to connect to MongoDB
    if mongosh --host localhost:27017 --eval "db.runCommand({ping: 1})" --quiet &> /dev/null || \
       mongo --host localhost:27017 --eval "db.runCommand({ping: 1})" --quiet &> /dev/null; then
        print_success "MongoDB is accessible on localhost:27017"
    else
        print_error "Cannot connect to MongoDB on localhost:27017"
        print_error "Please ensure MongoDB is running before starting the Docker container."
        exit 1
    fi
}

# Function to check if .env file exists
check_env_file() {
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating template..."
        cat > .env << EOF
# AI Provider APIs
GEMINI_API_KEY=your-google-api-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here
OPENAI_API_KEY=your-openai-key-here
XAI_API_KEY=your-xai-key-here

# Search APIs
SERPER_API_KEY=your-serper-key-here
BRAVE_API_KEY=your-brave-key-here

# Weather APIs
OPENWEATHER_API_KEY=your-openweather-key-here

# Personal Weather Station (optional)
WEATHERFLOW_ACCESS_TOKEN=your-weatherflow-token-here
WEATHERFLOW_STATION_ID=your-station-id-here
EOF
        print_warning "Please edit .env file with your API keys before running the application."
        print_warning "Opening .env file for editing..."
        
        # Try to open with common editors
        if command -v code &> /dev/null; then
            code .env
        elif command -v nano &> /dev/null; then
            nano .env
        else
            print_warning "Please manually edit the .env file with your API keys."
        fi
        
        read -p "Press Enter when you've finished editing the .env file..."
    else
        print_success ".env file found"
    fi
}

# Function to build and run the application
run_app() {
    print_status "Building and starting AI Chat MP..."
    
    # Build and run with docker-compose
    docker-compose up --build -d
    
    if [ $? -eq 0 ]; then
        print_success "AI Chat MP is starting up..."
        print_status "Waiting for application to be ready..."
        
        # Wait for the application to be ready
        sleep 10
        
        # Check if the container is running
        if docker-compose ps | grep -q "Up"; then
            print_success "Application is running!"
            print_status "You can access AI Chat MP at: http://localhost:8501"
            print_status ""
            print_status "To stop the application, run: docker-compose down"
            print_status "To view logs, run: docker-compose logs -f"
            
            # Try to open in browser
            if command -v open &> /dev/null; then
                print_status "Opening in browser..."
                open http://localhost:8501
            fi
        else
            print_error "Application failed to start. Check logs with: docker-compose logs"
            exit 1
        fi
    else
        print_error "Failed to start application"
        exit 1
    fi
}

# Function to show usage
show_usage() {
    echo "AI Chat MP Docker Launch Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start    - Start the application (default)"
    echo "  stop     - Stop the application"
    echo "  restart  - Restart the application"
    echo "  logs     - Show application logs"
    echo "  status   - Show application status"
    echo "  help     - Show this help message"
    echo ""
}

# Parse command line arguments
case "${1:-start}" in
    start)
        print_status "Starting AI Chat MP..."
        check_docker
        check_mongodb
        check_env_file
        run_app
        ;;
    stop)
        print_status "Stopping AI Chat MP..."
        docker-compose down
        print_success "Application stopped"
        ;;
    restart)
        print_status "Restarting AI Chat MP..."
        docker-compose down
        check_docker
        check_mongodb
        docker-compose up --build -d
        print_success "Application restarted"
        ;;
    logs)
        docker-compose logs -f
        ;;
    status)
        docker-compose ps
        ;;
    help)
        show_usage
        ;;
    *)
        print_error "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac