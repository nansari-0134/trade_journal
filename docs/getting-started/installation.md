# Installation & Setup

This guide details the complete installation and environment setup for running the Trade Journal locally or deploying it on a server.

---

## System Requirements

- **Operating System**: Windows 10/11, macOS 12+, or Ubuntu 20.04+ Linux
- **Python**: Version 3.10, 3.11, or 3.12
- **Git**: Installed and available in your system path
- **Disk Space**: At least 500 MB (includes virtual environment and cached market data)

---

## Step 1: Clone the Repository

Clone the project from GitHub into your local workspace:

```bash
git clone https://github.com/nansari-0134/trade_journal.git
cd trade_journal
```

---

## Step 2: Configure Virtual Environment

Always use an isolated virtual environment to prevent dependency conflicts.

=== "Windows (PowerShell)"
    ```powershell
    # Create the virtual environment
    python -m venv venv

    # Activate the environment
    .\venv\Scripts\Activate.ps1
    ```

=== "macOS / Linux"
    ```bash
    # Create the virtual environment
    python3 -m venv venv

    # Activate the environment
    source venv/bin/activate
    ```

---

## Step 3: Install Dependencies

Install the pinned production dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

If you plan to build or serve the documentation locally, ensure MkDocs and the Material theme are installed:

```bash
pip install mkdocs mkdocs-material
```

---

## Step 4: Apply Database Migrations

Initialize your local SQLite database:

```bash
python manage.py migrate
```

You should see output confirming that migrations for `admin`, `auth`, `contenttypes`, `journal`, and `sessions` were applied.

---

## Step 5: (Optional) Seed Sample Data

The application includes management commands to quickly seed common strategy templates and inter-product pairs:

```bash
# Seed standard strategy ratio templates (Spreads, Flies, Double-Flies)
python manage.py seed_strategies

# Seed common inter-product pairs (e.g., CL vs BZ)
python manage.py seed_interproduct_pairs
```

---

## Step 6: Launch the Development Server

Start the Django development server:

```bash
python manage.py runserver 127.0.0.1:8000
```

> **Note**: If port `8000` is already in use by another application on your system, bind to port `8001` or another open port:
> ```bash
> python manage.py runserver 127.0.0.1:8001
> ```

Open your browser and navigate to:
**[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** (or `http://127.0.0.1:8001/`).
