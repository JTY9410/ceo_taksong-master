# Gemini Project Overview: CEO Taksong Dashboard

## 1. Project Purpose

This project is a web-based dashboard for a logistics/transport company named "Taksong". It serves as an internal tool for the CEO and administrators to manage and visualize sales, customer, and transportation data.

## 2. Technology Stack

- **Backend:** Python 3, Flask
- **Database:** SQLite (`data/transport.db`)
- **Frontend:** HTML with Jinja2 templating
- **Key Python Libraries:**
  - `flask`: Web framework
  - `pandas`, `openpyxl`: For processing uploaded Excel files
  - `werkzeug`: User authentication (password hashing)
- **Deployment:** Docker, Docker Compose

## 3. Core Features

- **User Authentication:** Login system for authorized access.
- **Admin Panel:**
  - User management (`/admin/users`)
  - Customer data management (`/admin/customers`)
- **Dashboard (`/dashboard`):** Provides a high-level overview of key metrics.
- **Sales Management (`/sales`):**
  - Upload sales data via Excel files (`/sales/upload`).
  - View sales data (main, weekly, monthly, by customer).
- **Transport Management (`/transport`):**
  - Track different types of transport services (Jeju, self-car, special, shipping).
  - Manage penalties.

## 4. How to Run the Project

The project is containerized using Docker.

**To run the application:**
1.  Ensure Docker is installed and running.
2.  From the project root directory, run the command:
    ```bash
    docker-compose up -d
    ```
3.  The application will be accessible at `http://localhost:5009`.

**To stop the application:**
```bash
docker-compose down
```

## 5. Testing

The project includes a test script `test_excel_upload.py` for the Excel upload functionality and `simple_check.py` for basic data verification.

**To run the tests:**
```bash
# You may need to install dependencies first:
# pip install -r requirements.txt

# Run the simple check
python simple_check.py

# Run the excel upload test
python test_excel_upload.py
```
